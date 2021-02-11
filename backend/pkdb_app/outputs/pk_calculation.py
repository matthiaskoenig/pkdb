"""
Calculate pharmacokinetics
"""
from typing import List, Dict
from rest_framework import serializers
import logging
import warnings
import numpy as np
from django.apps import apps
from pkdb_app.info_nodes.units import ureg
from pkdb_analysis.pk import pharmacokinetics

logger = logging.getLogger(__name__)

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
    timecourse = subset.timecourse
    dosing = subset.get_single_dosing(timecourse["substance"])

    # dosing information must exist
    if not dosing:
        return outputs

    # pharmacokinetics are only calculated on normalized concentrations

    if timecourse["measurement_type_name"] == "concentration":
        variables = _timecourse_to_pkdict(timecourse, dosing)
        ctype = variables.pop("ctype", None)

        if dosing.application.info_node.name == "single dose" and timecourse["substance"] == dosing.substance.pk:
            pkinf = pharmacokinetics.TimecoursePK(**variables)
        else:
            _ = variables.pop("dosing", None)
            _ = variables.pop("intervention_time", None)
            pkinf = pharmacokinetics.TimecoursePKNoDosing(**variables)

        pk = pkinf.pk

        from pprint import pprint
        pprint(variables)
        pprint(pk)

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
                output_dict["tissue"] = get_or_none(timecourse["tissue"], model=Tissue)
                output_dict["method"] = get_or_none(timecourse["method"], model=Method)
                output_dict["substance"] = get_or_none(id=timecourse["substance"], model=Substance)
                output_dict["group"] =  get_or_none(id=timecourse["group"],model=Group)
                output_dict["individual"] = get_or_none(timecourse["individual"], model=Individual)
                output_dict["interventions"] = timecourse["interventions"]
                output_dict["study"] = dosing.study
                if output_dict["measurement_type"].info_node.name == "auc_end":
                    output_dict["time"] = max(timecourse["time"])
                    output_dict["time_unit"] = str(timecourse["time_unit"])

                outputs.append(output_dict)

    return outputs


def _timecourse_to_pkdict(tc: dict, dosing) -> Dict:

    """Create dictionary for pk calculation from timecourse.

    :return: dict
    """
    pk_dict = {}
    Q_ = ureg.Quantity
    pk_dict['ureg'] = ureg  # for unit conversions

    # substance
    pk_dict["substance"] = tc["substance_name"]
    # time
    pk_dict["time"] = Q_(np.array(tc["time"]), tc["time_unit"])

    # concentratio
    values = None
    ctype = None
    if tc["mean"]:
        values = np.array(tc["mean"])
        ctype = "mean"
    elif tc["median"]:
        values = tc["median"]
        ctype = "median"
    elif tc["value"]:
        values = np.array(tc["value"])
        ctype = "value"
    if ctype is not None:
        pk_dict["concentration"] = Q_(values, tc["unit"])
        pk_dict['ctype'] = ctype

    # dosing
    pk_dict["dose"] = Q_(np.nan, "mg")

    if dosing:
        if dosing.substance.pk == tc["substance"]:
            # pharmacokinetics is only calculated for single dose experiments
            # where the applied substance is the measured substance!

            if MeasurementType.objects.get(info_node__name="restricted dosing")._is_valid_unit(dosing.unit):
                if dosing.value is not None:
                    pk_dict["dose"] = Q_(dosing.value, dosing.unit)
                else:
                    warnings.warn(f"restricted dosing requires value: {dosing}")
                if dosing.time is not None:
                    pk_dict["intervention_time"] = Q_(dosing.time, dosing.time_unit)
    return pk_dict
