import json
import traceback

from django.utils.functional import cached_property
from django_elasticsearch_dsl_drf.serializers import DocumentSerializer
from pkdb_app.behaviours import MEASUREMENTTYPE_FIELDS
from pkdb_app.comments.serializers import DescriptionSerializer, CommentSerializer, CommentElasticSerializer, \
    DescriptionElasticSerializer
from pkdb_app.data.documents import SubSetDocument
from pkdb_app.data.models import DataSet, Data, SubSet, Dimension, DataPoint
from pkdb_app.outputs.models import Output
from pkdb_app.subjects.models import Individual
from pkdb_app.outputs.pk_calculation import pkoutputs_from_timecourse
from pkdb_app.outputs.serializers import OUTPUT_FOREIGN_KEYS, OUTPUT_FIELDS
from pkdb_app.serializers import WrongKeyValidationSerializer, ExSerializer, StudySmallElasticSerializer
from pkdb_app.subjects.models import DataFile
from pkdb_app.utils import _create, create_multiple_bulk, create_multiple_bulk_normalized, list_of_pk
from rest_framework import serializers
import pandas as pd
import numpy as np

from functools import lru_cache


class DimensionSerializer(WrongKeyValidationSerializer):
    output = serializers.CharField(write_only=True, allow_null=False, allow_blank=False)

    class Meta:
        model = Dimension
        fields = ["comments", "descriptions", "dimension", "output"]


