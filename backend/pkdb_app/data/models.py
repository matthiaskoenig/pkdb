"""Django models for data sets, subsets and data points.

The data points build the timecourses and the scatters.
"""

from collections.abc import Iterable
from typing import TYPE_CHECKING, Optional

import pandas as pd
from django.apps import apps
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from pkdb_app.behaviours import Accessible
from pkdb_app.interventions.models import Intervention
from pkdb_app.utils import CHAR_MAX_LENGTH

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager

    from pkdb_app.studies.models import Study


class DataSet(models.Model):
    """Add context to outputs by grouping them into datasets and subsets.

    The grouped outputs are already uploaded. These subsets represent, for
    example, the data points of a timecourse or of a scatter plot.
    """

    if TYPE_CHECKING:
        # reverse relation of the one to one field Study.dataset
        study: "Study"

    @property
    def subsets(self):
        """Return the subsets of the study this data set belongs to."""
        return self.study.subsets


class Data(models.Model):
    """A study's named figure or table, e.g. Fig3.

    The figure or table contains scatter or timecourse data.
    """

    class DataTypes(models.TextChoices):
        """The kinds of data a Data instance can hold: scatter or timecourse."""

        Scatter = "scatter", _("scatter")
        Timecourse = "timecourse", _("timecourse")

    name = models.CharField(max_length=CHAR_MAX_LENGTH)  # e.g. Fig3
    data_type = models.CharField(
        max_length=CHAR_MAX_LENGTH, choices=DataTypes.choices
    )  # options are scatter, timecourse, ...
    image = models.ForeignKey(
        "subjects.DataFile", related_name="data", on_delete=models.CASCADE, null=True
    )
    dataset = models.ForeignKey(
        DataSet, related_name="data", on_delete=models.CASCADE, null=True
    )


