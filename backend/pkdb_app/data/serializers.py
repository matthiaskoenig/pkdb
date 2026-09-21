"""Serializers for uploading and reading data sets, data and subsets."""

import json
import traceback
from functools import lru_cache

import numpy as np
import pandas as pd
from django_elasticsearch_dsl_drf.serializers import DocumentSerializer
from rest_framework import serializers

from pkdb_app.behaviours import MEASUREMENTTYPE_FIELDS
from pkdb_app.comments.serializers import (
    CommentElasticSerializer,
    CommentSerializer,
    DescriptionElasticSerializer,
    DescriptionSerializer,
)
from pkdb_app.data.documents import SubSetDocument
from pkdb_app.data.models import Data, DataPoint, DataSet, Dimension, SubSet
from pkdb_app.outputs.models import Output
from pkdb_app.outputs.pk_calculation import pkoutputs_from_timecourse
from pkdb_app.outputs.serializers import OUTPUT_FIELDS, OUTPUT_FOREIGN_KEYS
from pkdb_app.serializers import (
    ExSerializer,
    StudySmallElasticSerializer,
    WrongKeyValidationSerializer,
)
from pkdb_app.subjects.models import DataFile, Individual
from pkdb_app.utils import (
    _create,
    create_multiple_bulk,
    create_multiple_bulk_normalized,
    list_of_pk,
)


class DimensionSerializer(WrongKeyValidationSerializer):
    """Serializer for uploading one dimension of a scatter subset.

    The dimension is linked to an output.
    """

    output = serializers.CharField(write_only=True, allow_null=False, allow_blank=False)

    class Meta:
        model = Dimension
        fields = ["comments", "descriptions", "dimension", "output"]


