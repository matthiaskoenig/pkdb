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
import copy
import os
import sys
import json
import requests
import logging
import coloredlogs


coloredlogs.install(
    level="INFO",
    fmt="%(module)s:%(lineno)s %(funcName)s %(levelname) -10s %(message)s"
    # fmt="%(levelname) -10s %(asctime)s %(module)s:%(lineno)s %(funcName)s %(message)s"
)
logger = logging.getLogger(__name__)


BASEPATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../")
)
sys.path.append(BASEPATH)
from pkdb_app.data_management.utils import recursive_iter, set_keys

from pkdb_app.data_management.create_reference import run as create_reference
from collections import namedtuple


# -----------------------------
# master path
# -----------------------------

API_BASE = "http://0.0.0.0:8000"
API_URL = API_BASE +"/api/v1"

# API_URL = "http://www.pk-db.com/api/v1"

# -----------------------------
# setup database
# -----------------------------

PASSWORD = os.getenv("PKDB_DEFAULT_PASSWORD")
if not PASSWORD:
    raise ValueError("Password could not be read, export the environment variable.")


USERS = [
    {
        "username": "janekg",
        "first_name": "Jan",
        "last_name": "Grzegorzewski",
        "email": "Janekg89@hotmail.de",
        "password": PASSWORD,
    },
    {
        "username": "mkoenig",
        "first_name": "Matthias",
        "last_name": "König",
        "email": "konigmatt@googlemail.com",
        "password": PASSWORD,
    },
]

# create superuser and use it for authenification
#TOKEN = os.getenv("PKDB_TOKEN")
def get_token(api_base=API_BASE):
    response = requests.post(f"{api_base}/api-token-auth/",data={"username":"admin","password":PASSWORD})
    TOKEN = response.json().get("token")
    if not TOKEN:
        os.system(f"docker-compose run --rm web ./manage.py createsuperuser2 --username admin --password {PASSWORD} --email Janekg89@hotmail.de --noinput")
        response = requests.post(f"{api_base}/api-token-auth/", data={"username": "admin", "password": PASSWORD})
        TOKEN = response.json().get("token")
        #os.environ["PKDB_TOKEN"] = TOKEN
    return TOKEN

def get_header(api_base=API_BASE):
    TOKEN = get_token(api_base=api_base)
    HEADER = {'Authorization': f'token {TOKEN}'}
    return HEADER


def setup_database(api_url,header):
    """ Creates core information in database.

    This information is independent of study information. E.g., users, substances,
    categorials.

    :return:
    """
    from pkdb_app.categoricals import SUBSTANCES_DATA, KEYWORDS_DATA

    for substance in SUBSTANCES_DATA:
        response = requests.post(f"{api_url}/substances/", json={"name": substance}, headers=header
)
        if not response.status_code == 201:
            logging.warning(f"substance upload failed ")

    for keyword in KEYWORDS_DATA:
        response = requests.post(f"{api_url}/keywords/", json={"name": keyword}, headers=header
)
        if not response.status_code == 201:
            logging.warning(f"keyword upload failed ")
            logging.warning(response.text)

    for user in USERS:
        response = requests.post(f"{api_url}/users/", json=user, headers=header
)
        if not response.status_code == 201:
            logging.warning(f"user upload failed ")


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
def dict_raise_on_duplicates(ordered_pairs):
    """Reject duplicate keys."""
    d = {}
    for k, v in ordered_pairs:
        if k in d:
            raise ValueError("duplicate key: %r" % (k,))
        else:
            d[k] = v
    return d


def _read_json(path):
    """ Reads json.

    :param path: returns json, or None if parsing failed.
    :return:
    """
    with open(path) as f:
        try:
            json_data = json.loads(f.read(), object_pairs_hook=dict_raise_on_duplicates)
        except json.decoder.JSONDecodeError as err:
            logging.warning(f"{err}\nin {path}")
            return
        except ValueError as err:
            logging.warning(f"{err}\nin {path}")
            return

    return json_data


def read_reference_json(d):
    """ Reads JSON for reference. """
    path = d["reference_path"]
    d2 = d.copy()
    d2["json"] = _read_json(path)
    return d2


def read_study_json(path):
    return {"json": _read_json(path), "study_path": path}


# -------------------------------
# Helpers
# -------------------------------


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
def upload_files(file_path, header, api_url=API_URL ):
    """ Uploads all files in directory of given file.

    :param file_path:
    :return: dict with all keys for files
    """
    data_dict = {}
    head, sid = os.path.split(file_path)
    study_dir = os.path.join(head, sid)
    for root, dirs, files in os.walk(study_dir, topdown=False):
        # exclude files
        files = set(files) - set(["reference.json", "study.json", f"{sid}.pdf"])
        # exclude files
        forbidden_suffix = (".log", ".xlsx#", ".idea")
        forbidden_prefix = ".lock"

        files = [file for file in files if not file.endswith(forbidden_suffix)]
        files = [file for file in files if not file.startswith(forbidden_prefix)]
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, "rb") as f:
                response = requests.post(f"{api_url}/datafiles/", files={"file": f}, headers=header
)
            if response.status_code == 201:
                data_dict[file] = response.json()["id"]
            else:
                logging.warning(f"File upload failed: {file}")
                print(response.json())

    return data_dict


