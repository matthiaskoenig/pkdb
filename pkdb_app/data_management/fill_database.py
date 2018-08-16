"""
Script to load data into database.

Needs location of directory with data.
Uses bonobo framework, a lightweight extract-transform-load (ETL) framework,
for data transformation and preparation.

The upload expects a certain folder structure:
- folder name is STUDYNAME, e.g., Albert1974
- folder contains pdf as STUDYNAME.pdf, e.g., Albert1974.pdf
- folder contains reference information as `reference.json`
- folder contains study information as `study.json`
- folder contains additional files associated with study, i.e.,
    - tables, named STUDYNAME_Tab[0-9]*.png, e.g., Albert1974_Tab1.png
    - figures, named STUDYNAME_Fig[0-9]*.png, e.g., Albert1974_Fig2.png
    - excel file, named STUDYNAME.xlsx, e.g., Albert1974.xlsx
    - data files, named STUDYNAME_Tab[0-9]*.csv or STUDYNAME_Fig[0-9]*.csv

Details about the JSON schema are given elsewhere (JSON schema and REST API).
"""
import os
import sys
import bonobo
import coreapi
import json
import requests
from jsonschema import validate

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)
from pkdb_app.data_management.schemas import reference_schema
from pkdb_app.data_management.create_reference_caffeine import REFERENCESMASTERPATH


# FIXME: implement proper logging

# -----------------------------
# user information
# -----------------------------
PASSWORD = "test"
USERS = [
    {"username": "janekg", "first_name": "Jan", "last_name": "Grzegorzewski", "email": "Janekg89@hotmail.de",
          "password": PASSWORD},
    {"username": "mkoenig", "first_name": "Matthias", "last_name": "König", "email": "konigmatt@googlemail.com",
           "password": PASSWORD}
]

# -----------------------------
# master path
# -----------------------------
MASTER_PATH = REFERENCESMASTERPATH


def setup_database():
    """ Creates core information in database.

    This information is independent of study information. E.g., users, substances,
    categorials.

    :return:
    """
    # FIXME: use requests instead of core api
    from pkdb_app.categoricals import SUBSTANCES_DATA
    for substance in SUBSTANCES_DATA:
        client.action(document, ["substances", "create"], params={"name": substance})
    for user in USERS:
        client.action(document, ["users", "create"], params=user)


# -------------------------------
# Paths of JSON files
# -------------------------------
def _get_paths(filename):
    """ Finds paths of filename recursively in MASTER_PATH. """
    for root, dirs, files in os.walk(MASTER_PATH, topdown=False):
        if filename in files:
            yield os.path.join(root, filename)


def get_reference_paths():
    """ Finds paths of reference JSON files and corresponding PDFs.

    :return: dict
    """
    for path in _get_paths("reference.json"):
        pdf_path = os.path.join(os.path.dirname(path), f"{os.path.basename(path)}.pdf")
        yield {"reference_path": path, "pdf": pdf_path}


def get_study_paths():
    """ Finds paths of study JSON files. """
    _get_paths("study.json")


# -------------------------------
# Read JSON files
# -------------------------------
def _read_json(path):
    """ Reads json.

    :param path: returns json, or None if parsing failed.
    :return:
    """
    with open(path) as f:
        try:
            json_data = json.loads(f.read())
        except json.decoder.JSONDecodeError as err:
            print(err)
            return
    return json_data


def read_reference_json(d):
    """ Reads JSON for reference. """
    path = d["reference_path"]
    d2 = d.copy()
    d2["json"] = _read_json(path)
    return d2


def read_study_json(path):
    return {"json": _read_json(path),
            "study_path": path}




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
        get_reference_paths,
        read_reference_json,
        upload_reference,
    )
    return graph

def get_graph_study(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_study_paths,
        read_study_json,
        upload_study,
    )
    return graph


def get_services(**options):
    return {}


if __name__ == '__main__':
    client = coreapi.Client()
    document = client.get("http://0.0.0.0:8000/")

    # core database setup
    setup_database()

    # run the bonobo chain
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph_references(**options), services=get_services(**options))
        bonobo.run(get_graph_study(**options), services=get_services(**options))

