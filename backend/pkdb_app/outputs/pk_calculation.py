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

    # pharmacokinetics are only calculated on normalized concentrations
    if tc_type == "concentration" and tc.normed:
        variables = timecourse_to_pkdict(tc)
        c_type = variables.pop("c_type", None)

        pkinf = pharmacokinetics.PKInference(**variables)
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
            "vdss": MeasurementType.objects.get(info_node__name="vdss"),
        }

        for key in key_mapping.keys():
            pk_par = getattr(pk, key)
            if not np.isnan(pk[key]):
                output_dict = {}
                output_dict[c_type] = pk_par.magnitude
                output_dict["unit"] = pk_par.units
                output_dict["measurement_type"] = key_mapping[key]
                output_dict["calculated"] = True
                output_dict["tissue"] = tc.tissue
                output_dict["substance"] = tc.substance
                output_dict["group"] = tc.group
                output_dict["individual"] = tc.individual
                output_dict["study"] = tc.study
                if output_dict["measurement_type"].info_node.name == "auc_end":
                    output_dict["time"] = max(tc.time)
                    output_dict["time_unit"] = tc.time_unit

                outputs.append(output_dict)

    return outputs


def timecourse_to_pkdict(tc: Timecourse) -> Dict:
    """Create dictionary for pk calculation from timecourse.

    :return: dict
    """
    pk_dict = {}
    
    # substance
    pk_dict["substance"] = tc.substance.info_node.name

    # time
    pk_dict["t"] = pd.Series(tc.time)
    pk_dict["t_unit"] = tc.time_unit

    # concentration
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

    return pk_dict