def upload_reference_json(json_reference, header, api_url=API_URL ):
    """ Uploads reference JSON. """
    success = True
    # post
    response = requests.post(f"{api_url}/references/", json=json_reference["json"], headers=header
)
    if not response.status_code == 201:
        logging.info(json_reference["json"]["name"] + "\n" + response.text)
        success = False

    # patch
    with open(json_reference["pdf"], "rb") as f:
        response = requests.patch(
            f'{api_url}/references/{json_reference["json"]["sid"]}/', files={"pdf": f} , headers=header

        )

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
            json_data = json.loads(
                response.text, object_pairs_hook=dict_raise_on_duplicates
            )

            msg = json.dumps(json_data, sort_keys=True, indent=2)
            logging.warning(f"\n{msg}")

        except json.decoder.JSONDecodeError as err:
            # something went wrong on the django serializer side
            logging.error(err)
            logging.warning(response.text)

        return False
    return True


def upload_study_json(json_study_dict, header, api_url=API_URL):
    """ Uploads study JSON.

    :returns success code
    """
    json_study = json_study_dict["json"]
    if not json_study:
        logging.warning("No study information in `study.json`")
        return False

    # upload files (and get dict for file ids)
    study_dir = os.path.dirname(json_study_dict["study_path"])
    file_dict = upload_files(study_dir,header=header)

    for keys, item in recursive_iter(json_study_dict):
        if isinstance(item, str):
            for file, file_pk in file_dict.items():
                item = item.replace(file, str(file_pk))
            set_keys(json_study_dict, item, *keys)

    # ---------------------------
    # post study core
    # ---------------------------
    study_core = copy.deepcopy(json_study)
    related_sets = ["groupset", "interventionset", "individualset", "outputset"]
    [study_core.pop(this_set, None) for this_set in related_sets]
    study_core["files"] = list(file_dict.values())
    response = requests.post(f"{API_URL}/studies/", json=study_core, headers=header)
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
    response = requests.patch(f"{api_url}/studies/{sid}/", json=study_sets, headers=header
)
    success = success and check_json_response(response)

    # is using group, has to be uploaded separately from the groupset
    if "individualset" in json_study.keys():
        response = requests.patch(
            f"{api_url}/studies/{sid}/",
            json={"individualset": json_study.get("individualset")},headers=header
        )

        success = success and check_json_response(response)

    if "outputset" in json_study.keys():
        response = requests.patch(
            f"{api_url}/studies/{sid}/", json={"outputset": json_study.get("outputset") } ,headers=header

        )
        success = success and check_json_response(response)

    if success:
        # print access URL
        logging.info(f"{API_URL}/studies/{sid}/")

    return success


def upload_study_from_dir(study_dir, header, api_url=API_URL):
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
    # if you need to change anything in the study for all studies:
    # if study_json.get("design") == "":
    #    study_json["design"] = None
    #    with open(study_path, 'w') as fp:
    #        json.dump(study_json, fp, indent=4)

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
            success_ref = upload_reference_json(read_reference_json(reference_dict), api_url=api_url, header=header)

    # upload study.json
    success_study = upload_study_json(study_dict, api_url=api_url,header=header)

    if success_ref and success_study:
        logging.info("--- upload successful ---")

    return {}


def fill_database(args,header,api_url=API_URL):
    """ Main function to fill database.

    :param args: command line arguments
    :return:
    """

    # core database setup
    setup_database(api_url=api_url,header=header)

    for study_path in sorted(get_study_paths()):
        study_folder_path = os.path.dirname(study_path)
        study_name = os.path.basename(study_folder_path)

        logging.info("-" * 80)
        logging.info(f"Uploading [{study_name}]")
        upload_study_from_dir(study_folder_path,api_url=api_url, header=header)

    print("--- done ---")


if __name__ == "__main__":

    HEADER = get_header()
    DATA_PATH = os.path.abspath(os.path.join(BASEPATH, "..", "pkdb_data", "caffeine"))
    if not os.path.exists(DATA_PATH):
        print("-" * 80)
        print("DATA_PATH:", DATA_PATH)
        print("-" * 80)
        raise FileNotFoundError

    fill_database(args=None,header=HEADER)

    DATA_PATH = os.path.abspath(os.path.join(BASEPATH, "..", "pkdb_data", "codeine"))
    if not os.path.exists(DATA_PATH):
        print("-" * 80)
        print("DATA_PATH:", DATA_PATH)
        print("-" * 80)
        raise FileNotFoundError

    fill_database(args=None, header=HEADER)

    # ----------------------------
    # python fill_database.py -u "http://www.pk-db.com/api/v1"
    # python fill_database.py -u "http://0.0.0.0:8000/api/v1"

    # parser = argparse.ArgumentParser(description="Watch a study directory for changes")
    # parser.add_argument("-u", help="url to upload data to", dest="url", type=str, required=True)
    # parser.set_defaults(func=fill_database)
    # args = parser.parse_args()
    # args.func(args)
    # ----------------------------
