from django.db import models
from pkdb_app.behaviours import Accessible
from pkdb_app.utils import CHAR_MAX_LENGTH


class Figure(models.Model):
    """
    A reported figure in publication or
    """
    outputset = models.ForeignKey('outputs.OutputSet', related_name="figures", on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=CHAR_MAX_LENGTH) # e.g. Fig3
    f_type = models.CharField(max_length=CHAR_MAX_LENGTH)  # options are scatter, timecourse, ...
    image = models.ForeignKey('subjects.DataFile', related_name="figures", on_delete=models.CASCADE, null=True)
    #study = models.ForeignKey('studies.Study', on_delete=models.CASCADE, related_name="figures")


class DataSet(models.Model):
    """
    A dataset contains dimensions a
    """
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    figure = models.ForeignKey(Figure, related_name="datasets", on_delete=models.CASCADE)


class DataSetPoint(models.Model):
    """
    A DataSetPoint can have multiple dimensions. These dimensions are spanned by outputs.
    """
    dataset = models.ForeignKey(DataSet, related_name="dataset_points", on_delete=models.CASCADE)
    outputs = models.ManyToManyField('outputs.Output', through="Dimension")


class Dimension(Accessible):
    """
    """
    d_type = models.CharField(max_length=CHAR_MAX_LENGTH)
    dataset_point = models.ForeignKey(DataSetPoint, related_name="dimensions", on_delete=models.CASCADE)
    output = models.ForeignKey('outputs.Output', related_name="dimensions", on_delete=models.CASCADE)
    study = models.ForeignKey('studies.Study', on_delete=models.CASCADE, related_name="dimensions")

    @property
    def figure_pk(self):
        return self.dataset_point.dataset.figure.pk

    @property
    def figure_name(self):
        return self.dataset_point.dataset.figure.name

    @property
    def f_type(self):
        return self.dataset_point.dataset.figure.f_type

    @property
    def dataset_pk(self):
        return self.dataset_point.dataset.pk

    @property
    def dataset_name(self):
        return self.dataset_point.dataset.name

    @property
    def dataset_point_pk(self):
        return self.dataset_point.pk