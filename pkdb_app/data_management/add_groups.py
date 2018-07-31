import os
import sys

import pandas as pd
import bonobo

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)

from pkdb_app.data_management.fill_database import get_study_json_path, open_study
from pkdb_app.data_management.initialize_study import save_study, study_filename, SEPERATOR
from pkdb_app.categoricals import CHARACTERISTIC_CATEGORIES,CHARACTERISTIC_DTYPE
from pkdb_app.data_management.create_reference import SUBJECTSPATH

from pkdb_app.utils import create_if_exists, clean_import


def add_groupset_to_study(study):
    study_json = {**study["json"]}
    subject_pd = pd.read_csv(SUBJECTSPATH,delimiter='\t',keep_default_na=False)
    this_subject = subject_pd[subject_pd["reference"] == study_json["name"]]
    this_subject.replace({'NA':None}, inplace=True)

    study_json["groupset"] = {}
    try:
        test = this_subject["description"].unique()[0]
        study_json["groupset"]["description"] = SEPERATOR.join(this_subject["description"].unique())
    except IndexError:
        print( f'{study_json["name"]}: has no group')

    study_json["groupset"]["groups"] = []

    for group in this_subject.itertuples():
        yield {"json": study_json,"group": group._asdict(), "study_path": study["study_path"]}


def add_group_to_groupset(data):
    #add groupsets
    #######################################################
    group = {}
    group["count"] = data["group"]["count"]
    group["name"] = data["group"]["groups"]
    group["description"] = data["group"]["description"]
    group["characteristica"] = add_characteristic_values(data["group"])
    json = {**data["json"]}
    json["groupset"]["groups"].append(group)
    return {"json":json, "study_path":data["study_path"]}

def add_characteristic_values(group):
    characteristics_values = []
    for category in CHARACTERISTIC_CATEGORIES:
        for characteristics_value in process_characteristic_values(group,category):
            temp_characteristics_value = {**characteristics_value}
            for key in ["category","count"]:
                temp_characteristics_value.pop(key,None)
            if not temp_characteristics_value == {}:
                characteristics_values.append(characteristics_value)
    return characteristics_values

def process_characteristic_values(group,category):
    this_value = str(group.get("category",""))
    if this_value.strip().replace('.','',1).isdigit() or CHARACTERISTIC_DTYPE[category] == "numeric":

        numeric_data = {}
        numeric_data["category"] = category
        if "new_count" in group:
            numeric_data["count"] = group["new_count"]

        if group["count"] > 1:
            numeric_data = create_if_exists(group,category,numeric_data,"mean")
            numeric_data = create_if_exists(group,f"{category}_median",numeric_data,"median")
            numeric_data = create_if_exists(group,f"{category}_min",numeric_data,"min")
            numeric_data = create_if_exists(group,f"{category}_max",numeric_data,"max")
            numeric_data = create_if_exists(group,f"{category}_sd",numeric_data,"sd")
            numeric_data = create_if_exists(group,f"{category}_se",numeric_data,"se")
            numeric_data = create_if_exists(group,f"{category}_cv",numeric_data,"cv")
            numeric_data = create_if_exists(group,f"{category}_unit",numeric_data,"unit")

        else:
            numeric_data = create_if_exists(group,category,numeric_data,"float")


        return [clean_import(numeric_data)]

    else:
        categorical_data = {}
        if "new_count" in group:
            categorical_data["count"] = group["new_count"]



        categorical_data["category"] = category
        categorical_data = create_if_exists(group, category, categorical_data, "choice")

        return [clean_import(categorical_data)]

def get_graph_study(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_study_json_path,
        open_study,
        add_groupset_to_study,
        add_group_to_groupset,
        save_study,
    )
    return graph

def get_services(**options):
    return {}


if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph_study(**options), services=get_services(**options))
