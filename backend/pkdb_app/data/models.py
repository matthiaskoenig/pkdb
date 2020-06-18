from django.db import models
from pkdb_app.behaviours import Accessible
from pkdb_app.utils import CHAR_MAX_LENGTH
from django.utils.translation import gettext_lazy as _


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


