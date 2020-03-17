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
        ctype = variables.pop("ctype", None)

        pkinf = pharmacokinetics.TimecoursePK(**variables)
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

        for key in key_mapping.keys():
            pk_par = getattr(pk, key)
            # check that exists
            if pk_par and not np.isnan(pk_par.magnitude):
                output_dict = {}
                output_dict[ctype] = pk_par.magnitude
                output_dict["unit"] = str(pk_par.units)
                output_dict["measurement_type"] = key_mapping[key]
                output_dict["calculated"] = True
                output_dict["tissue"] = tc.tissue
                output_dict["substance"] = tc.substance
                output_dict["group"] = tc.group
                output_dict["individual"] = tc.individual
                output_dict["study"] = tc.study
                if output_dict["measurement_type"].info_node.name == "auc_end":
                    output_dict["time"] = max(tc.time)
                    output_dict["time_unit"] = str(tc.time_unit)

                outputs.append(output_dict)

    return outputs


def timecourse_to_pkdict(tc: Timecourse) -> Dict:
    """Create dictionary for pk calculation from timecourse.

    :return: dict
    """
    pk_dict = {}
    Q_ = ureg.Quantity
    pk_dict['ureg'] = ureg  # for unit conversions

    # substance
    pk_dict["substance"] = tc.substance.info_node.name
    # time
    pk_dict["time"] = Q_(pd.Series(tc.time).values, tc.time_unit)

    # concentration
    values = None
    ctype = None
    if tc.mean:
        values = pd.Series(tc.mean).values
        ctype = "mean"
    elif tc.median:
        values = pd.Series(tc.median).values
        ctype = "median"
    elif tc.value:
        values = pd.Series(tc.value).values
        ctype = "value"
    if ctype is not None:
        pk_dict["concentration"] = Q_(values, tc.unit)
        pk_dict['ctype'] = ctype

    # dosing
    pk_dict["dose"] = Q_(np.nan, "mg")

    dosing = tc.get_dosing()
    if dosing:
        if dosing.substance == tc.substance:
            if MeasurementType.objects.get(info_node__name="restricted dosing").is_valid_unit(dosing.unit):
                pk_dict["dose"] = Q_(dosing.value, dosing.unit)
                if dosing.time:
                    pk_dict["intervention_time"] = Q_(dosing.time, dosing.time_unit)

    return pk_dict
