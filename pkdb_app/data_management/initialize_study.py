"""
Creates study.py json files in master folder with group infrmation
"""



import bonobo
import pandas as pd
import numpy as np
import json
import os
import sys

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)

from pkdb_app.data_management.create_reference import collect_reference, add_reference_path, ensure_dir

MK = "Matthias König"
MK_u = "mkoenig"
JG_u = "janekg"
JG = "Jan Grzeogrzewski"
SUBSTANCES = ["caffeine",]
pkdb_version = 1.0
study_filename = "study.json"
SEPERATOR = "||"

def study_create(reference):
    #create json for study
    json = {"sid": reference["sid"]}
    json["pkdb_version"] = pkdb_version
    json["creator"] = MK_u
    json["name"] = reference["name"]
    json["substances"] = SUBSTANCES
    json["reference"] = reference["sid"]
    json["curators"] = [MK_u, JG_u]
    study_path = os.path.join(reference["reference_path"],study_filename)
    return {"json":json, "study_path":study_path}


def save_study(d):
    json_file = os.path.join(d["study_path"])
    ensure_dir(json_file)
    with open(json_file, 'w') as fp:
        json.dump(d['json'],fp, indent=4, ensure_ascii=False,)


def get_graph(**options):
    graph = bonobo.Graph()

    # add reference information
    graph.add_chain(*collect_reference)

    #add studies
    graph.add_chain(
        study_create,
        save_study,
        _input=add_reference_path,
    )
    return graph


def get_services(**options):
    return {}

if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph(**options), services=get_services(**options))