class SubSetSerializer(ExSerializer):
    """
    DataSetSerializer
    """
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    dimensions = DimensionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    shared = serializers.ListField(child=serializers.CharField(), write_only=True, allow_empty=True)

    class Meta:
        model = SubSet
        fields = ['name', "descriptions", "comments", "dimensions", "shared"]

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        return data

    def create(self, validated_data):
        validated_data["study"] = self.context["study"]

        subset_instance, poped_data = _create(model_manager=self.Meta.model.objects,
                                              validated_data=validated_data,
                                              create_multiple_keys=['comments', 'descriptions'],
                                              pop=['dimensions', 'shared'])

        if subset_instance.data.data_type in ["scatter"]:
            kwargs = {**poped_data, 'subset_instance': subset_instance}
            self.create_scatter(**kwargs)
        elif subset_instance.data.data_type == "timecourse":
            kwargs = {'dimensions': poped_data["dimensions"], 'subset_instance': subset_instance}
            self.create_timecourse(**kwargs)
        # subset_instance.save()
        return subset_instance

    def validate_shared(self, shared):
        if isinstance(shared , str):
            raise serializers.ValidationError({"shared": "Shared field has to be a list not a string.", "detail": shared})


    def _validate_time(self, time):
        if any(np.isnan(np.array(time))):
            raise serializers.ValidationError({"time": "No time points are allowed to be nan", "detail": time})

    def calculate_pks_from_timecourses(self, subset):
        # calculate pharmacokinetics outputs
        try:
            outputs = pkoutputs_from_timecourse(subset)
        except Exception as e:
            raise serializers.ValidationError(
                {"pharmacokinetics exception": traceback.format_exc()}
            )

        errors = []
        for output in outputs:
            try:
                output["measurement_type"].validate_complete(output)
            except ValueError as err:
                errors.append(err)
        if errors:
            raise serializers.ValidationError(
                {"calculated outputs": errors},
            )
        interventions = [o.pop("interventions") for o in outputs]

        outputs_dj = create_multiple_bulk(subset, "subset", outputs, Output)

        for intervention, output in zip(interventions, outputs_dj):
            output.interventions.add(*intervention)

        if outputs_dj:
            outputs_normed = create_multiple_bulk_normalized(outputs_dj, Output)
            for output in outputs_normed:
                output.interventions.add(*output.raw.interventions.all())
        subset.save()

    @staticmethod
    def _add_id_to_foreign_keys(value: str):
        if value in OUTPUT_FOREIGN_KEYS:
            return value + "_id"
        else:
            return value

    @staticmethod
    def _remove_id_to_foreign_keys(value: str):
        if "_id" in value:
            return value[:-3]
        else:
            return value

    def create_scatter(self, dimensions, shared, subset_instance):
        study = self.context["study"]
        study_outputs = study.outputs.filter(normed=True)
        if len(dimensions) != 2:
            raise serializers.ValidationError(
                f"Scatter plots have to be two dimensional. Dimensions: <{dimensions}> has a len of <{len(dimensions)}.> ")

        if not shared:
            raise serializers.ValidationError(
                f"The <shared> field is required for scatter plots.")
        outputs_pd = pd.DataFrame(study_outputs.values())

        data_set = outputs_pd[outputs_pd['label'].isin(dimensions)]
        if len(data_set) == 0:
            raise serializers.ValidationError(
                {"data_set": {
                    "data": [{"subsets": {"dimensions": f"Outputs with label <{dimensions}> do not exist."}}]}})

        data_set["dimension"] = None
        data_set.loc[data_set['label'] == dimensions[0], 'dimension'] = 0
        data_set.loc[data_set['label'] == dimensions[1], 'dimension'] = 1

        shared_reformated = []
        for shared_field in shared:
            shared_field_reformated = self._add_id_to_foreign_keys(shared_field)
            if shared_field_reformated not in data_set:
                p_options = [self._remove_id_to_foreign_keys(c) for c in data_set.columns]
                raise serializers.ValidationError(
                    f"Shared_field <{shared_field}> not in outputs fields. Options are <{p_options}>")
            shared_reformated.append(shared_field_reformated)

        if len(data_set.groupby(shared_reformated)) == 0:
            raise serializers.ValidationError(
                f"Outputs have no values on shared field")

        subset_outputs = []
        for shared_values, shared_data in data_set.groupby(shared_reformated):
            x_data = shared_data[shared_data["dimension"] == 0]
            y_data = shared_data[shared_data["dimension"] == 1]

            if len(x_data) != 1 or len(y_data) != 1:
                if shared == ['individual']:
                    print(int(shared_values))
                    shared_values = Individual.objects.get(pk=int(shared_values)).name
                raise serializers.ValidationError(
                    f"Dimensions <{dimensions}> do not match in respect to the shared fields."
                    f"The shared field <{shared}> with values <{shared_values}>"
                    f" do not uniquely assign 1 x output to 1 y output. "
                    f"<{dimensions[0]}> has <{len(x_data)}> outputs. <{dimensions[1]}> has <{len(y_data)}> outputs."
                )
            data_point_instance = DataPoint.objects.create(subset=subset_instance)
            x_output = study_outputs.get(pk=x_data["id"])
            y_output = study_outputs.get(pk=y_data["id"])
            subset_outputs.append(x_output)
            subset_outputs.append(y_output)

            Dimension.objects.create(dimension=0,
                                     study=study,
                                     output=x_output,
                                     data_point=data_point_instance)
            Dimension.objects.create(dimension=1,
                                     study=study,
                                     output=y_output,
                                     data_point=data_point_instance)

        subset_instance.pks.add(*subset_outputs)

    def create_timecourse(self, subset_instance, dimensions):
        study = self.context["study"]
        if len(dimensions) != 1:
            raise serializers.ValidationError(
                f"Timecourses have to be one-dimensional, but '{len(dimensions)}' dimensions found <{dimensions}>.")
        subset_outputs = study.outputs.filter(normed=True, label=dimensions[0])
        if len(subset_outputs) == 0:
            raise serializers.ValidationError(
                f"Timecourses cannot be empty. No outputs found <{dimensions[0]}>.")
        if len(subset_outputs) == 1:
            raise serializers.ValidationError(
                f"Timecourses require at least two outputs, but only a single output exists in timecourse. "
                f"Encode the label <{dimensions[0]}> as 'output_type=output' instead of 'output_type=timecourse'.")
        subset_instance.pks.add(*subset_outputs)
        if not subset_outputs.exists():
            raise serializers.ValidationError(
                {"dataset": {
                    "data": [
                        {"subsets": {"name": f"Outputs with label <{dimensions}> do not exist."}}
                    ]
                }}
            )

        dimensions = []
        for output in subset_outputs.iterator():
            data_point_instance = DataPoint.objects.create(subset=subset_instance)

            dimension = Dimension(dimension=0, study=study, output=output, data_point=data_point_instance)
            dimensions.append(dimension)
        Dimension.objects.bulk_create(dimensions)

        self.calculate_pks_from_timecourses(subset_instance)


class DataSerializer(ExSerializer):
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    subsets = SubSetSerializer(
        many=True, read_only=False, required=True, allow_null=True
    )
    image = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Data
        fields = ['name', "data_type", "comments", "descriptions", "image", "subsets"]

    def to_internal_value(self, data):
        # ----------------------------------
        # if timecourse, add time subsets automatically
        # ----------------------------------
        # todo: ...
        # ----------------------------------
        # finished
        # ----------------------------------
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        study = self.context["study"]
        data_instance, poped_data = _create(model_manager=self.Meta.model.objects,
                                            validated_data={**validated_data, "dataset": study.dataset},
                                            create_multiple_keys=['comments', 'descriptions'],
                                            pop=['subsets'])

        for subset in poped_data["subsets"]:
            subset_instance, poped_data = _create(model_serializer=SubSetSerializer(context=self.context),
                                                  validated_data={**subset, "data": data_instance},
                                                  create_multiple_keys=['comments', 'descriptions'])
        return data_instance