class SubSetSerializer(ExSerializer):
    """Serializer for uploading a subset.

    The scatter or timecourse data points of the subset are built.
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

    shared = serializers.ListField(
        child=serializers.CharField(), write_only=True, allow_empty=True
    )

    class Meta:
        model = SubSet
        fields = ["name", "descriptions", "comments", "dimensions", "shared"]

    def to_internal_value(self, data):
        """Check for unexpected keys and return the raw data unchanged.

        The field conversion of the framework is skipped.
        """
        self.validate_wrong_keys(data)
        return data

    def create(self, validated_data):
        """Create the subset and build its data points.

        The data type of the subset decides whether scatter or timecourse points
        are built.
        """
        validated_data["study"] = self.context["study"]

        subset_instance, poped_data = _create(
            model_manager=self.Meta.model.objects,
            validated_data=validated_data,
            create_multiple_keys=["comments", "descriptions"],
            pop=["dimensions", "shared"],
        )

        if subset_instance.data.data_type in ["scatter"]:
            kwargs = {**poped_data, "subset_instance": subset_instance}
            self.create_scatter(**kwargs)
        elif subset_instance.data.data_type == "timecourse":
            kwargs = {
                "dimensions": poped_data["dimensions"],
                "subset_instance": subset_instance,
            }
            self.create_timecourse(**kwargs)
        # subset_instance.save()
        return subset_instance

    def validate_shared(self, shared):
        """Validate that the shared field is a list, not a plain string."""
        if isinstance(shared, str):
            raise serializers.ValidationError(
                {
                    "shared": "Shared field has to be a list not a string.",
                    "detail": shared,
                }
            )

    def _validate_time(self, time):
        if any(np.isnan(np.array(time))):
            raise serializers.ValidationError(
                {"time": "No time points are allowed to be nan", "detail": time}
            )

    def calculate_pks_from_timecourses(self, subset):
        """Calculate the pharmacokinetics outputs of the timecourse subset.

        The calculated outputs are bulk created.
        """
        # calculate pharmacokinetics outputs
        try:
            outputs = pkoutputs_from_timecourse(subset)
        except Exception as err:
            raise serializers.ValidationError(
                {"pharmacokinetics exception": traceback.format_exc()}
            ) from err

        errors = []
        for output in outputs:
            try:
                output["measurement_type"].validate_complete(output)
            except ValueError as err:
                errors.append(err)
        if errors:
            raise serializers.ValidationError(
                {"calculated outputs": errors},  # ty: ignore[invalid-argument-type]  # DRF renders any detail value with force_str, the stub type is narrower
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
        return value

    @staticmethod
    def _remove_id_to_foreign_keys(value: str):
        if "_id" in value:
            return value[:-3]
        return value

    def create_scatter(self, dimensions, shared, subset_instance):
        """Build the two-dimensional scatter data points of the subset.

        The data points are built from the study's outputs.
        """
        study = self.context["study"]
        study_outputs = study.outputs.filter(normed=True)
        if len(dimensions) != 2:
            raise serializers.ValidationError(
                f"Scatter plots have to be two dimensional. Dimensions: <{dimensions}> has a len of <{len(dimensions)}.> "
            )

        if not shared:
            raise serializers.ValidationError(
                "The <shared> field is required for scatter plots."
            )
        outputs_pd = pd.DataFrame(study_outputs.values())

        data_set = outputs_pd[outputs_pd["label"].isin(dimensions)]
        if len(data_set) == 0:
            raise serializers.ValidationError(
                {
                    "data_set": {
                        "data": [
                            {
                                "subsets": {
                                    "dimensions": f"Outputs with label <{dimensions}> do not exist."
                                }
                            }
                        ]
                    }
                }
            )

        data_set["dimension"] = None
        data_set.loc[data_set["label"] == dimensions[0], "dimension"] = 0
        data_set.loc[data_set["label"] == dimensions[1], "dimension"] = 1

        shared_reformated = []
        for shared_field in shared:
            shared_field_reformated = self._add_id_to_foreign_keys(shared_field)
            if shared_field_reformated not in data_set:
                p_options = [
                    self._remove_id_to_foreign_keys(c) for c in data_set.columns
                ]
                raise serializers.ValidationError(
                    f"Shared_field <{shared_field}> not in outputs fields. Options are <{p_options}>"
                )
            shared_reformated.append(shared_field_reformated)

        if len(data_set.groupby(shared_reformated)) == 0:
            raise serializers.ValidationError("Outputs have no values on shared field")

        subset_outputs = []
        for shared_values, shared_data in data_set.groupby(shared_reformated):
            x_data = shared_data[shared_data["dimension"] == 0]
            y_data = shared_data[shared_data["dimension"] == 1]

            if len(x_data) != 1 or len(y_data) != 1:
                if shared == ["individual"]:
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

            Dimension.objects.create(
                dimension=0,
                study=study,
                output=x_output,
                data_point=data_point_instance,
            )
            Dimension.objects.create(
                dimension=1,
                study=study,
                output=y_output,
                data_point=data_point_instance,
            )

        subset_instance.pks.add(*subset_outputs)

    def create_timecourse(self, subset_instance, dimensions):
        """Build the timecourse data points of the subset.

        The pharmacokinetics outputs of the subset are calculated.
        """
        study = self.context["study"]
        if len(dimensions) != 1:
            raise serializers.ValidationError(
                f"Timecourses have to be one-dimensional, but '{len(dimensions)}' dimensions found <{dimensions}>."
            )
        subset_outputs = study.outputs.filter(normed=True, label=dimensions[0])
        if len(subset_outputs) == 0:
            raise serializers.ValidationError(
                f"Timecourses cannot be empty. No outputs found <{dimensions[0]}>."
            )
        if len(subset_outputs) == 1:
            raise serializers.ValidationError(
                f"Timecourses require at least two outputs, but only a single output exists in timecourse. "
                f"Encode the label <{dimensions[0]}> as 'output_type=output' instead of 'output_type=timecourse'."
            )
        subset_instance.pks.add(*subset_outputs)
        if not subset_outputs.exists():
            raise serializers.ValidationError(
                {
                    "dataset": {
                        "data": [
                            {
                                "subsets": {
                                    "name": f"Outputs with label <{dimensions}> do not exist."
                                }
                            }
                        ]
                    }
                }
            )

        dimensions = []
        for output in subset_outputs.iterator():
            data_point_instance = DataPoint.objects.create(subset=subset_instance)

            dimension = Dimension(
                dimension=0, study=study, output=output, data_point=data_point_instance
            )
            dimensions.append(dimension)
        Dimension.objects.bulk_create(dimensions)

        self.calculate_pks_from_timecourses(subset_instance)


class DataSerializer(ExSerializer):
    """Serializer for uploading a named data figure or table and its subsets."""

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
        fields = ["name", "data_type", "comments", "descriptions", "image", "subsets"]

    def to_internal_value(self, data):
        """Validate that no unexpected keys are present in the uploaded data."""
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
        """Create the data instance and its subsets."""
        study = self.context["study"]
        data_instance, poped_data = _create(
            model_manager=self.Meta.model.objects,
            validated_data={**validated_data, "dataset": study.dataset},
            create_multiple_keys=["comments", "descriptions"],
            pop=["subsets"],
        )

        for subset in poped_data["subsets"]:
            _, poped_data = _create(
                model_serializer=SubSetSerializer(context=self.context),
                validated_data={**subset, "data": data_instance},
                create_multiple_keys=["comments", "descriptions"],
            )
        return data_instance


class DataSetSerializer(ExSerializer):
    """Serializer for uploading a study's data set.

    The data set consists of the data figures/tables and their subsets.
    """

    data = DataSerializer(many=True, read_only=False, required=False, allow_null=True)
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = DataSet
        fields = ["data", "comments", "descriptions"]

    def _validate_unique_names(self, data_container):
        names = []
        for data_single in data_container:
            if data_single.get("name") in names:
                raise serializers.ValidationError(
                    {
                        "name": f"Duplicated name <{data_single.get('name')}>. Consider writing the name "
                        f"in the to the excel sheet. By mapping the name field {{'name':'col==*'}} the instances are"
                        f" automatically groupby the name."
                    }
                )

            names.append(data_single.get("name"))
            subset_names = []
            for subset in data_single.get("subsets", []):
                if subset.get("name") in subset_names:
                    raise serializers.ValidationError(
                        f"Subsets with same names are not allowed within one data instance. "
                        f"Data instance <{data_single.get('name')}> contains multiple subsets with name <{subset.get('name')}>."
                    )
                subset_names.append(subset.get("name"))

    def to_internal_value(self, data):
        """Split and expand the uploaded data and subset rows.

        The auto-generated timecourses are appended afterwards.
        """
        self.validate_wrong_keys(data)

        # parse special formatting:
        data_container = []
        for data_unsplitted in data.get("data", []):
            temp_data = self.split_entry(data_unsplitted)
            for data_single in temp_data:
                subsets = data_single.get("subsets")
                if subsets:
                    temp_subsets = []
                    for subset in subsets:
                        temp_subsets.extend(self.split_entry(subset))
                    data_single["subsets"] = temp_subsets
                data_container.extend(self.entries_from_file(data_single))
        self.validate_no_timeocourses(data_container)
        autogenerate_timecourses = self.autogenerate_timecourses()
        if autogenerate_timecourses:
            data_container.append(autogenerate_timecourses)

        data["data"] = data_container
        return super().to_internal_value(data)

    def validate_no_timeocourses(self, data):
        """Raise ValidationError for an explicitly declared timecourse.

        A data entry declared with data_type=timecourse is rejected.
        """
        for data_single in data:
            if data_single.get("data_type") == Data.DataTypes.Timecourse:
                raise serializers.ValidationError(
                    "timecourses are not allowed to be definied explictly in dataset. "
                    "Timecourses are created automatically by adding label "
                    "and output_type='timecourse' to the respective outputs."
                )

    def autogenerate_timecourses(self):
        """Build a data entry which groups the timecourse outputs by label.

        The grouped outputs are the timecourse outputs of the study. None is
        returned when the study has no such output.
        """
        # Study = apps.get_model('studies', 'Study')

        study_sid = self.context["request"].path.split("/")[-2]
        outputs = Output.objects.filter(
            study__sid=study_sid, normed=True, output_type=Output.OutputTypes.Timecourse
        )
        timecourse_labels = outputs.values_list("label", flat=True).distinct()
        if len(timecourse_labels) > 0:
            return {
                "name": "AutoGenerate",
                "data_type": "timecourse",
                "subsets": [
                    {"name": label, "dimensions": [label]}
                    for label in timecourse_labels
                ],
            }
        return None

    def validate(self, attrs):
        """Validate that data and subset names are unique within the data set."""
        self._validate_unique_names(attrs["data"])
        return super().validate(attrs)

    def create(self, validated_data):
        """Create the data set and its data instances."""
        dataset_instance, poped_data = _create(
            model_manager=self.Meta.model.objects,
            validated_data=validated_data,
            create_multiple_keys=["comments", "descriptions"],
            pop=["data"],
        )
        data_instance_container = []
        for data_single in poped_data["data"]:
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
    """Read-only serializer for a subset's timecourse array.

    The array is flattened into per-field columns.
    """

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

    @staticmethod
    @lru_cache(maxsize=128)
    def _get_general(obj):
        """This function reshapes and reformats the outputs to a Pandas DataFrame."""
        obj = [v["point"][0] for v in json.loads(obj)["array"]]
        result = pd.DataFrame(obj)
        return result.where(result.notnull(), None)

    def _get_field(self, obj, field):
        result = self._get_general(json.dumps(obj.to_dict()))
        if result[field].isnull().all():
            return None
        return list(result[field].values)

    def get_output_pk(self, obj):
        """Return the primary keys of the subset's outputs."""
        self._get_general(json.dumps(obj.to_dict()))
        return self._get_field(obj, "pk")

    def get_intervention_pk(self, obj):
        """Return the primary keys of the interventions of the subset's first output."""
        result = self._get_general(json.dumps(obj.to_dict()))
        return [i["pk"] for i in result["interventions"].iloc[0]]

    def get_group_pk(self, obj):
        """Return the primary key of the subset's group, or None if it has none."""
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["group"][0]:
            return result["group"][0]["pk"]
        return None

    def get_individual_pk(self, obj):
        """Return the primary key of the subset's individual, or None if it has none."""
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["individual"][0]:
            return result["individual"][0]["pk"]
        return None

    def get_normed(self, obj):
        """Return whether the subset's outputs are normalized."""
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["normed"][0]

    def get_tissue(self, obj):
        """Return the sid of the subset's tissue info node, or None if it has none."""
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["tissue"][0]:
            return result["tissue"][0]["sid"]
        return None

    def get_tissue_label(self, obj):
        """Return the label of the subset's tissue info node, or None if it has none."""
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["tissue"][0]:
            return result["tissue"][0]["label"]
        return None

    def get_method(self, obj):
        """Return the sid of the subset's method info node, or None if it has none."""
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["method"][0]:
            return result["method"][0]["sid"]
        return None

    def get_method_label(self, obj):
        """Return the label of the subset's method info node, or None if it has none."""
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["method"][0]:
            return result["method"][0]["label"]
        return None

    def get_label(self, obj):
        """Return the subset's label."""
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["label"][0]

    def get_time(self, obj):
        """Return the subset's time values."""
        return self._get_field(obj, "time")

    def get_time_unit(self, obj):
        """Return the subset's time unit."""
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["time_unit"][0]

    def get_measurement_type(self, obj):
        """Return the sid of the subset's measurement type info node."""
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["measurement_type"][0]["sid"]

    def get_measurement_type_label(self, obj):
        """Return the label of the subset's measurement type info node."""
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["measurement_type"][0]["label"]

    def get_choice(self, obj):
        """Return the sid of the subset's choice info node, or None if it has none."""
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["choice"][0]:
            return result["choice"][0]["sid"]
        return None

    def get_choice_label(self, obj):
        """Return the label of the subset's choice info node, or None if it has none."""
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["choice"][0]:
            return result["choice"][0]["label"]
        return None

    def get_substance(self, obj):
        """Return the sid of the subset's substance info node.

        None is returned when the subset has no substance info node.
        """
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["substance"][0]:
            return result["substance"][0]["sid"]
        return None

    def get_substance_label(self, obj):
        """Return the label of the subset's substance info node.

        None is returned when the subset has no substance info node.
        """
        result = self._get_general(json.dumps(obj.to_dict()))
        if result["substance"][0]:
            return result["substance"][0]["label"]
        return None

    def get_value(self, obj):  # ty: ignore[invalid-method-override]  # the SerializerMethodField named value requires get_value, which collides with Field.get_value
        """Return the subset's values."""
        return self._get_field(obj, "value")

    def get_mean(self, obj):
        """Return the subset's means."""
        return self._get_field(obj, "mean")

    def get_median(self, obj):
        """Return the subset's medians."""
        return self._get_field(obj, "median")

    def get_min(self, obj):
        """Return the subset's mins."""
        return self._get_field(obj, "min")

    def get_max(self, obj):
        """Return the subset's maxs."""
        return self._get_field(obj, "max")

    def get_sd(self, obj):
        """Return the subset's standard deviations."""
        return self._get_field(obj, "sd")

    def get_se(self, obj):
        """Return the subset's standard errors."""
        return self._get_field(obj, "se")

    def get_cv(self, obj):
        """Return the subset's coefficients of variation."""
        return self._get_field(obj, "cv")

    def get_unit(self, obj):
        """Return the subset's unit."""
        result = self._get_general(json.dumps(obj.to_dict()))
        return result["unit"][0]

    class Meta:
        fields = [
            "study_sid",
            "study_name",
            "output_pk",
            "intervention_pk",
            "group_pk",
            "individual_pk",
            "normed",
            "calculated",
            *OUTPUT_FIELDS,
            *MEASUREMENTTYPE_FIELDS,
        ]


