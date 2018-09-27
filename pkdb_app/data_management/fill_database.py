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
from pkdb_app import logging_utils
from pkdb_app.data_management import setup_database as sdb
logger = logging.getLogger(__name__)

BASEPATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../")
)
sys.path.append(BASEPATH)

from pkdb_app.data_management.utils import recursive_iter, set_keys
from pkdb_app.data_management.create_reference import run as create_reference
from collections import namedtuple


# -------------------------------
# Paths of JSON files
# -------------------------------
def _get_paths(data_dir, filename):
    """ Finds paths of filename recursively in base_dir. """
    for root, dirs, files in os.walk(data_dir, topdown=False):

        if filename in files:
            yield os.path.join(root, filename)


def get_reference_paths(data_dir):
    """ Finds paths of reference JSON files and corresponding PDFs.

    :return: dict
    """
    for path in _get_paths(data_dir, "reference.json"):
        study_name = os.path.basename(os.path.dirname(path))
        pdf_path = os.path.join(os.path.dirname(path), f"{study_name}.pdf")
        yield {"reference_path": path, "pdf": pdf_path}


def get_study_paths(data_dir):
    """ Finds paths of study JSON files. """
    return sorted(_get_paths(data_dir=data_dir, filename="study.json"))


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
def upload_files(file_path, authentication_header, api_url, client=None):
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
                response = sdb.requests_with_client(client, requests, f"{api_url}/datafiles/", method="post", files={"file": f}, headers=authentication_header)
            if response.status_code == 201:
                data_dict[file] = response.json()["id"]
            else:
                logging.error(f"File upload failed: {file}")
                logging.error(response.content)

    return data_dict


def upload_reference_json(json_reference, authentication_header, api_url, client=None):
    """ Uploads reference JSON. """
    success = True
    # post
    response = sdb.requests_with_client(client, requests, f"{api_url}/references/", method="post", data=json_reference["json"],
                                        headers=authentication_header)

    if not response.status_code == 201:
        logging.info(json_reference["json"]["name"] + "\n" + str(response.content))
        success = False

    # patch
    with open(json_reference["pdf"], "rb") as f:
        response = sdb.requests_with_client(client, requests, f"{api_url}/references/{json_reference['json']['sid']}/", method="patch",
                                            files={"pdf": f},
                                            headers=authentication_header)

    if not response.status_code == 200:
        logging.info(json_reference["json"]["name"] + "\n" + str(response.content))
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
                response.content, object_pairs_hook=dict_raise_on_duplicates
            )

            msg = json.dumps(json_data, sort_keys=True, indent=2)
            logging.warning(f"\n{msg}")

        except json.decoder.JSONDecodeError as err:
            # something went wrong on the django serializer side
            logging.error(err)
            logging.warning(response.content)

        return False
    return True


def upload_study_json(json_study_dict, authentication_header, api_url, client=None):
    """ Uploads study JSON.

    :returns success code
    """
    json_study = json_study_dict["json"]
    if not json_study:
        logging.warning("No study information in `study.json`")
        return False

    # upload files (and get dict for file ids)
    study_dir = os.path.dirname(json_study_dict["study_path"])
    file_dict = upload_files(study_dir, authentication_header=authentication_header, client=client)

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

    response = sdb.requests_with_client(client, requests, f"{api_url}/studies/", method="post",
                                        data=study_core,
                                        headers=authentication_header)
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
    response = sdb.requests_with_client(client, requests, f"{api_url}/studies/{sid}/", method="patch",
                                        data=study_sets,
                                        headers=authentication_header)
    success = success and check_json_response(response)

    # is using group, has to be uploaded separately from the groupset
    if "individualset" in json_study.keys():

        response = sdb.requests_with_client(client, requests, f"{api_url}/studies/{sid}/", method="patch",
                                            data={"individualset": json_study.get("individualset")},
                                            headers=authentication_header)

        success = success and check_json_response(response)

    if "outputset" in json_study.keys():
        response = sdb.requests_with_client(client, requests, f"{api_url}/studies/{sid}/", method="patch",
                                        data={"outputset": json_study.get("outputset")},
                                        headers=authentication_header)
        success = success and check_json_response(response)

    if success:
        logging.info(f"{API_URL}/studies/{sid}/")

    return success


def upload_study_from_dir(study_dir, authentication_header, api_url, client=None):
    """ Upload a complete study directory.

    Includes
    - study.json
    - reference.json
    - files

    :param study_dir:
    :return:
    """
    # FIXME: studies must be uploaded via the respective creator username (for now everything uploaded via admin)
    # This requires to get the respective tokens for the users

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
            success_ref = upload_reference_json(read_reference_json(reference_dict), api_url=api_url,
                                                authentication_header=authentication_header, client=client)

    # upload study.json
    success_study = upload_study_json(study_dict, api_url=api_url,
                                      authentication_header=authentication_header, client=client)

    if success_ref and success_study:
        logging.info("--- upload successful ---")

    return {}


def upload_studies_from_data_dir(data_dir, api_url, authentication_header=None, client=None):
    """ Uploads studies in given data directory.

    :param args: command line arguments
    :return:
    """
    if not os.path.exists(data_dir):
        logging.error("Data directory does not exist: " + data_dir)
        raise FileNotFoundError

    for study_path in get_study_paths(data_dir):
        study_folder_path = os.path.dirname(study_path)
        study_name = os.path.basename(study_folder_path)

        logging.info("-" * 80)
        logging.info(f"Uploading [{study_name}]")

        upload_study_from_dir(study_folder_path, api_url=api_url,
                              authentication_header=authentication_header, client=client)


if __name__ == "__main__":
    # core database setup (user, substance, keyword data)

    authentication_header = sdb.get_authentication_header(api_base=sdb.API_BASE, username="admin", password=sdb.DEFAULT_PASSWORD)
    # run via setup_database
    # sdb.setup_database(api_url=sdb.API_URL, authentication_header=authentication_header)

    DATA_BASE_PATH = os.path.join(BASEPATH, "..", "pkdb_data")
    DATA_PATHS = [
        os.path.join(DATA_BASE_PATH, "caffeine"),
        os.path.join(DATA_BASE_PATH, "codeine"),
    ]
    for data_dir in DATA_BASE_PATH:
        upload_studies_from_data_dir(data_dir=data_dir, api_url=sdb.API_URL,
                                     authentication_header=authentication_header)
