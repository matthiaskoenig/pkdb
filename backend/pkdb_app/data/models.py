
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from pkdb_app.behaviours import Accessible
from pkdb_app.interventions.models import Intervention
from pkdb_app.utils import CHAR_MAX_LENGTH
from django.utils.translation import gettext_lazy as _
import pandas as pd

class DataSet(models.Model):
    """
    DataSet adds context to the outputs. Here, already uploaded outputs can be grouped to datasets and subsets. These subsets respresent
    e.g. the data points of a timecourse, or the data points of a scatter plot.
    """


class Data(models.Model):
    """
    A Data  These are mostly scatterplots or timecourses.
    """
    class DataTypes(models.TextChoices):
        """ Data Types. """
        Scatter = 'scatter', _('scatter')
        Timecourse = 'timecourse', _('timecourse')

    name = models.CharField(max_length=CHAR_MAX_LENGTH) # e.g. Fig3
    data_type = models.CharField(max_length=CHAR_MAX_LENGTH, choices=DataTypes.choices)  # options are scatter, timecourse, ...
    image = models.ForeignKey('subjects.DataFile', related_name="data", on_delete=models.CASCADE, null=True)
    dataset = models.ForeignKey(DataSet, related_name="data", on_delete=models.CASCADE, null=True)


class SubSet(models.Model):
    """

    """
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    data = models.ForeignKey(Data, related_name="subsets", on_delete=models.CASCADE)

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
    def outputs(self):
        return self.data_points.values_list('outputs', flat=True)

    @property
    def interventions(self):
        return self.data_points.values_list('outputs__interventions', flat=True)

    def _timecourse_extra(self):
        return {
            'interventions':'outputs__interventions',
            'interventions__measurement_type': 'outputs__interventions__measurement_type',
            'interventions__substance': 'outputs__interventions__substance',
            'application':'outputs__interventions__application',
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

    def timecourse(self):
        return self.data_points.prefetch_related('outputs').values(*self._timecourse_extra().values())

    def timecourse_df(self):
        return pd.DataFrame(self.timecourse()).rename(columns={v:k for k,v in self._timecourse_extra().items()})



class DataPoint(models.Model):
    """
    A DataSetPoint can have multiple dimensions. These dimensions are spanned by outputs.
    """
    subset = models.ForeignKey(SubSet, related_name="data_points", on_delete=models.CASCADE)
    outputs = models.ManyToManyField('outputs.Output', through="Dimension")


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


