import os, sys
import bonobo
import coreapi
import json

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)

from pkdb_app.data_management.create_reference import REFERENCESMASTERPATH
from jsonschema import validate
from pkdb_app.data_management.schemas import reference_schema





def get_reference_json_path():
    for root, dirs, files in os.walk(REFERENCESMASTERPATH, topdown=False):
        if "reference.json" in files:
            yield os.path.join(root, 'reference.json')

def get_study_json_path():
    for root, dirs, files in os.walk(REFERENCESMASTERPATH, topdown=False):
        if "study.json" in files:
            yield os.path.join(root, 'study.json')

def open_reference(d):
    with open(d) as f:
        json_dict = json.loads(f.read())
    return {"json":json_dict, "reference_path":d}

def open_study(d):
    with open(d) as f:

        json_dict = json.loads(f.read())
    return {"json":json_dict, "study_path":d}

def upload_reference(json_reference):
    validate(json_reference["json"],reference_schema)
    client.action(document, ["references", "create"], params=json_reference["json"])

def upload_study(json_study):
    client.action(document, ["studies", "create"], params=json_study["json"])

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

