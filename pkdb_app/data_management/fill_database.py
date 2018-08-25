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
import json
import requests
import bonobo
from jsonschema import validate
import logging
import coloredlogs

coloredlogs.install(
    level='INFO',
    fmt="%(module)s:%(lineno)s %(funcName)s %(levelname) -10s %(message)s"
    # fmt="%(levelname) -10s %(asctime)s %(module)s:%(lineno)s %(funcName)s %(message)s"
)
logger = logging.getLogger(__name__)


# FIXME: remove bonobo

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)
from pkdb_app.data_management.schemas import reference_schema
from pkdb_app.data_management.create_reference import run as create_reference
from collections import namedtuple


# FIXME: implement proper logging

# -----------------------------
# master path
# -----------------------------
# DATA_PATH = os.path.join(BASEPATH, "data", "Master", "Studies")
DATA_PATH = os.path.abspath(os.path.join(BASEPATH, "..", "pkdb_data", "caffeine"))
if not os.path.exists(DATA_PATH):
    print("-" * 80)
    print("DATA_PATH:", DATA_PATH)
    print("-" * 80)
    raise FileNotFoundError

API_URL = "http://0.0.0.0:8000/api/v1"
# API_URL = "http://www.pk-db.com/api/v1"

# -----------------------------
# setup database
# -----------------------------

PASSWORD = os.getenv("PKDB_DEFAULT_PASSWORD")
if not PASSWORD:
    raise ValueError("Password could not be read, export the environment variable.")

USERS = [
    {"username": "janekg", "first_name": "Jan", "last_name": "Grzegorzewski", "email": "Janekg89@hotmail.de",
     "password": PASSWORD},
    {"username": "mkoenig", "first_name": "Matthias", "last_name": "König", "email": "konigmatt@googlemail.com",
     "password": PASSWORD}
]


def setup_database(api_url):
    """ Creates core information in database.

    This information is independent of study information. E.g., users, substances,
    categorials.

    :return:
    """
    from pkdb_app.categoricals import SUBSTANCES_DATA
    for substance in SUBSTANCES_DATA:
        response = requests.post(f'{api_url}/substances/', json={"name": substance})
        check_json_response(response)

    for user in USERS:
        response = requests.post(f'{api_url}/users/', json=user)
        check_json_response(response)


# -------------------------------
# Paths of JSON files
# -------------------------------
def _get_paths(filename):
    """ Finds paths of filename recursively in MASTER_PATH. """
    for root, dirs, files in os.walk(DATA_PATH, topdown=False):
        if filename in files:
            yield os.path.join(root, filename)


def get_reference_paths():
    """ Finds paths of reference JSON files and corresponding PDFs.

    :return: dict
    """
    for path in _get_paths("reference.json"):
        study_name = os.path.basename(os.path.dirname(path))
        pdf_path = os.path.join(os.path.dirname(path), f"{study_name}.pdf")
        yield {"reference_path": path, "pdf": pdf_path}


def get_study_paths():
    """ Finds paths of study JSON files. """
    return _get_paths("study.json")


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
            logging.warning(f'{err}\nin {path}')
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


# -------------------------------
# Helpers
# -------------------------------

def recursive_iter(obj, keys=()):
    """ Creates dictionary with key:object from nested JSON data structure. """
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from recursive_iter(v, keys + (k,))
    elif any(isinstance(obj, t) for t in (list, tuple)):
        for idx, item in enumerate(obj):
            yield from recursive_iter(item, keys + (idx,))

        if len(obj) == 0:
            yield keys, None

    else:
        yield keys, obj


def set_keys(d, value, *keys):
    """ Changes keys in nested dictionary. """
    for key in keys[:-1]:
        d = d[key]
    d[keys[-1]] = value


def remove_keys(d, value, *keys):
    """ Changes keys in nested dictionary. """
    for key in keys[:-1]:
        d = d[key]
    d[keys[-1]] = value


def pop_comments(d, *keys):
    """ Pops comment in nested dictionary. """
    for key in keys:

        if key == "comments":
            d.pop("comments")
            return
        d = d[key]


# -------------------------------
# Upload JSON in database
# -------------------------------
def upload_files(file_path, api_url=API_URL):
    """ Uploads all files in directory of given file.

    :param file_path:
    :return: dict with all keys for files
    """
    data_dict = {}
    head, sid = os.path.split(file_path)
    study_dir = os.path.join(head, sid)
    for root, dirs, files in os.walk(study_dir, topdown=False):
        #exclude files
        files = set(files) - set(['reference.json', 'study.json', f'{sid}.pdf'])
        #exclude files
        forbidden_suffix = (".log",".xlsx#",".idea")
        files = [file for file in files if not file.endswith(forbidden_suffix)]

        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                response = requests.post(f'{api_url}/datafiles/', files={"file": f})
            if response.status_code == 201:
                data_dict[file] = response.json()["id"]
            else:
                logging.warning(f"File upload failed: {file}")
                print(response.json())

    return data_dict


def upload_reference_json(json_reference, api_url=API_URL):
    """ Uploads reference JSON. """
    success = True
    validate(json_reference["json"], reference_schema)

    # post
    response = requests.post(f'{api_url}/references/', json=json_reference["json"])
    if not response.status_code == 201:
        logging.info(json_reference["json"]["name"] + "\n" + response.text)
        success = False

    # patch
    with open(json_reference["pdf"], 'rb') as f:
        response = requests.patch(f'{api_url}/references/{json_reference["json"]["sid"]}/', files={"pdf": f})

    if not response.status_code == 200:
        logging.info(json_reference["json"]["name"] + "\n" + response.text)
        success = False

    return success