class Timecourseable(models.Model):
    """Abstract mixin providing the timecourse and scatter representations.

    The representations are built from the data points.
    """

    if TYPE_CHECKING:
        # every concrete subclass declares the data foreign key and is the
        # target of the reverse relation DataPoint.subset
        data: "Data"
        data_points: "RelatedManager[DataPoint]"

    class Meta:
        abstract = True

    def output_pk(self):
        """Return the primary keys of the outputs of this instance's data points."""
        return self.data_points.values_list("outputs__pk")

    @cached_property
    def timecourse(self):
        """Build and return the merged timecourse dict.

        The dict is built from this instance's data points.
        """
        tc = self.merge_values(
            self.data_points.prefetch_related("outputs").values(
                *self._timecourse_extra().values()
            ),
            sort_values=["outputs__interventions__pk", "outputs__time"],
        )
        self.reformat_timecourse(tc, self._timecourse_extra())
        self.validate_timecourse(tc)
        return tc

    def reformat_timecourse(self, timecourse, mapping):
        """Rename the keys of the timecourse dict per mapping.

        A single intervention pk is wrapped into a tuple.
        """
        for new_key, old_key in mapping.items():
            timecourse[new_key] = timecourse.pop(old_key)
            if new_key in ["intervention_pk", "interventions"] and isinstance(
                timecourse[new_key], int
            ):
                timecourse[new_key] = (timecourse[new_key],)

    @cached_property
    def timecourse_representation(self):
        """Return the merged timecourse dict of this instance.

        None is returned when the data of the instance is not a timecourse.
        """
        if self.data.data_type == Data.DataTypes.Timecourse:
            timecourse = self.merge_values(
                self.data_points.values(
                    *self.keys_timecourse_representation().values()
                ),
            )
            self.reformat_timecourse(timecourse, self.keys_timecourse_representation())
            return timecourse
        return None

    def timecourse_extra_no_intervention(self):
        """Return the mapping of timecourse dict keys to queryset value paths.

        The intervention fields are excluded.
        """
        return {
            "output": "outputs__pk",
            "measurement_type": "outputs__measurement_type",
            "measurement_type_name": "outputs__measurement_type__info_node__name",
            "tissue": "outputs__tissue",
            "tissue_name": "outputs__tissue__info_node__name",
            "method": "outputs__method",
            "method_name": "outputs__method__info_node__name",
            "substance": "outputs__substance",
            "substance_name": "outputs__substance__info_node__name",
            "group": "outputs__group",
            "individual": "outputs__individual",
            "time": "outputs__time",
            "value": "outputs__value",
            "mean": "outputs__mean",
            "median": "outputs__median",
            "cv": "outputs__cv",
            "sd": "outputs__sd",
            "se": "outputs__se",
            "time_unit": "outputs__time_unit",
            "unit": "outputs__unit",
        }

    def keys_timecourse_representation(self):
        """Return the mapping of the timecourse representation keys.

        The keys are mapped to the queryset value paths.
        """
        return {
            "study_sid": "outputs__study__sid",
            "study_name": "outputs__study__name",
            "outputs_pk": "outputs__pk",
            "subset_pk": "subset_id",
            "subset_name": "subset__name",
            "intervention_pk": "outputs__interventions__pk",
            "group_pk": "outputs__group_id",
            "individual_pk": "outputs__individual_id",
            "normed": "outputs__normed",
            "calculated": "outputs__calculated",
            "tissue": "outputs__tissue__info_node__sid",
            "tissue_label": "outputs__tissue__info_node__label",
            "method": "outputs__method__info_node__sid",
            "method_label": "outputs__method__info_node__label",
            "label": "outputs__label",
            "output_type": "outputs__output_type",
            "time": "outputs__time",
            "time_unit": "outputs__time_unit",
            "measurement_type": "outputs__measurement_type__info_node__sid",
            "measurement_type__label": "outputs__measurement_type__info_node__label",
            "choice": "outputs__choice__info_node__sid",
            "choice_label": "outputs__choice__info_node__label",
            "substance": "outputs__substance__info_node__sid",
            "substance_label": "outputs__substance__info_node__label",
            "value": "outputs__value",
            "mean": "outputs__mean",
            "median": "outputs__median",
            "min": "outputs__min",
            "max": "outputs__max",
            "sd": "outputs__sd",
            "se": "outputs__se",
            "cv": "outputs__cv",
            "unit": "outputs__unit",
        }

    def _timecourse_extra(self):
        return {
            **self.timecourse_extra_no_intervention(),
            "label": "outputs__label",
            "application": "outputs__interventions__application",
            "application_name": "outputs__interventions__application__info_node__name",
            "interventions": "outputs__interventions__pk",
            "interventions_measurement_type": "outputs__interventions__measurement_type",
            "interventions_substance": "outputs__interventions__substance",
        }

    @staticmethod
    def none_tuple(values):
        """Return the values as a tuple.

        A single-element (None,) tuple is returned when values is iterable and
        all its entries are NaN.
        """
        if isinstance(values, Iterable) and all(pd.isna(v) for v in values):
            return (None,)
        return tuple(values)

    @staticmethod
    def to_list(tdf):
        """Apply none_tuple and tuple_or_value to the timecourse dataframe.

        Every column is converted.
        """
        return tdf.apply(SubSet.none_tuple).apply(SubSet.tuple_or_value)

    @staticmethod
    def tuple_or_value(values):
        """Return the single distinct value when all values are equal.

        Values which are not all equal are returned unchanged.
        """
        if len(set(values)) == 1:
            return next(iter(values))
        return values

    @staticmethod
    def _tuple_or_value(values):
        """Return the single distinct value when all values are equal.

        Values which are not all equal are returned as a tuple.
        """
        if len(set(values)) == 1:
            return next(iter(values))
        return tuple(values)

    @staticmethod
    def merge_values(
        values=None,
        df=None,
        groupby=("outputs__pk",),
        sort_values=("outputs__interventions__pk", "outputs__time"),
    ):
        """Sort and group the values and collapse the columns of each group.

        The rows are sorted by sort_values and grouped by groupby. A column of a
        group collapses to its single value where all rows agree and to None
        where all values are None.
        """
        if values:
            df = pd.DataFrame(values)
        if sort_values:
            df = df.sort_values(list(sort_values))  # ty: ignore[unresolved-attribute]  # known defect, reported: df stays None for empty values
        merged_dict = (
            df.groupby(list(groupby), as_index=False)  # ty: ignore[unresolved-attribute]  # known defect, reported: df stays None for empty values
            .apply(SubSet.to_list)
            .to_dict("list")
        )

        for key, values in merged_dict.items():
            if key not in [
                "outputs__time",
                "outputs__value",
                "outputs__mean",
                "outputs__median",
                "outputs__cv",
                "outputs__sdoutputs__se",
            ]:
                merged_dict[key] = SubSet.tuple_or_value(values)

            if all(v is None for v in values):
                merged_dict[key] = None

        return merged_dict

    def get_name(self, values, Model):
        """Return the name of the given Model instance.

        A list of ids in values returns the list of their names.
        """
        if isinstance(values, int):
            return Model.objects.get(pk=values).name
        return [self.get_name(value, Model) for value in values]

    def validate_timecourse(self, timecourse):
        """Raise ValueError for key values which are not unique.

        The key values of the timecourse have to be unique within the subset.
        """
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
                label = timecourse["label"]
                raise ValueError(
                    f"Subset with label '{label}' used for timecourse is not unique on '{key}'. Values are '{name}'. "
                    f"Check uniqueness of labels for timecourses."
                )


