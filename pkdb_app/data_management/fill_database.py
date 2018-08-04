import os, sys
import bonobo
import coreapi
import json
import requests

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)

from pkdb_app.data_management.create_reference import REFERENCESMASTERPATH
from jsonschema import validate
from pkdb_app.data_management.schemas import reference_schema


PASSWORD = "test"
Jan_G_U = {"username":"janekg","first_name":"Jan","last_name":"Grzegorzewski","email":"Janekg89@hotmail.de","password":PASSWORD}
Matthias_K = {"username":"mkoenig","first_name":"Matthias","last_name":"König","email":"konigmatt@googlemail.com","password":PASSWORD}

USERS = [Jan_G_U, Matthias_K]

def upload_user(USERS):
    for user in USERS:
        requests.post()

def get_reference_json_path():
    for root, dirs, files in os.walk(REFERENCESMASTERPATH, topdown=False):
        if "reference.json" in files:
            json_file = os.path.join(root, 'reference.json')
            pdf_file = os.path.join(root,f"{os.path.basename(root)}.pdf")

            yield {"json":json_file , "pdf": pdf_file}

def get_study_json_path():
    for root, dirs, files in os.walk(REFERENCESMASTERPATH, topdown=False):
        if "study.json" in files:
            yield os.path.join(root, 'study.json')

def open_reference(d):

    with open(d["json"]) as f:
        json_dict = json.loads(f.read())
    return {"json":json_dict,"pdf":d["pdf"], "reference_path":d["json"]}

def open_study(d):
    with open(d) as f:
        json_dict = json.loads(f.read())
    return {"json":json_dict, "study_path":d}

def upload_reference(json_reference):
    validate(json_reference["json"],reference_schema)
    client.action(document, ["references", "create"], params=json_reference["json"])
    with open(json_reference["pdf"],'rb') as f:
        requests.patch(f'http://0.0.0.0:8000/api/v1/references/{json_reference["json"]["sid"]}/', files={"pdf":f})



def upload_study(json_study):
    study_partial = {}
    study_partial["sid"] = json_study["json"]["sid"]
    study_partial["name"] = json_study["json"]["name"]
    study_partial["pkdb_version"] = json_study["json"]["pkdb_version"]
    study_partial["design"] = json_study["json"]["design"]
    #study_partial["substances"] = json_study["json"]["substances"]
    study_partial["reference"] = json_study["json"]["reference"]
    #study_partial["curators"] = json_study["json"]["curators"]
    #study_partial["creator"] = json_study["json"]["creator"]
    study_partial["groupset"] = json_study["json"]["groupset"]




    client.action(document, ["studies", "create"], params=study_partial)

def get_graph_references(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_reference_json_path,
        open_reference,
        upload_reference,
    )
    return graph

def get_graph_study(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_study_json_path,
        open_study,
        upload_study,
    )
    return graph


def get_services(**options):
    return {}


if __name__ == '__main__':
    client = coreapi.Client()
    document = client.get("http://0.0.0.0:8000/")

    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph_references(**options), services=get_services(**options))
        bonobo.run(get_graph_study(**options), services=get_services(**options))