class DataSetSerializer(ExSerializer):
    data = DataSerializer(many=True, read_only=False, required=False, allow_null=True)
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = DataSet
        fields = ['data', "comments", "descriptions"]

    def _validate_unique_names(self, data_container):
        names = []
        for data_single in data_container:
            if data_single.get("name") in names:
                raise serializers.ValidationError(
                    {"name": f"Duplicated name <{data_single.get('name')}>. Consider writing the name "
                             f"in the to the excel sheet. By mapping the name field {{'name':'col==*'}} the instances are"
                             f" automatically groupby the name."})

            else:
                names.append(data_single.get("name"))
            subset_names = []
            for subset in data_single.get("subsets", []):
                if subset.get("name") in subset_names:
                    raise serializers.ValidationError(
                        f"Subsets with same names are not allowed within one data instance. "
                        f"Data instance <{data_single.get('name')}> contains multiple subsets with name <{subset.get('name')}>.")
                else:
                    subset_names.append(subset.get("name"))

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)

        # parse special formatting:
        data_container = []
        for data_unsplitted in data.get('data', []):
            temp_data = self.split_entry(data_unsplitted)
            for data_single in temp_data:
                subsets = data_single.get('subsets')
                if subsets:
                    temp_subsets = []
                    for subset in subsets:
                        temp_subsets.extend(
                            self.split_entry(subset)
                        )
                    data_single['subsets'] = temp_subsets
                data_container.extend(self.entries_from_file(data_single))
        self.validate_no_timeocourses(data_container)
        autogenerate_timecourses = self.autogenerate_timecourses()
        if autogenerate_timecourses:
            data_container.append(autogenerate_timecourses)

        data['data'] = data_container
        return super().to_internal_value(data)

    def validate_no_timeocourses(self, data):
        for data_single in data:
            if data_single.get("data_type") == Data.DataTypes.Timecourse:
                raise serializers.ValidationError("timecourses are not allowed to be definied explictly in dataset. "
                                                  "Timecourses are created automatically by adding label "
                                                  "and output_type='timecourse' to the respective outputs.")


    def autogenerate_timecourses(self):
        # Study = apps.get_model('studies', 'Study')

        study_sid = self.context["request"].path.split("/")[-2]
        outputs = Output.objects.filter(study__sid=study_sid, normed=True, output_type=Output.OutputTypes.Timecourse)
        timecourse_labels = outputs.values_list("label", flat=True).distinct()
        if len(timecourse_labels) > 0:
            auto_generated_data = {
                "name": "AutoGenerate",
                "data_type": "timecourse",
                "subsets":
                    [{"name": label, "dimensions": [label]} for label in timecourse_labels]
            }
            return auto_generated_data

    def validate(self, attrs):
        self._validate_unique_names(attrs["data"])
        return super().validate(attrs)

    def create(self, validated_data):
        dataset_instance, poped_data = _create(model_manager=self.Meta.model.objects,
                                               validated_data=validated_data,
                                               create_multiple_keys=['comments', 'descriptions'],
                                               pop=['data'])
        data_instance_container = []
        for data_single in poped_data['data']:
            data_single["dataset"] = dataset_instance
            data_instance, _ = _create(
                model_serializer=DataSerializer(context=self.context),
                validated_data=data_single,
            )

            data_instance_container.append(data_instance)

        dataset_instance.data.add(*data_instance_container)
        dataset_instance.save()
        return dataset_instance


################################
# Read Serializer
################################

