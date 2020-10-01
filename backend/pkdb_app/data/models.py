import itertools
from collections import Iterable

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from django.utils.functional import cached_property
from pkdb_app.behaviours import Accessible
from pkdb_app.interventions.models import Intervention
from pkdb_app.utils import CHAR_MAX_LENGTH
from django.utils.translation import gettext_lazy as _
import pandas as pd
from django.apps import apps


class DataSet(models.Model):
    """
    DataSet adds context to the outputs. Here, already uploaded outputs can be grouped to datasets and subsets. These subsets respresent
    e.g. the data points of a timecourse, or the data points of a scatter plot.
    """
    @property
    def subsets(self):
        return self.study.subsets


class Data(models.Model):
    """
    These are mostly scatter or timecourses.
    """
    class DataTypes(models.TextChoices):
        """ Data Types. """
        Scatter = 'scatter', _('scatter')
        Timecourse = 'timecourse', _('timecourse')

    name = models.CharField(max_length=CHAR_MAX_LENGTH)  # e.g. Fig3
    data_type = models.CharField(max_length=CHAR_MAX_LENGTH,
                                 choices=DataTypes.choices)  # options are scatter, timecourse, ...
    image = models.ForeignKey('subjects.DataFile', related_name="data", on_delete=models.CASCADE, null=True)
    dataset = models.ForeignKey(DataSet, related_name="data", on_delete=models.CASCADE, null=True)


