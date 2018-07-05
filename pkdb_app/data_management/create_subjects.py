"""
Creates json files in master folder
"""
from fill_database import get_reference_json_path,open_json
from create_master import SUBJECTSPATH, save_json, add_reference_path
from categoricals import CHARACTERISTIC_CATEGORIES
import bonobo
import pandas as pd




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
    group["characteristics_values"] = add_characteristic_values(data["group"])

    json = {**data["json"]}
    json["groups"].append(group)
    return {"json":json, "reference_path":add_reference_path(json)["reference_path"]}


def add_characteristic_values(group):
    characteristics_values = []
    for value in CHARACTERISTIC_CATEGORIES:
        value_dict = {}
        value_dict["value"] = value
        value_dict["choice"] = group.get(value)
        characteristics_values.append(value_dict)
        #process_characteristic_values(category_dict)
    return characteristics_values


def process_characteristic_values(data):
    if "/" in data["choice"]:
        data["choice"].split("/")



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
