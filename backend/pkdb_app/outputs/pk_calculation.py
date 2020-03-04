"""
Calculate pharmacokinetics
"""
from typing import List, Dict
import numpy as np
import pandas as pd
from django.apps import apps
from pkdb_app.info_nodes.units import ureg
from pkdb_analysis.pk import pharmacokinetics

MeasurementType = apps.get_model('info_nodes.MeasurementType')
Output = apps.get_model('outputs.Output')
Timecourse = apps.get_model('outputs.Timecourse')


def pkoutputs_from_timecourse(tc: Timecourse) -> List[Dict]:
    """Calculates pharmacokinetics outputs for timecourse.

    :param tc: models.Timecourse
    :return:
    """
    outputs = []
    tc_type = tc.measurement_type.info_node.name

    if tc_type == "concentration" and tc.normed:
        # pharmacokinetics are only calculated on normalized concentrations

        variables = tc.timecourse_to_pkdict()
        c_type = variables.pop("c_type", None)
        _ = variables.pop("bodyweight_type", None)

        pk = pharmacokinetics.f_pk(**variables)

        key_mapping = {
            "auc": MeasurementType.objects.get(info_node__name="auc_end"),
            "aucinf": MeasurementType.objects.get(info_node__name="auc_inf"),
            "cl": MeasurementType.objects.get(info_node__name="clearance"),
            "cmax": MeasurementType.objects.get(info_node__name="cmax"),
            "kel": MeasurementType.objects.get(info_node__name="kel"),
            "thalf": MeasurementType.objects.get(info_node__name="thalf"),
            "tmax": MeasurementType.objects.get(info_node__name="tmax"),
            "vd": MeasurementType.objects.get(info_node__name="vd"),
        }

        for key in ["auc", "aucinf", "cl", "cmax", "kel", "thalf", "vd", "tmax"]:
            pk_unit = pk[f"{key}_unit"]
            if not np.isnan(pk[key]):
                output_dict = {}
                output_dict[c_type] = pk[key]
                output_dict["unit"] = pk_unit
                output_dict["measurement_type"] = key_mapping[key]
                output_dict["calculated"] = True
                output_dict["tissue"] = tc.tissue
                output_dict["substance"] = tc.substance
                output_dict["group"] = tc.group
                output_dict["individual"] = tc.individual
                if output_dict["measurement_type"].info_node.name == "auc_end":
                    output_dict["time"] = max(tc.time)
                    output_dict["time_unit"] = tc.time_unit
                output_dict["study"] = tc.study
                outputs.append(output_dict)

    return outputs


def timecourse_to_pkdict(tc: Timecourse) -> Dict:
    """Create dictionary for pk calculation from timecourse.

    :return: dict
    """
    pk_dict = {}

    # substance
    pk_dict["compound"] = tc.substance.info_node.name

    bodyweight = tc.get_bodyweight().first()

    # time
    pk_dict["t"] = pd.Series(tc.time)
    pk_dict["t_unit"] = tc.time_unit

    # concentration
    # FIXME: the timecourse data must be filtered based on the dosing times
    #   (or alternatively this should be handled in the pk calculation)
    pk_dict["c_unit"] = tc.unit

    if tc.mean:
        pk_dict["c"] = pd.Series(tc.mean)
        pk_dict["c_type"] = "mean"

    elif tc.median:
        pk_dict["c"] = pd.Series(tc.median)
        pk_dict["c_type"] = "median"

    elif tc.value:
        pk_dict["c"] = pd.Series(tc.value)
        pk_dict["c_type"] = "value"

    # dosing
    dosing = tc.get_dosing()
    if dosing:
        if dosing.substance == tc.substance:
            if MeasurementType.objects.get(info_node__name="restricted dosing").is_valid_unit(dosing.unit):
                p_unit_dosing = tc.measurement_type.p_unit(dosing.unit)
                p_unit_concentration = tc.measurement_type.p_unit(pk_dict["c_unit"])
                vd_unit = p_unit_dosing / p_unit_concentration
                pk_dict["vd_unit"] = str(vd_unit)
                pk_dict["dose"] = dosing.value
                if dosing.time:
                    # convert dosing time in units of the timecourse
                    pk_dict["intervention_time"] = (ureg(dosing.time_unit) * dosing.time).to(
                        tc.time_unit).magnitude

                pk_dict["dose_unit"] = dosing.unit

    # bodyweight dependent values
    if bodyweight:
        pk_dict["bodyweight_unit"] = bodyweight.unit

        if bodyweight.value:
            pk_dict["bodyweight"] = bodyweight.value
            pk_dict["bodyweight_type"] = "value"

        elif bodyweight.mean:
            pk_dict["bodyweight"] = bodyweight.mean
            pk_dict["bodyweight_type"] = "mean"

        elif bodyweight.median:
            pk_dict["bodyweight"] = bodyweight.median
            pk_dict["bodyweight_type"] = "median"

    return pk_dict
