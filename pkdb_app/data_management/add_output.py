import bonobo
import pandas as pd
import os,sys
BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)


from pkdb_app.data_management.fill_database import get_study_json_path, open_study
from pkdb_app.data_management.create_reference import PHARMACOKINETICSPATH
from pkdb_app.data_management.initialize_study import save_study
from pkdb_app.utils import create_if_exists, clean_import


def add_outputs_to_study(study):
    dosing_pd = pd.read_csv(PHARMACOKINETICSPATH, delimiter='\t')
    study_json = {**study["json"]}
    study_json["outputset"] = {}
    study_json["outputset"]["description"] = ""
    study_json["outputset"]["outputs"] = []

    study_output = dosing_pd[dosing_pd["study"] == study_json["name"]]
    for name, data in study_output.groupby(["subjects", "dosing","substance"]):
        output = {}
        output["group"] = name[0]
        output["intervention"] = name[1]

        output["substance"] = name[2]

        for i, row in data.iterrows():

            output["pktype"] = row["pktype"]
            output["value"] = row["value"]
            output['tissue'] = row["tissue"]
            output['sd'] = row["sd"]
            output['se'] = row["se"]
            output['cv'] = row["cv"]
            output['min'] = row["min"]
            output['max'] = row["max"]
            output['unit'] = row["unit"]

        study_json["outputset"]["outputs"].append(clean_import(output))

    yield {"json":study_json,"study_path": study["study_path"]}

def get_graph_study(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_study_json_path,
        open_study,
        add_outputs_to_study,
        save_study,
    )
    return graph

def get_services(**options):
    return {}


if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph_study(**options), services=get_services(**options))


