import bonobo
import pandas as pd
import os
import sys
import json

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)

from pkdb_app.data_management.fill_database import get_study_json_path, open_study
from pkdb_app.data_management.create_reference import DOSINGPATH, ensure_dir
from pkdb_app.data_management.initialize_study import save_study, SEPERATOR
from pkdb_app.utils import create_if_exists, clean_import

def add_intervention_to_study(study):
    dosing_pd = pd.read_csv(DOSINGPATH, delimiter='\t')
    study_json = {**study["json"]}
    study_json["interventionset"] = {}
    this_interventions = dosing_pd[dosing_pd["study"] == study_json["name"]]
    this_interventions.replace({'NA':None}, inplace=True)

    try:
        test = this_interventions["dosing_details"].unique()[0]
        study_json["interventionset"]["description"] = SEPERATOR.join(this_interventions["dosing_details"].unique())
    except IndexError:
        print( f'{study_json["name"]}:has no Interventions')

    study_json["interventionset"]["interventions"] = []

    for i, row in this_interventions.iterrows():
        intervention_json = {}
        intervention_json["name"] = row["dosing"]
        intervention_json["substance"] = row["substance"]
        intervention_json["time"] = row["times"]
        intervention_json["time_unit"] = row["times_unit"]
        intervention_json["route"] = row["route"]
        intervention_json["value"] = row["dose"]
        intervention_json["unit"] = row["dose_unit"]
        study_json["interventionset"]["interventions"].append(clean_import(intervention_json))

    yield {"json":study_json,"study_path": study["study_path"]}



def save_reference(d):
    ensure_dir(d["interventions_file"])
    with open(d["interventions_file"], 'a') as fp:
        json.dump(d['json'], fp, indent=4)


def get_graph_study(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_study_json_path,
        open_study,
        add_intervention_to_study,
        save_study,
    )
    return graph

def get_services(**options):
    return {}


if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph_study(**options), services=get_services(**options))
