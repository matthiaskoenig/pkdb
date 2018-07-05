import os
import bonobo
import coreapi
import json
from create_master import REFERENCESMASTERPATH

client = coreapi.Client()
document = client.get("http://0.0.0.0:8000/")


def get_reference_json_path():
    for root, dirs, files in os.walk(REFERENCESMASTERPATH, topdown=False):
        if "data.json" in files:
            yield os.path.join(root, 'data.json')


def open_json(d):
    with open(d) as f:
        json_dict = json.loads(f.read())
    return {"json":json_dict, "reference_path":d}


def upload_reference(json_reference):
    client.action(document, ["references", "create"], params=json_reference["json"])


def get_graph(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_reference_json_path,
        open_json,
        upload_reference,
    )
    return graph


def get_services(**options):
    return {}


if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph(**options), services=get_services(**options))