def check_json_response(response):
    """ Check response and create warning if not valid

    :param response:
    :return:
    """
    if response.status_code not in [200, 201]:
        try:
            json_data = json.loads(response.text)

            msg = json.dumps(json_data, sort_keys=True, indent=2)
            logging.warning(f'\n{msg}')

        except json.decoder.JSONDecodeError as err:
            # something went wrong on the django serializer side
            logging.error(err)
            logging.warning(response.text)

        return False
    return True


def upload_study_json(json_study_dict, api_url=API_URL):
    """ Uploads study JSON.

    :returns success code
    """
    success = True
    json_study = json_study_dict["json"]
    if not json_study:
        logging.warning("No study information in `study.json`")
        return False

    # upload files (and get dict for file ids)
    study_dir = os.path.dirname(json_study_dict["study_path"])
    file_dict = upload_files(study_dir)

    comments = []
    for keys, item in recursive_iter(json_study_dict):
        #set_keys(json_study_dict,item.replace(item,file_dict[item]),*keys)
        if isinstance(item,str):
            for file, file_pk in file_dict.items():
                item = item.replace(file, str(file_pk))

            set_keys(json_study_dict, item, *keys)

        if "comments" in keys:
            n_keys = []
            for key in keys:
                n_keys.append(key)
                if key == "comments":
                    break
            comments.append(tuple(n_keys))
    for comment in set(comments):
        pop_comments(json_study_dict, *comment)
    #from pprint import pprint
    #pprint(list(recursive_iter(json_study_dict)))

    # ---------------------------
    # post study core
    # ---------------------------
    study_core = {}
    study_core["sid"] = json_study.get("sid")
    study_core["name"] = json_study.get("name")
    study_core["pkdb_version"] = json_study.get("pkdb_version")
    study_core["design"] = json_study.get("design")
    study_core["substances"] = json_study.get("substances")
    study_core["reference"] = json_study.get("reference")
    study_core["curators"] = json_study.get("curators")
    study_core["creator"] = json_study.get("creator")
    study_core["files"] = list(file_dict.values())

    response = requests.post(f'{API_URL}/studies/', json=study_core)
    success = check_json_response(response)

    # ---------------------------
    # post study sets
    # ---------------------------
    study_sets = {}
    study_sets["groupset"] = json_study.get("groupset")
    study_sets["interventionset"] = json_study.get("interventionset")

    # FIXME: Where are groupset, individualset and interventionset uploaded?

    # post
    sid = json_study["sid"]
    response = requests.patch(f'{api_url}/studies/{sid}/', json=study_sets)
    success = success and check_json_response(response)

    # is using group, has to be uploaded separately from the groupset
    if "individualset" in json_study.keys():
        response = requests.patch(f'{api_url}/studies/{sid}/',
                                  json={"individualset": json_study.get("individualset")})

        success = success and check_json_response(response)


    if "outputset" in json_study.keys():
        response = requests.patch(f'{api_url}/studies/{sid}/',
                                  json={"outputset": json_study.get("outputset")})
        success = success and check_json_response(response)

    if success:
        # print access URL
        logging.info(f'{API_URL}/studies/{sid}/')

    return success


def upload_study_from_dir(study_dir, api_url=API_URL):
    """ Upload a complete study directory.

    Includes
    - study.json
    - reference.json
    - files

    :param study_dir:
    :return:
    """

    # handle study.json
    study_path = os.path.join(study_dir, "study.json")
    _, study_name = os.path.split(study_dir)
    if not os.path.exists(study_path):
        logging.warning("`study.json` missing.")
        return False

    study_dict = read_study_json(study_path)
    if not study_dict:
        logging.warning("`study.json` is empty.")
        return False

    study_json = study_dict.get("json", None)

    # try to create missing reference.json
    reference_path = os.path.join(study_dir, "reference.json")
    reference_pdf = os.path.join(study_dir, f"{study_name}.pdf")
    if study_json and not os.path.exists(reference_path):
        if study_json:
            pmid = study_json.get("reference", None)
            if pmid is not None:
                Reference = namedtuple("Reference", ["reference", "name", "pmid"])
                ref = Reference(reference=study_dir, name=study_name, pmid=pmid)
                create_reference(ref)
            else:
                logging.warning("`reference.json` missing, and no pmid in `study.json`")

    # upload reference.json
    success_ref = True
    if os.path.exists(reference_path):
        reference_dict = {"reference_path": reference_path, "pdf": reference_pdf}
        if read_reference_json(reference_dict):
            success_ref = upload_reference_json(read_reference_json(reference_dict), api_url)

    # upload study.json
    success_study = upload_study_json(study_dict, api_url)

    if success_ref and success_study:
        logging.info("--- upload successful ---")

    return {}


# -------------------------------
# Bonobo
# -------------------------------
def get_graph_references(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_reference_paths,
        read_reference_json,
        upload_reference_json,
    )
    return graph


def get_graph_study(**options):
    graph = bonobo.Graph()
    # add studies
    graph.add_chain(
        get_study_paths,
        read_study_json,
        upload_study_json,
    )
    return graph


def get_services(**options):
    return {}


# -------------------------------------------------------------------------------
if __name__ == '__main__':

    API_URL = "http://0.0.0.0:8000/api/v1"
    # API_URL = "http://www.pk-db.com/api/v1"

    # core database setup
    setup_database(api_url=API_URL)

    # run the bonobo chain
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph_references(**options), services=get_services(**options))
        bonobo.run(get_graph_study(**options), services=get_services(**options))

    print("--- done ---")