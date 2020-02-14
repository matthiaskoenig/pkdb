from django.apps import apps
from pkdb_app.analysis.pharmacokinetic import f_pk
import numpy as np
def _calculate_outputs(timecourse):
    outputs = []
    MeasurementType = apps.get_model('info_nodes.MeasurementType')

    if timecourse.measurement_type.info_node.name == "concentration" and timecourse.normed:
        variables = timecourse.get_pharmacokinetic_variables()
        c_type = variables.pop("c_type", None)
        _ = variables.pop("bodyweight_type", None)
        pk = f_pk(**variables)

        key_mapping = {"auc": MeasurementType.objects.get(info_node__name="auc_end"),
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
                output_dict["tissue"] = timecourse.tissue
                output_dict["substance"] = timecourse.substance
                output_dict["group"] = timecourse.group
                output_dict["individual"] = timecourse.individual
                if output_dict["measurement_type"].info_node.name == "auc_end":
                    output_dict["time"] = max(timecourse.time)
                    output_dict["time_unit"] = timecourse.time_unit
                output_dict["study"] = timecourse.study
                outputs.append(output_dict)
    return outputs