class SubSetElasticSerializer(DocumentSerializer):
    """Elasticsearch serializer for a subset (scatter or timecourse).

    The array and the timecourse fields are serialized as well.
    """

    study = StudySmallElasticSerializer(read_only=True)
    name = serializers.CharField()
    data_type = serializers.CharField()
    array = serializers.SerializerMethodField()

    class Meta:
        document = SubSetDocument
        fields = ["pk", "study", "name", "data_type", "array", "timecourse"]

    def get_array(self, object):
        """Return the subset's array of data points as a plain list."""
        return [point["point"] for point in object.to_dict()["array"]]


class DataSetElasticSmallSerializer(serializers.ModelSerializer):
    """Elasticsearch serializer for a data set.

    The serialized fields are the descriptions, the comments and the subset
    primary keys.
    """

    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    subsets = serializers.SerializerMethodField()

    class Meta:
        model = DataSet
        fields = ["pk", "descriptions", "comments", "subsets"]
        read_only_fields = fields

    def get_subsets(self, obj):
        """Return the primary keys of the data set's subsets."""
        return list_of_pk("subsets", obj)


class DataAnalysisSerializer(serializers.ModelSerializer):
    """Elasticsearch serializer for a single dimension of a data analysis row."""

    class Meta:
        model = Dimension
        fields = [
            "study_sid",
            "study_name",
            "data_pk",
            "data_name",
            "data_type",
            "subset_pk",
            "subset_name",
            "data_point_pk",
            "output_pk",
            "dimension",
        ]
        read_only_fields = fields
