"""
Creates json files in master folder
"""
from fill_database import get_reference_json_path,open_json
from create_master import SUBJECTSPATH, save_json, add_reference_path
from categoricals import CHARACTERISTIC_CATEGORIES,CHARACTERISTIC_DTYPE
import bonobo
import pandas as pd
import numpy as np
import math


def subjects_load(json_reference):
    data_pd = pd.read_csv(SUBJECTSPATH,delimiter='\t')
    this_data = data_pd[data_pd["reference"] == json_reference["json"]["sid"]]
    json = {**json_reference["json"]}
    json["groups"] = []
    for name, row in this_data.iterrows():
        yield {"json": json, "group": row.to_dict()}




def add_subject_to_json(data):
    group = {}
    group["count"] = data["group"]["count"]
    group["sid"] = f'{data["json"]["sid"]}-{data["group"]["groups"]}'
    group["description"] = data["group"]["description"]
    group["characteristic_values"] = add_characteristic_values(data["group"])

    json = {**data["json"]}
    json["groups"].append(group)
    return {"json":json, "reference_path":add_reference_path(json)["reference_path"]}


def add_characteristic_values(group):
    characteristics_values = []
    for category in CHARACTERISTIC_CATEGORIES:
        for characteristics_value in process_characteristic_values(group,category):
            characteristics_values.append(characteristics_value)
    return characteristics_values

def remove_nans(group):
    for key, value in group.items():
        if value is np.NaN:
            group[key] = None
        if str(value) == "nan":
            group[key] = None
        if str(value) == "":
            group[key] = None
        if str(value) == "NANS":
            group[key] = None
        if str(value) == "None":
            group[key] = None





def process_characteristic_values(group,category):
    remove_nans(group)
    this_value = str(group.get(category,""))

    if "|" in this_value:
        characteristic_values = []
        counts_and_choices = this_value.split("|")
        for count_and_choice in counts_and_choices:
            count , choice = count_and_choice.split()
            this_group = {**group}
            this_group["count"] = count
            this_group[category] =  choice
            characteristic_values += process_characteristic_values(this_group,category)
        return characteristic_values

    elif this_value.strip().replace('.','',1).isdigit() or CHARACTERISTIC_DTYPE[category] == "numeric":
        numeric_data = {}
        numeric_data["category"] = category
        #numeric_data["choice"] = None
        numeric_data["count"] = group["count"]
        if numeric_data["count"] > 1:

            numeric_data["mean"] = group.get(category, None)
            numeric_data["median"] = group.get(f"{category}_median",None)
            numeric_data["min"] = group.get(f"{category}_min",None)
            numeric_data["max"] = group.get(f"{category}_max",None)
            numeric_data["sd"] = group.get(f"{category}_sd",None)
            numeric_data["se"] = group.get(f"{category}_se",None)
            numeric_data["cv"] = group.get(f"{category}_cv",None)
            numeric_data["unit"] = group.get(f"{category}_unit",None)
        else:
            numeric_data["float"] = group.get(category, None)

        return [numeric_data]



    else:
        categorical_data = {}
        categorical_data["count"] = group.get("count",None)
        categorical_data["category"] = category
        categorical_data["choice"] = group.get(category,None)
        return [categorical_data]











def get_graph(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_reference_json_path,
        open_json,
        subjects_load,
        add_subject_to_json,
        save_json,
    )
    return graph




def get_services(**options):
    return {}


if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph(**options), services=get_services(**options))