class SubSet(Accessible, Timecourseable):
    """Concrete data subset of a study.

    A subset is, for example, one timecourse or one series of a scatter plot.
    """

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    data = models.ForeignKey(Data, related_name="subsets", on_delete=models.CASCADE)
    study = models.ForeignKey(
        "studies.Study", on_delete=models.CASCADE, related_name="subsets"
    )

    def get_single_dosing(self, substance) -> Optional[Intervention]:
        """Return the single dosing intervention with the given substance, if it exists.

        If multiple dosing interventions exist, no dosing is returned.
        """
        try:
            return Intervention.objects.filter(id__in=self.interventions).get(
                normed=True,
                measurement_type__info_node__name="dosing",
                substance=substance,
            )

        except (ObjectDoesNotExist, MultipleObjectsReturned):
            return None

    @property
    def array(self):
        """Return the data type of the subset.

        The data points are iterated over first and the result is unused.
        """
        [point.values_list("output") for point in self.data_points]  # ty: ignore[not-iterable]  # known broken code, iterates the RelatedManager instead of .all()
        return self.data.data_type

    @property
    def data_type(self):
        """Return the subset's data type (scatter or timecourse)."""
        return self.data.data_type

    @property
    def outputs(self):
        """Return the primary keys of the outputs of this subset's data points."""
        return self.data_points.values_list("outputs", flat=True)

    @property
    def interventions(self):
        """Return the primary keys of the interventions of this subset's outputs."""
        return self.data_points.values_list("outputs__interventions", flat=True)

    def keys_scatter_representation(self):
        """Return the mapping of scatter representation keys to queryset value paths."""
        return {
            **self.keys_timecourse_representation(),
            "dimension": "dimensions__dimension",
            "data_point": "pk",
        }

    @cached_property
    def scatter_representation(self):
        """Build and return the combined x/y scatter dict.

        The dict is built for this subset's data points.
        """
        scatter_x = self.merge_values(
            self.data_points.filter(dimensions__dimension=0).values(
                *self.keys_scatter_representation().values()
            ),
            sort_values=None,
        )
        self.reformat_timecourse(scatter_x, self.keys_scatter_representation())

        scatter_y = self.merge_values(
            self.data_points.filter(dimensions__dimension=1)
            .prefetch_related("outputs")
            .values(*self.keys_scatter_representation().values()),
            sort_values=None,
        )
        self.reformat_timecourse(scatter_y, self.keys_scatter_representation())

        identical_keys = ["study_sid", "study_name", "subset_pk", "subset_name"]

        return {
            **{k: v for k, v in scatter_x.items() if k in identical_keys},
            **{f"x_{k}": v for k, v in scatter_x.items() if k not in identical_keys},
            **{f"y_{k}": v for k, v in scatter_y.items() if k not in identical_keys},
        }


class DataPoint(models.Model):
    """A data point of a subset, spanned by the outputs of its dimensions."""

    subset = models.ForeignKey(
        SubSet, related_name="data_points", on_delete=models.CASCADE
    )
    outputs = models.ManyToManyField(
        "outputs.Output", through="Dimension", related_name="data_points"
    )


class Dimension(Accessible):
    """One dimension (e.g. x or y) of a data point.

    The dimension links the data point to the output which spans it.
    """

    dimension = models.IntegerField()
    data_point = models.ForeignKey(
        DataPoint, related_name="dimensions", on_delete=models.CASCADE
    )
    output = models.ForeignKey(
        "outputs.Output", related_name="dimensions", on_delete=models.CASCADE
    )
    study = models.ForeignKey(
        "studies.Study", on_delete=models.CASCADE, related_name="dimensions"
    )

    @property
    def data_pk(self):
        """Return the primary key of the data this dimension's data point belongs to."""
        return self.data_point.subset.data.pk

    @property
    def data_name(self):
        """Return the name of the data this dimension's data point belongs to."""
        return self.data_point.subset.data.name

    @property
    def data_type(self):
        """Return the data type of this dimension's data point.

        The data type is scatter or timecourse.
        """
        return self.data_point.subset.data.data_type

    @property
    def subset_pk(self):
        """Return the primary key of the subset of this dimension's data point."""
        return self.data_point.subset.pk

    @property
    def subset_name(self):
        """Return the name of the subset this dimension's data point belongs to."""
        return self.data_point.subset.name

    @property
    def data_point_pk(self):
        """Return the primary key of this dimension's data point."""
        return self.data_point.pk

    @property
    def output_pk(self):
        """Return the primary key of the output that spans this dimension."""
        return self.output.pk