class TimecourseSerializer(serializers.Serializer):
    """ Timecourse Serializer"""
    study_sid = serializers.CharField()
    study_name = serializers.CharField()
    output_pk = serializers.SerializerMethodField()
    subset_pk = serializers.IntegerField(source="pk")
    subset_name = serializers.CharField(source="name")

    intervention_pk = serializers.SerializerMethodField()
    group_pk = serializers.SerializerMethodField()
    individual_pk = serializers.SerializerMethodField()
    normed = serializers.SerializerMethodField()

    tissue = serializers.SerializerMethodField()
    tissue_label = serializers.SerializerMethodField()

    method = serializers.SerializerMethodField()
    method_label = serializers.SerializerMethodField()

    label = serializers.SerializerMethodField()

    time = serializers.SerializerMethodField()
    time_unit = serializers.SerializerMethodField()

    measurement_type = serializers.SerializerMethodField()
    measurement_type_label = serializers.SerializerMethodField()
    choice = serializers.SerializerMethodField()
    choice_label = serializers.SerializerMethodField()

    substance = serializers.SerializerMethodField()
    substance_label = serializers.SerializerMethodField()

    value = serializers.SerializerMethodField()
    mean = serializers.SerializerMethodField()
    median = serializers.SerializerMethodField()
    min = serializers.SerializerMethodField()
    max = serializers.SerializerMethodField()
    sd = serializers.SerializerMethodField()
    se = serializers.SerializerMethodField()
    cv = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()

    # @cached_property
    # def json_object(self):
    #    return json.dumps(self.instance.to_dict())

    @lru_cache(maxsize=128)
    def _get_general(self, obj):
        """ This function reshapes and reformats the outputs to a Pandas DataFrame. """

        obj = [v["point"][0] for v in json.loads(obj)["array"]]
        result = pd.DataFrame(obj)
        return result.where(result.notnull(), None)

    def _get_field(self, obj, field):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result[field].isnull().all():
            return None
        return list(result[field].values)

    def get_output_pk(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        return self._get_field(obj, "pk")

    def get_intervention_pk(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        return [i["pk"] for i in result["interventions"].iloc[0]]

    def get_group_pk(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["group"][0]:
            return result["group"][0]["pk"]

    def get_individual_pk(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["individual"][0]:
            return result["individual"][0]["pk"]

    def get_normed(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["normed"][0]

    def get_tissue(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["tissue"][0]:
            return result["tissue"][0]["sid"]

    def get_tissue_label(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["tissue"][0]:
            return result["tissue"][0]["label"]

    def get_method(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["method"][0]:
            return result["method"][0]["sid"]

    def get_method_label(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["method"][0]:
            return result["method"][0]["label"]

    def get_label(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["label"][0]

    def get_time(self, obj):
        return self._get_field(obj, "time")

    def get_time_unit(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["time_unit"][0]

    def get_measurement_type(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["measurement_type"][0]["sid"]

    def get_measurement_type_label(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["measurement_type"][0]["label"]

    def get_choice(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["choice"][0]:
            return result["choice"][0]["sid"]

    def get_choice_label(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["choice"][0]:
            return result["choice"][0]["label"]

    def get_substance(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["substance"][0]:
            return result["substance"][0]["sid"]

    def get_substance_label(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["substance"][0]:
            return result["substance"][0]["label"]

    def get_value(self, obj):
        return self._get_field(obj, "value")

    def get_mean(self, obj):
        return self._get_field(obj, "mean")

    def get_median(self, obj):
        return self._get_field(obj, "median")

    def get_min(self, obj):
        return self._get_field(obj, "min")

    def get_max(self, obj):
        return self._get_field(obj, "max")

    def get_sd(self, obj):
        return self._get_field(obj, "sd")

    def get_se(self, obj):
        return self._get_field(obj, "se")

    def get_cv(self, obj):
        return self._get_field(obj, "cv")

    def get_unit(self, obj):
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["unit"][0]

    class Meta:
        fields = ["study_sid", "study_name", "output_pk", "intervention_pk", "group_pk", "individual_pk", "normed",
                  "calculated"] + OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS


class SubSetElasticSerializer(DocumentSerializer):
    study = StudySmallElasticSerializer(read_only=True)
    name = serializers.CharField()
    data_type = serializers.CharField()
    array = serializers.SerializerMethodField()

    class Meta:
        document = SubSetDocument
        fields = ["pk",
                  "study",
                  "name",
                  "data_type",
                  "array",
                  "timecourse"]

    def get_array(self, object):
        return [point["point"] for point in object.to_dict()["array"]]


class DataSetElasticSmallSerializer(serializers.ModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    subsets = serializers.SerializerMethodField()

    class Meta:
        model = DataSet
        fields = ["pk", "descriptions", "comments", "subsets"]
        read_only_fields = fields

    def get_subsets(self, obj):
        return list_of_pk("subsets", obj)


class DataAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dimension
        fields = ["study_sid",
                  "study_name",
                  "data_pk",
                  "data_name",
                  "data_type",
                  "subset_pk",
                  "subset_name",
                  "data_point_pk",
                  "output_pk",
                  "dimension"]
        read_only_fields = fields
