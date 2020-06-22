"""
Calculate pharmacokinetics
"""
from typing import List, Dict
import warnings
import numpy as np
import pandas as pd
from django.apps import apps
from pkdb_app.info_nodes.units import ureg
from pkdb_analysis.pk import pharmacokinetics

MeasurementType = apps.get_model('info_nodes.MeasurementType')
Substance = apps.get_model('info_nodes.Substance')
Method = apps.get_model('info_nodes.Method')
Tissue = apps.get_model('info_nodes.Tissue')
Output = apps.get_model('outputs.Output')

Subset = apps.get_model('data.Subset')
Individual = apps.get_model('subjects.Individual')
Group = apps.get_model('subjects.Group')


def pkoutputs_from_timecourse(subset:Subset) -> List[Dict]:
    """Calculates pharmacokinetics outputs for timecourse.

    :param subset: models.SubSet
    :return:
    """
    outputs = []
    dosing = subset.get_single_dosing()
    if not dosing:
        # dosing information must exist
        return outputs
    # pharmacokinetics are only calculated on normalized concentrations
    timecourse_df = subset.timecourse_df()
    def validate_unique_fields(timecourse_df):
        unique_values = [
            "interventions",
            "application",
            "measurement_type",
            "tissue",
            "method",
            "substance",
            "group",
            "individual",
            "unit",
            "time_unit"
        ]
        for value in unique_values:
            if len(timecourse_df[value].unique()) != 1:
                raise Exception(f"subset used for timecourse is not unique on {value}. Intervetions are {list(timecourse_df[value])} ")

    validate_unique_fields(timecourse_df)


    if  timecourse_df.measurement_type_name.iloc[0] == "concentration":

        variables = _timecourse_to_pkdict(timecourse_df, dosing)
        ctype = variables.pop("ctype", None)
        if dosing.application.info_node.name == "single dose" and timecourse_df.substance.iloc[0] == dosing.substance.pk:
            pkinf = pharmacokinetics.TimecoursePK(**variables)

        else:
            _ = variables.pop("dosing", None)
            _ = variables.pop("intervention_time", None)
            pkinf = pharmacokinetics.TimecoursePKNoDosing(**variables)



        pk = pkinf.pk

        key_mapping = {
            "auc": MeasurementType.objects.get(info_node__name="auc_end"),
            "aucinf": MeasurementType.objects.get(info_node__name="auc_inf"),
            "cl": MeasurementType.objects.get(info_node__name="clearance"),
            "cmax": MeasurementType.objects.get(info_node__name="cmax"),
            "kel": MeasurementType.objects.get(info_node__name="kel"),
            "thalf": MeasurementType.objects.get(info_node__name="thalf"),
            "tmax": MeasurementType.objects.get(info_node__name="tmax"),
            "vd": MeasurementType.objects.get(info_node__name="vd"),
            "vdss": MeasurementType.objects.get(info_node__name="vd_ss"),
        }

        def get_or_none(id, model):
            if id:
                return model.objects.get(id=id)

        for key in key_mapping.keys():
            pk_par = getattr(pk, key, None)
            # check that exists
            if pk_par and not np.isnan(pk_par.magnitude):
                output_dict = {}
                output_dict[ctype] = pk_par.magnitude
                output_dict["unit"] = str(pk_par.units)
                output_dict["measurement_type"] = key_mapping[key]
                output_dict["calculated"] = True
                output_dict["tissue"] = get_or_none(timecourse_df.tissue.iloc[0], model=Tissue)
                output_dict["method"] = get_or_none(timecourse_df.method.iloc[0], model=Method)
                output_dict["substance"] = get_or_none(id=timecourse_df.substance.iloc[0], model=Substance)
                output_dict["group"] =  get_or_none(id=timecourse_df.group.iloc[0],model=Group)
                output_dict["individual"] = get_or_none(timecourse_df.individual.iloc[0], model=Individual)
                output_dict["interventions"] = timecourse_df.interventions.iloc[0]

                output_dict["study"] = dosing.study
                if output_dict["measurement_type"].info_node.name == "auc_end":
                    output_dict["time"] = max(timecourse_df.time)
                    output_dict["time_unit"] = str(timecourse_df.time_unit.iloc[0])

                outputs.append(output_dict)

    return outputs


def _timecourse_to_pkdict(tc: pd.DataFrame, dosing) -> Dict:
    """Create dictionary for pk calculation from timecourse.

    :return: dict
    """
    pk_dict = {}
    Q_ = ureg.Quantity
    pk_dict['ureg'] = ureg  # for unit conversions

    # substance
    pk_dict["substance"] = tc.substance_name.iloc[0]
    # time
    pk_dict["time"] = Q_(tc.time.values, tc.time_unit.iloc[0])

    # concentration
    values = None
    ctype = None
    if any(tc["mean"].values):
        values = tc["mean"].values
        ctype = "mean"
    elif any(tc["mean"].values):
        values = tc["median"].values
        ctype = "median"
    elif any(tc.value.values):
        values = tc.value.values
        ctype = "value"
    if ctype is not None:
        pk_dict["concentration"] = Q_(values, tc.unit.iloc[0])
        pk_dict['ctype'] = ctype

    # dosing
    pk_dict["dose"] = Q_(np.nan, "mg")

    if dosing:
        if dosing.substance.pk == tc.substance.iloc[0]:
            # pharmacokinetics is only calculated for single dose experiments
            # where the applied substance is the measured substance!

            if MeasurementType.objects.get(info_node__name="restricted dosing").is_valid_unit(dosing.unit):
                if dosing.value is not None:
                    pk_dict["dose"] = Q_(dosing.value, dosing.unit)
                else:
                    warnings.warn(f"restricted dosing requires value: {dosing}")
                if dosing.time is not None:
                    pk_dict["intervention_time"] = Q_(dosing.time, dosing.time_unit)

    return pk_dict
