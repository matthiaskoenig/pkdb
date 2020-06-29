import traceback

from pkdb_app.comments.serializers import DescriptionSerializer, CommentSerializer
from pkdb_app.data.models import DataSet, Data, SubSet, Dimension, DataPoint
from pkdb_app.outputs.models import Output
from pkdb_app.outputs.pk_calculation import pkoutputs_from_timecourse
from pkdb_app.outputs.serializers import OUTPUT_FOREIGN_KEYS
from pkdb_app.serializers import WrongKeyValidationSerializer, ExSerializer
from pkdb_app.subjects.models import DataFile
from pkdb_app.utils import _create, create_multiple_bulk, create_multiple_bulk_normalized
from rest_framework import serializers
import pandas as pd
import numpy as np

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
        fields = ['name', "descriptions",  "comments", "dimensions", "shared"]

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        return data


    def create(self, validated_data):
        subset_instance, poped_data = _create(model_manager=self.Meta.model.objects,
                                              validated_data=validated_data,
                                              create_multiple_keys=['comments', 'descriptions'],
                                              pop=['dimensions', 'shared'])

        if subset_instance.data.data_type in  ["scatter","fictve_scatter"]:
            kwargs = {**poped_data, 'subset_instance': subset_instance}
            self.create_scatter(**kwargs)
        elif subset_instance.data.data_type == "timecourse":
            kwargs = {'subset_instance': subset_instance}
            self.create_timecourse(**kwargs)
        # subset_instance.save()
        return subset_instance

    def validate_timecourse(self):
        raise NotImplementedError

    def _validate_interventions(self, data):
        # all outputs of an timecourse have to share the same interventions.
        raise NotImplementedError

    def _validate_time(self, time):
        if any(np.isnan(np.array(time))):
            raise serializers.ValidationError({"time": "no time points are allowed to be nan", "detail": time})



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

        outputs_dj = create_multiple_bulk(subset, "timecourse", outputs, Output)

        for intervention, output in zip(interventions,outputs_dj):
            output.interventions.add(*intervention)

        if outputs_dj:
            outputs_normed = create_multiple_bulk_normalized(outputs_dj, Output)
            for output in outputs_normed:
                output.interventions.add(*output.raw.interventions.all())
        subset.save()

    @staticmethod
    def _add_id_to_foreign_keys(value:str):
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
        outputs_pd = pd.DataFrame(study_outputs.values())

        data_set = outputs_pd[outputs_pd['label'].isin(dimensions)]
        if len(data_set) == 0:
            raise serializers.ValidationError(
                {"data_set":{"data":[{"subsets":{"dimensions":f"Outputs with label <{dimensions}> do not exist."}}]}})

        data_set["dimension"] = None
        data_set.loc[data_set['label'] == dimensions[0],'dimension'] = 0
        data_set.loc[data_set['label'] == dimensions[1],'dimension'] = 1

        shared_reformated = []
        for shared_field in shared:
            shared_field_reformated = self._add_id_to_foreign_keys(shared_field)
            if shared_field_reformated not in data_set:

                p_options = [self._remove_id_to_foreign_keys(c) for c in data_set.columns]
                raise serializers.ValidationError(f"Shared_field <{shared_field}> not in outputs fields. Options are <{p_options}>")
            shared_reformated.append(shared_field_reformated)

        if len(data_set.groupby(shared_reformated)) == 0:
            raise serializers.ValidationError(
                f"Outputs have no values on shared field")

        for shared_values, shared_data in data_set.groupby(shared_reformated):
            x_data = shared_data[shared_data["dimension"] == 0]
            y_data = shared_data[shared_data["dimension"] == 1]


            if len(x_data) != 1 or len(y_data) != 1:
                raise serializers.ValidationError(
                f"Dimensions <{dimensions}> do not match in respect to the shared fields."
                f"The shared field <{shared}> with values <{shared_values}>"
                f" do not uniquely assign 1 x output to 1 y output. "
                f"<{dimensions[0]}> has <{len(x_data)}> outputs. <{dimensions[1]}> has <{len(y_data)}> outputs."
                )
            data_point_instance = DataPoint.objects.create(subset=subset_instance)

            Dimension.objects.create(dimension=0,
                                     study=study,
                                     output=study_outputs.get(pk=x_data["id"]),
                                     data_point=data_point_instance)
            Dimension.objects.create(dimension=1,
                                     study=study,
                                     output=study_outputs.get(pk=y_data["id"]),
                                     data_point=data_point_instance)



    def create_timecourse(self, subset_instance):
        study = self.context["study"]
        subset_outputs = study.outputs.filter(normed=True,label=subset_instance.name)
        if not subset_outputs.exists():
            raise serializers.ValidationError(
                {"dataset": {"data": [
                    {"subsets": {"name": f" Outputs with label <{subset_instance.name}> do not exist."}}]}})

        dimensions = []
        for output in subset_outputs.iterator():
            data_point_instance = DataPoint.objects.create(subset=subset_instance)
            dimension = Dimension(dimension=0,study=study, output=output,data_point=data_point_instance)
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
        subsets = []
        self.validate_wrong_keys(data)
        for subset in data.get('subsets', []):
            temp_subsets = self.split_entry(subset)
            #for splitted_subset in temp_subsets:
            #    subsets.extend(self.entries_from_file(splitted_subset))
        data['subsets'] = temp_subsets
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

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)

        # parse special formatting:
        data_container = []
        for data_single in data.get('data', []):
            temp_data = self.split_entry(data_single)
            for splitted_data in temp_data:
                data_container.extend(self.entries_from_file(splitted_data))
        data['data'] = data_container

        return super().to_internal_value(data)


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
