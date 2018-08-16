import bonobo
import pandas as pd
import os,sys
BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)


from pkdb_app.data_management.fill_database import get_study_paths, read_study_json
from pkdb_app.data_management.create_reference_caffeine import PHARMACOKINETICSPATH, TIMECOURSEPATH, OUTPUTINDIVIDUALPATH
from pkdb_app.data_management.initialize_study import save_study
from pkdb_app.utils import create_if_exists, clean_import

def inizialize_output(study):
    study_json = {**study["json"]}
    study_json["outputset"] = {}
    study_json["outputset"]["description"] = ""
    study_json["outputset"]["outputs"] = []
    yield {"json": study_json, "study_path": study["study_path"]}

def add_outputs_to_study(study):
    dosing_pd = pd.read_csv(PHARMACOKINETICSPATH, delimiter='\t')
    study_json = {**study["json"]}

    study_output = dosing_pd[dosing_pd["study"] == study_json["name"]]
    for name, data in study_output.groupby(["subjects", "dosing","substance"]):
        output = {}
        output["group"] = name[0]
        interventions = name[1].split(",")
        output["interventions"] = list(map(str.strip,interventions))


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

def add_timecourse_to_ouput(data):
    this_data = {**data}
    timecourse_pd = pd.read_csv(TIMECOURSEPATH, delimiter='\t', keep_default_na=False, encoding="utf-8")
    this_timecourse = timecourse_pd[timecourse_pd["study"] == this_data["json"]["name"]]
    this_timecourse.replace({'NA': None}, inplace=True)

    if len(this_timecourse) > 0:
        this_data["json"]["outputset"]["timecourse"] = []
        for timecourse in this_timecourse.itertuples(index=False):
            timecourse_dict = timecourse._asdict()
            timecourse_dict.pop("study")
            if ("interventions" in timecourse_dict and timecourse_dict["interventions"]):
                timecourse_dict["interventions"] = list(
                    map(str.strip, timecourse_dict["interventions"].split(",")))

            this_data["json"]["outputset"]["timecourse"].append(clean_import(timecourse_dict))


    return this_data

def add_individualmapping_to_ouput(data):
    this_data = {**data}
    individuals_output_pd = pd.read_csv(OUTPUTINDIVIDUALPATH, delimiter='\t', keep_default_na=False, encoding="utf-8")
    this_individuals_output = individuals_output_pd[individuals_output_pd["study"] == this_data["json"]["name"]]
    this_individuals_output.replace({'NA': None}, inplace=True)

    if len(this_individuals_output) > 0:
        for individuals_output in this_individuals_output.itertuples(index=False):
            individuals_output_dict = individuals_output._asdict()
            individuals_output_dict.pop("study")
            if ("interventions" in individuals_output_dict and individuals_output_dict["interventions"]):
                individuals_output_dict["interventions"] = list(map(str.strip,individuals_output_dict["interventions"].split(",")))

            this_data["json"]["outputset"]["outputs"].append(clean_import(individuals_output_dict))
    return this_data


def get_graph_study(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_study_paths,
        read_study_json,
        inizialize_output,
        add_individualmapping_to_ouput,
        add_timecourse_to_ouput,
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


