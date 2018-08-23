import os
import sys
from pprint import pprint
import pandas as pd
import bonobo

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)

from pkdb_app.data_management.fill_database import get_study_paths, read_study_json
from pkdb_app.data_management.initialize_study import save_study, study_filename, SEPERATOR
from pkdb_app.categoricals import CHARACTERISTIC_CATEGORIES,CHARACTERISTIC_DTYPE
from pkdb_app.data_management.create_reference_caffeine import SUBJECTSPATH, INDIVIDUALPATH
from pkdb_app.utils import create_if_exists, clean_import


def add_groupset_to_study(study):
    study_json = {**study["json"]}
    subject_pd = pd.read_csv(SUBJECTSPATH,delimiter='\t',keep_default_na=False)
    this_subject = subject_pd[subject_pd["reference"] == study_json["name"]]
    this_subject = this_subject.replace({'NA':None})
    #this_subject.columns = [c.replace('_', ' ') for c in this_subject.columns]
    study_json["groupset"] = {}
    try:
        test = this_subject["description"].unique()[0]
        study_json["groupset"]["description"] = SEPERATOR.join(this_subject["description"].unique())
    except IndexError:
        print( f'{study_json["name"]}: has no group')

    if len(this_subject) > 1:
        study_json["groupset"]["characteristica"] = []
    study_json["groupset"]["groups"] = []

    for group in this_subject.itertuples():
        #print(group.reset_index().to_dict())
        #print(group)
        #print(group.to_dict("records"))
        yield {"json": study_json,"group": group._asdict(), "study_path": study["study_path"]}


def add_group_to_groupset(data):

    data_group = { k.replace('_', ' '):v for k,v in data["group"].items()}
    print(data_group)
    #add groupsets
    #######################################################
    group = {}

    group["count"] = data["group"]["count"]
    group["name"] = data["group"]["groups"]
    #group["description"] = data["group"]["description"]
    group["characteristica"] = add_characteristic_values(data_group)
    json = {**data["json"]}
    json["groupset"]["groups"].append(group)
    return {"json":json, "study_path":data["study_path"]}

def add_characteristica_groupset(data):

    this_data = {**data}
    groups = this_data["json"]["groupset"]["groups"]
    number_of_groups = len(groups)

    if number_of_groups > 1:
        new_groups =[]
        for group in groups:
            new_chara = []
            for characteristica in group['characteristica']:
                characteristica.pop("count",None)
                new_chara.append(tuple(characteristica.items()))
            new_groups.append(set(new_chara))

        groupset_chara_tuples = set.intersection(*new_groups)
        groupset_dict = [dict(x) for x in groupset_chara_tuples]
        this_data["json"]["groupset"]["characteristica"] = groupset_dict

        new_groups = [group - groupset_chara_tuples for group in new_groups]
        groups_dict = [list(map(dict,x)) for x in new_groups]

        for i, group in enumerate(groups_dict):
            this_data["json"]["groupset"]["groups"][i]['characteristica'] = group

    return this_data


def add_individual_set(data):
    this_data = {**data}
    individials_pd = pd.read_csv(INDIVIDUALPATH, delimiter='\t', keep_default_na=False)
    this_individuals = individials_pd[individials_pd["study"] == this_data["json"]["name"]]
    this_individuals.replace({'NA': None}, inplace=True)

    if len(this_individuals) > 0:
        this_data["json"]["individualset"] = {}

        this_data["json"]["individualset"]["description"] = ""
        this_data["json"]["individualset"]["individuals"] = []

        for individuals in this_individuals.itertuples():
            individuals_dict_raw = individuals._asdict()
            individuals_dict_raw = {k.replace('_', ' '): v for k, v in individuals_dict_raw.items()}

            individuals_dict = {}
            individuals_dict["name"] =  individuals_dict_raw["name"]
            individuals_dict["group"] =  individuals_dict_raw["group"]
            individuals_dict["source"] =  individuals_dict_raw["source"]
            individuals_dict["format"] =  individuals_dict_raw["format"]
            individuals_dict["figure"] =  individuals_dict_raw["figure"]
            individuals_dict['characteristica'] = add_characteristic_values(individuals_dict_raw)
            this_data["json"]["individualset"]["individuals"].append(clean_import(individuals_dict))


    return this_data




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
        group["count"] = group.get("count",1)
        if "new_count" in group:
            numeric_data["count"] = group["new_count"]

        if group["count"] > 1:
            numeric_data = create_if_exists(group,category,numeric_data,"mean")
            numeric_data = create_if_exists(group,f"{category} median",numeric_data,"median")
            numeric_data = create_if_exists(group,f"{category} min",numeric_data,"min")
            numeric_data = create_if_exists(group,f"{category} max",numeric_data,"max")
            numeric_data = create_if_exists(group,f"{category} sd",numeric_data,"sd")
            numeric_data = create_if_exists(group,f"{category} se",numeric_data,"se")
            numeric_data = create_if_exists(group,f"{category} cv",numeric_data,"cv")

        else:
            numeric_data = create_if_exists(group,category,numeric_data,"value")

        numeric_data = create_if_exists(group, f"{category} unit", numeric_data, "unit")

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
        get_study_paths,
        read_study_json,
        add_groupset_to_study,
        add_group_to_groupset,
        save_study,
    )
    return graph


def get_graph_groupset_chara(**options):
    graph = bonobo.Graph()
    graph.add_chain(
            get_study_paths,
            read_study_json,
            add_characteristica_groupset,
            save_study,
    )
    return graph

def get_graph_groupset_individual(**options):
    graph = bonobo.Graph()
    graph.add_chain(
            get_study_paths,
            read_study_json,
            add_individual_set,
            save_study,
    )
    return graph
def get_services(**options):
    return {}


if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph_study(**options), services=get_services(**options))
        bonobo.run(get_graph_groupset_chara(**options), services=get_services(**options))
        bonobo.run(get_graph_groupset_individual(**options), services=get_services(**options))
