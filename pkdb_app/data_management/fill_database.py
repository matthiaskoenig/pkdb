import os, sys
import bonobo
import coreapi
import json
import requests

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)
from jsonschema import validate
from pkdb_app.data_management.schemas import reference_schema
import logging
import mondrian
# One line setup (excepthook=True tells mondrian to handle uncaught exceptions)
#mondrian.setup(excepthook=True)
# Use logging, as usual.
#logger = logging.getLogger()
#logger.setLevel(logging.DEBUG)

if hasattr (sys, 'tracebacklimit'):
    del sys.tracebacklimit

class Stop (Exception):
    def __init__ (self):
        sys.tracebacklimit = 0

PASSWORD = "test"
Jan_G_U = {"username":"janekg","first_name":"Jan","last_name":"Grzegorzewski","email":"Janekg89@hotmail.de","password":PASSWORD}
Matthias_K = {"username":"mkoenig","first_name":"Matthias","last_name":"König","email":"konigmatt@googlemail.com","password":PASSWORD}

USERS = [Jan_G_U, Matthias_K]


def get_reference_json_path():

    fill_user_and_substances()
    from pkdb_app.data_management.create_reference_caffeine import REFERENCESMASTERPATH

    for root, dirs, files in os.walk(REFERENCESMASTERPATH, topdown=False):
        if "reference.json" in files:
            json_file = os.path.join(root, 'reference.json')
            pdf_file = os.path.join(root,f"{os.path.basename(root)}.pdf")

            yield {"json":json_file , "pdf": pdf_file}


def get_study_json_path():
    from pkdb_app.data_management.create_reference_caffeine import REFERENCESMASTERPATH
    for root, dirs, files in os.walk(REFERENCESMASTERPATH, topdown=False):
        if "study.json" in files:
            yield os.path.join(root, 'study.json')


def open_reference(d):
    with open(d["json"]) as f:
        try:
            json_dict = json.loads(f.read())
        except json.decoder.JSONDecodeError as err:
            print(err)
            return
    return {"json":json_dict,"pdf":d["pdf"], "reference_path":d["json"]}


def open_study(d):
    with open(d) as f:
        try:
            json_dict = json.loads(f.read())
        except json.decoder.JSONDecodeError as err:
            print(err)
            return



    return {"json":json_dict, "study_path":d}


def upload_reference(json_reference):
    ok = True
    validate(json_reference["json"],reference_schema)
    #client.action(document, ["references", "create"], params=json_reference["json"])
    response = requests.post(f'http://0.0.0.0:8000/api/v1/references/', json=json_reference["json"])
    if not response.status_code == 201:
        print(json_reference["json"]["name"], response.text)
        ok = False


    with open(json_reference["pdf"],'rb') as f:
        response = requests.patch(f'http://0.0.0.0:8000/api/v1/references/{json_reference["json"]["sid"]}/', files={"pdf":f})

    if not response.status_code == 200:
        print(json_reference["json"]["name"], response.text)
        ok = False

    return ok



def fill_user_and_substances():
    from pkdb_app.categoricals import SUBSTANCES_DATA
    for substance in SUBSTANCES_DATA:
        client.action(document, ["substances", "create"], params={"name":substance})
    for user in USERS:
        client.action(document, ["users", "create"], params=user)


def fill_files(file_path):
    data_dict = {}
    head, sid = os.path.split(file_path)
    study_dir = os.path.join(head,sid)
    for root, dirs, files in os.walk(study_dir, topdown=False):
        files = set(files) - set(['reference.json', 'study.json', f'{sid}.pdf'])
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path,'rb') as f:
                response = requests.post(f'http://0.0.0.0:8000/api/v1/datafiles/', files={"file": f})
            data_dict[file] = response.json()["id"]
    return data_dict

def recursive_iter(obj, keys=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from recursive_iter(v, keys + (k,))
    elif any(isinstance(obj, t) for t in (list, tuple)):
        for idx, item in enumerate(obj):
            yield from recursive_iter(item, keys + (idx,))
    else:
        yield keys, obj

def set_keys(d, value, *keys):
    for key in keys[:-1]:
        d = d[key]
    d[keys[-1]] = value
def pop_comment(d, *keys):

    for key in keys[:-1]:

        if  key == "comments":
            d.pop("comments")
            return

        d = d[key]




def upload_study(json_study):
    ok = True
    study_dir = os.path.dirname(json_study["study_path"])
    file_dict = fill_files(study_dir)
    comments = []
    for keys, item in recursive_iter(json_study):
        if item in file_dict.keys():
            set_keys(json_study, file_dict[item], *keys)
        if "comments" in keys:
            comments.append(keys)

    for comment in comments:
        pop_comment(json_study,*comment)



    study_partial = {}

    study_partial["sid"] = json_study["json"]["sid"]
    study_partial["name"] = json_study["json"]["name"]
    study_partial["pkdb_version"] = json_study["json"]["pkdb_version"]
    study_partial["design"] = json_study["json"]["design"]
    study_partial["substances"] = json_study["json"]["substances"]
    study_partial["reference"] = json_study["json"]["reference"]
    study_partial["curators"] = json_study["json"]["curators"]
    study_partial["creator"] = json_study["json"]["creator"]
    study_partial["files"] = list(file_dict.values())
    #study_partial["bla"] = "bla"





    #client.action(document, ["studies", "create"], params=study_partial)
    response = requests.post(f'http://0.0.0.0:8000/api/v1/studies/',
                              json=study_partial)
    if not response.status_code == 201:
        print(json_study["json"]["name"],response.text)
        ok = False




    study_partial2 = {}
    study_partial2["groupset"] = json_study["json"]["groupset"]
    study_partial2["interventionset"] = json_study["json"]["interventionset"]
    study_partial2["individualset"] = json_study["json"].get("individualset", None)


    response = requests.patch(f'http://0.0.0.0:8000/api/v1/studies/{json_study["json"]["sid"]}/', json = study_partial2)
    if not response.status_code == 200:
        print(json_study["json"]["name"], response.text)
        ok = False

    if "outputset" in json_study["json"].keys():
        response = requests.patch(f'http://0.0.0.0:8000/api/v1/studies/{json_study["json"]["sid"]}/', json = {"outputset": json_study["json"].get("outputset")})
        if not response.status_code == 200:
            print(json_study["json"]["name"],response.text)
            ok = False

    return ok

    #study_partial["outputset"] = json_study["json"].get("outputset",None)


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