class SubSet(Accessible):
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    data = models.ForeignKey(Data, related_name="subsets", on_delete=models.CASCADE)
    study = models.ForeignKey('studies.Study', on_delete=models.CASCADE, related_name="subsets")

    def get_single_dosing(self) -> Intervention:
        """Returns a single intervention of type dosing if existing.
        If multiple dosing interventions exist, no dosing is returned!.
        """
        try:
            dosing_measurement_type = Intervention.objects.filter(id__in=self.interventions).get(
                normed=True, measurement_type__info_node__name="dosing"
            )
            return dosing_measurement_type

        except (ObjectDoesNotExist, MultipleObjectsReturned):
            return None

    @property
    def array(self):
        [point.values_list("output") for point in self.data_points]
        return self.data.data_type

    @property
    def data_type(self):
        return self.data.data_type

    @property
    def outputs(self):
        return self.data_points.values_list('outputs', flat=True)

    @property
    def interventions(self):
        return self.data_points.values_list('outputs__interventions', flat=True)

    def timecourse_extra_no_intervention(self):
        return {
            'output': 'outputs__pk',
            'measurement_type': 'outputs__measurement_type',
            'measurement_type_name': 'outputs__measurement_type__info_node__name',
            'tissue': 'outputs__tissue',
            'tissue_name': 'outputs__tissue__info_node__name',
            'method': 'outputs__method',
            'method_name': 'outputs__method__info_node__name',
            'substance': 'outputs__substance',
            'substance_name': 'outputs__substance__info_node__name',
            'group': 'outputs__group',
            'individual': 'outputs__individual',
            'time': 'outputs__time',
            'value': 'outputs__value',
            'mean': 'outputs__mean',
            'median': 'outputs__median',
            'cv': 'outputs__cv',
            'sd': 'outputs__sd',
            'se': 'outputs__se',
            'time_unit': 'outputs__time_unit',
            'unit': 'outputs__unit',
        }
    def keys_timecourse_representation(self):
        return {
            "study_sid":"outputs__study__sid",
            "study_name": "outputs__study__name",
            "outputs_pk": "outputs__pk",
            "subset_pk": "subset_id",
            "subset_name": "subset__name",
            "interventions": "outputs__interventions__pk",
            "group_pk": "outputs__group_id",
            "individual_pk": "outputs__individual_id",
            "normed": 'outputs__normed',
            "calculated": 'outputs__calculated',
            "tissue": 'outputs__tissue__info_node__sid',
            "tissue_label": 'outputs__tissue__info_node__label',
            "method": 'outputs__method__info_node__sid',
            "method_label": 'outputs__method__info_node__label',
            "label": 'outputs__label',
            "output_type": 'outputs__output_type',
            "time": 'outputs__time',
            'time_unit': 'outputs__time_unit',
            "measurement_type":	"outputs__measurement_type__info_node__sid",
            "measurement_type__label": "outputs__measurement_type__info_node__label",
            "choice":	"outputs__choice__info_node__sid",
            "choice_label": "outputs__choice__info_node__label",
            "substance": "outputs__substance__info_node__sid",
            "substance_label": "outputs__substance__info_node__label",
            "value": 'outputs__value',
            "mean": 'outputs__mean',
            "median": 'outputs__median',
            "min": 'outputs__min',
            "max": 'outputs__max',
            'sd': 'outputs__sd',
            'se': 'outputs__se',
            'cv': 'outputs__cv',
            'unit': 'outputs__unit',
        }

    def _timecourse_extra(self):
        return {
            **self.timecourse_extra_no_intervention(),
            'label': 'outputs__label',
            'application': 'outputs__interventions__application',
            'application_name': 'outputs__interventions__application__info_node__name',
            'interventions': 'outputs__interventions__pk',
            'interventions_measurement_type': 'outputs__interventions__measurement_type',
            'interventions_substance': 'outputs__interventions__substance',

        }

    @staticmethod
    def none_tuple(values):
        if isinstance(values, Iterable):
            if all(pd.isna(v) for v in values):
                return (None,)
        return tuple(values)

    @staticmethod
    def to_list(tdf):
        return tdf.apply(SubSet.none_tuple).apply(SubSet.tuple_or_value)

    @staticmethod
    def tuple_or_value(values):
        if len(set(values)) == 1:
            return list(values)[0]
        return values

    @staticmethod
    def _tuple_or_value(values):
        if len(set(values)) == 1:
            return list(values)[0]
        return tuple(values)

    @staticmethod
    def merge_values(values=None ,df=None, groupby=("outputs__pk",), sort_values=["outputs__interventions__pk","outputs__time"]):

        if values:
            df =pd.DataFrame(values)
        if sort_values:
            df = df.sort_values(sort_values)
        merged_dict = df.groupby(list(groupby), as_index=False).apply(SubSet.to_list).to_dict("list")

        for key, values in merged_dict.items():
            if key not in ['outputs__time', 'outputs__value', 'outputs__mean', 'outputs__median', 'outputs__cv',
                           'outputs__sd' 'outputs__se']:

                merged_dict[key] = SubSet.tuple_or_value(values)

            if all(v is None for v in values):
                merged_dict[key] = None

        return merged_dict

    def get_name(self, values, Model):
        if isinstance(values, int):
            return Model.objects.get(pk=values).name
        else:
            return [self.get_name(value, Model) for value in values]

    def validate_timecourse(self, timecourse):
        unique_values = {
            "interventions": Intervention,
            "application_name": None,
            "measurement_type_name": None,
            "tissue_name": None,
            "method_name": None,
            "substance_name": None,
            "group": apps.get_model("subjects.Group"),
            "individual": apps.get_model("subjects.Individual"),
            "unit": None,
            "time_unit": None,
        }
        for key, value in unique_values.items():
            if isinstance(timecourse[key], list):
                if value:
                    name = self.get_name(timecourse[key], value)
                else:
                    name = list(timecourse[key])
                raise ValueError(f"Subset used for timecourse is not unique on '{key}'. Values are '{name}'. "
                                 f"Check uniqueness of labels for timecourses.")

    @cached_property
    def timecourse(self):
        """ FIXME: Documentation """
        tc = self.merge_values(
            self.data_points.prefetch_related('outputs').values(*self._timecourse_extra().values()),
            sort_values=["outputs__interventions__pk", "outputs__time"]
        )
        self.reformat_timecourse(tc, self._timecourse_extra())
        self.validate_timecourse(tc)
        return tc

    def reformat_timecourse(self, timecourse, mapping):
        """ FIXME: Documentation & type hinting """
        for new_key, old_key in mapping.items():
            timecourse[new_key] = timecourse.pop(old_key)
            if new_key == "interventions":
                if isinstance(timecourse[new_key], int):
                    timecourse[new_key] = (timecourse[new_key],)

    @cached_property
    def timecourse_representation(self):
        """ FIXME: Documentation """
        timecourse = self.merge_values(
            self.data_points.values(*self.keys_timecourse_representation().values()),)
        self.reformat_timecourse(timecourse, self.keys_timecourse_representation())
        return timecourse

    def keys_scatter_representation(self):
        """ FIXME: Documentation """
        return {**self.keys_timecourse_representation(),
                "dimension": "dimensions__dimension",
                "data_point": "pk"
        }

    @cached_property
    def scatter_representation(self):
        scatter_x = self.merge_values(self.data_points.filter(dimensions__dimension=0).values(*self.keys_scatter_representation().values()), sort_values=None)
        self.reformat_timecourse(scatter_x, self.keys_scatter_representation())

        scatter_y = self.merge_values(self.data_points.filter(dimensions__dimension=1).prefetch_related('outputs').values(*self.keys_scatter_representation().values()),sort_values=None)
        self.reformat_timecourse(scatter_y, self.keys_scatter_representation())

        identical_keys = ["study_sid", "study_name", "subset_pk", "subset_name"]

        return {**{k: v for k, v in scatter_x.items() if k in identical_keys},
                **{f"x_{k}": v for k, v in scatter_x.items() if k not in identical_keys},
                **{f"y_{k}": v for k, v in scatter_y.items() if k not in identical_keys}}

class DataPoint(models.Model):
    """
    A DataSetPoint can have multiple dimensions. These dimensions are spanned by outputs.
    """
    subset = models.ForeignKey(SubSet, related_name="data_points", on_delete=models.CASCADE)
    outputs = models.ManyToManyField('outputs.Output', through="Dimension", related_name="data_points")


class Dimension(Accessible):
    """
    """

    dimension = models.IntegerField()
    data_point = models.ForeignKey(DataPoint, related_name="dimensions", on_delete=models.CASCADE)
    output = models.ForeignKey('outputs.Output', related_name="dimensions", on_delete=models.CASCADE)
    study = models.ForeignKey('studies.Study', on_delete=models.CASCADE, related_name="dimensions")

    @property
    def data_pk(self):
        return self.data_point.subset.data.pk

    @property
    def data_name(self):
        return self.data_point.subset.data.name

    @property
    def data_type(self):
        return self.data_point.subset.data.data_type

    @property
    def subset_pk(self):
        return self.data_point.subset.pk

    @property
    def subset_name(self):
        return self.data_point.subset.name

    @property
    def data_point_pk(self):
        return self.data_point.pk

    @property
    def output_pk(self):
        return self.output.pk
