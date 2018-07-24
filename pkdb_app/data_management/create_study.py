"""
Creates json files in master folder
"""
from create_reference import collect_reference, add_reference_path, SUBJECTSPATH, ensure_dir
from categoricals import CHARACTERISTIC_CATEGORIES,CHARACTERISTIC_DTYPE
import bonobo
import pandas as pd
import numpy as np
import json
import os


def study_load(reference):
    data_pd = pd.read_csv(SUBJECTSPATH,delimiter='\t')
    this_data = data_pd[data_pd["reference"] == reference["name"]]
    json = {"sid": reference["sid"]}
    json["name"] = reference["name"]
    json["reference"] = reference["sid"]
    json["groups"] = []

    for name, row in this_data.iterrows():
        yield {"json": json, "group": row.to_dict(),"reference": reference}

def add_subject_to_json(data):
    group = {}
    group["count"] = data["group"]["count"]
    group["name"] = f'{data["json"]["name"]}-{data["group"]["groups"]}'
    group["description"] = data["group"]["description"]
    group["characteristic_values"] = add_characteristic_values(data["group"])

    json = {**data["json"]}
    json["groups"].append(group)
    return {"json":json, "study_path":data["reference"]["reference_path"]}


def add_characteristic_values(group):
    characteristics_values = []
    for category in CHARACTERISTIC_CATEGORIES:
        for characteristics_value in process_characteristic_values(group,category):
            temp_characteristics_value = {**characteristics_value}
            for key in ["category","count"]:
                temp_characteristics_value.pop(key,None)
            if not all(value is None for value in temp_characteristics_value.values()):
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
        if str(value) == "NA":
            group[key] = None
        if str(value) == "None":
            group[key] = None
        if str(value) == "-":
            group[key] = None


def clean_dict(d):
    return {k: v for k, v in d.items() if v is not None}


def process_characteristic_values(group,category):
    remove_nans(group)

    this_value = str(group.get(category,""))

    if "|" in this_value:
        characteristic_values = []
        counts_and_choices = this_value.split("|")
        for count_and_choice in counts_and_choices:
            count , choice = count_and_choice.split()
            this_group = {**group}
            this_group["new_count"] = count
            this_group[category] = choice
            characteristic_values += process_characteristic_values(this_group,category)
        return characteristic_values

    elif this_value.strip().replace('.','',1).isdigit() or CHARACTERISTIC_DTYPE[category] == "numeric":
        numeric_data = {}
        numeric_data["category"] = category

        if "new_count" in group:
            numeric_data["count"] = group["new_count"]

        if group["count"] > 1:
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

        return [clean_dict(numeric_data)]



    else:
        categorical_data = {}
        if "new_count" in group:
            categorical_data["count"] = group["new_count"]

        categorical_data["category"] = category
        categorical_data["choice"] = group.get(category,None)
        return [clean_dict(categorical_data)]





def save_json(d):
    json_file = os.path.join(d["study_path"],"study.json")
    ensure_dir(json_file)
    with open(json_file, 'w') as fp:
        json.dump(d['json'],fp, indent=4)





def get_graph(**options):
    graph = bonobo.Graph()

    # add reference information
    graph.add_chain(*collect_reference)
    graph.add_chain()

    #add studies
    graph.add_chain(
        study_load,
        add_subject_to_json,
        save_json,
        _input=add_reference_path,
    )
    return graph




def get_services(**options):
    return {}


if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph(**options), services=get_services(**options))
