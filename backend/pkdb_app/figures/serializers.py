from pkdb_app.comments.serializers import DescriptionSerializer, CommentSerializer
from pkdb_app.figures.models import Figure, DataSet, Dimension, DataSetPoint
from pkdb_app.serializers import WrongKeyValidationSerializer, ExSerializer
from pkdb_app.subjects.models import DataFile
from pkdb_app.utils import _create
from rest_framework import serializers
import pandas as pd

class DimensionSerializer(WrongKeyValidationSerializer):
    output = serializers.CharField(write_only=True, allow_null=False, allow_blank=False)

    class Meta:
        model = Dimension
        fields = ["comments", "descriptions", "d_type", "output"]


class DataSetSerializer(WrongKeyValidationSerializer):

    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    dimensions = DimensionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    shared_fields = serializers.ListField(child=serializers.CharField(), write_only=True, allow_empty=True)

    class Meta:
        model = DataSet
        fields = ['name', "comments", "descriptions", "dimensions", "shared_fields"]

    def to_internal_value(self, data):
        return super().to_internal_value(data)


    def create_scatter(self, dataset_instance, dimensions, shared_fields,):
        study = self.context["study"]
        study_outputs = study.outputs.filter(normed=True)
        x_label = None
        y_label = None
        for dimension in dimensions:
            if dimension.get("d_type", None) == "x":
                x_label = dimension.get("output", None)
            elif dimension.get("d_type", None) == "y":
                y_label = dimension.get("output", None)
            else:
                raise serializers.ValidationError("Dimension within a figure of f_type <scatter> can only have d_type of <x> or <y>.")
        if y_label is None:
            raise serializers.ValidationError(
                "For a figure with d_type scatter a dimension with d_type <y> is required. Dimension field output cannot be empty.")
        if x_label is None:
            raise serializers.ValidationError(
                "For a figure with d_type scatter a dimension with d_type <x> is required. Dimension field output cannot be empty.")

        outputs_pd = pd.DataFrame(study_outputs.values())
        data_set = outputs_pd[outputs_pd['label'].isin([x_label,y_label])]
        if len(data_set) == 0:
            raise serializers.ValidationError(
                {"output_set":{"figures":[{"datasets":{"dimensions":f"No Outputs with label <{x_label}> or <{y_label}> in DataSet"}}]}})



        data_set["d_type"] = None

        data_set.loc[data_set['label'] == x_label,'d_type'] = 'x'
        data_set.loc[data_set['label'] == y_label,'d_type'] = 'y'


        for shared_field in shared_fields:
            if shared_field not in data_set:
                raise serializers.ValidationError(f"Shared_field not in outputs fields. Options are <{list(data_set.columns)}>")
        if len(data_set.groupby(shared_fields)) == 0:
            raise serializers.ValidationError(
                f"Outputs have no values on shared Field")
        for shared_values, shared_data in data_set.groupby(shared_fields):
            print(shared_data["label"])
            x_data = shared_data[shared_data["d_type"] == "x"]
            y_data = shared_data[shared_data["d_type"] == "y"]

            if len(x_data) != 1 or len(y_data) != 1:
                raise serializers.ValidationError(
                f"There is a problem for x outputs with label <{x_label}> and y outputs with label <{y_label}>. "
                f"The shared_fields <{shared_fields}> with values {shared_values}"
                f" cannot uniquely assign one x value to one y value."
                )
            dataset_point_instance = DataSetPoint.objects.create(dataset=dataset_instance)

            Dimension.objects.create(d_type="x",
                                     study=study,
                                     output=study_outputs.get(pk=x_data["id"]),
                                     dataset_point=dataset_point_instance)
            Dimension.objects.create(d_type="y",
                                     study=study,
                                     output=study_outputs.get(pk=y_data["id"]),
                                     dataset_point=dataset_point_instance)


    def create(self, validated_data):

        figure_instance = self.context["figure"]
        data_set_instance, poped_data = _create(model_manager=figure_instance.datasets,
                                                validated_data=validated_data,
                                                create_multiple_keys=['comments', 'descriptions'],
                                                pop=['dimensions', 'shared_fields'])

        if figure_instance.f_type == "scatter":
            kwargs = {**poped_data, 'dataset_instance':data_set_instance}
            self.create_scatter(**kwargs)
        elif figure_instance.f_type =="timecourse":
            kwargs = {'dataset_instance':data_set_instance}
            self.create_timecourse(**kwargs)
        return data_set_instance

    def create_timecourse(self, dataset_instance):
        study = self.context["study"]
        study_outputs = study.outputs.filter(normed=True)
        dataset_outputs = study_outputs.filter(label=dataset_instance.name)
        if not dataset_outputs.exists():
            raise serializers.ValidationError(
                {"output_set": {"figures": [
                    {"datasets": {"name": f"No Outputs with label <{dataset_instance.name}> in DataSet"}}]}})

        dimensions = []
        for output in dataset_outputs.iterator():
            dataset_point_instance = DataSetPoint.objects.create(dataset=dataset_instance)
            dimension = Dimension(d_type='timecourse',study=study, output=output,dataset_point= dataset_point_instance)
            dimensions.append(dimension)
        Dimension.objects.bulk_create(dimensions)


class FigureSerializer(ExSerializer):

    datasets = DataSetSerializer(many=True, read_only=False, required=False, allow_null=True)
    image = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )


    class Meta:
        model = Figure
        fields = ['name', 'datasets', 'image', 'f_type', "comments", "descriptions",]

    def to_internal_value(self, data):
        temp_datasets = data.get('datasets',[])
        datasets = []
        for dataset in temp_datasets:
             temp_datasets = self.split_entry(dataset)
             datasets.extend(temp_datasets)
        data['datasets'] = datasets
        return super().to_internal_value(data)

    def create(self, validated_data):
        figure_instance, poped_data = _create(model_manager=self.Meta.model.objects,
                                        validated_data=validated_data,
                                        create_multiple_keys=['comments', 'descriptions'],
                                        pop=['datasets'])

        datasets = poped_data["datasets"]
        for dataset in datasets:
            self.context["figure"] = figure_instance

            _create(model_serializer=DataSetSerializer(context=self.context),
                    validated_data=dataset,
                    create_multiple_keys=['comments', 'descriptions'])

        return figure_instance


################################
# Read Serializer
################################

class FigureAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dimension
        fields = ["study_sid", "figure_pk", "figure_name", ""]

        read_only_fields = fields
