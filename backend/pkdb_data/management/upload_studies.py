#!/usr/bin/env python
"""Script to load study data into database.

Needs location of directory with data.

The upload expects a certain folder structure:

- folder name is STUDYNAME, e.g., Albert1974
- folder contains pdf as STUDYNAME.pdf, e.g., Albert1974.pdf
- folder contains reference information as `reference.json`
- folder contains study information as `study.json`
- folder contains additional files associated with study, i.e.,
    - tables, named `STUDYNAME_Tab[0-9]*.png`, e.g., Albert1974_Tab1.png
    - figures, named `STUDYNAME_Fig[0-9]*.png`, e.g., Albert1974_Fig2.png
    - excel file, named STUDYNAME.xlsx, e.g., Albert1974.xlsx
    - data files, named `STUDYNAME_Tab[0-9]*.csv` or `STUDYNAME_Fig[0-9]*.csv`

Details about the JSON schema are given elsewhere (JSON schema and REST API).
"""

import copy
import logging
import os
import time
import traceback
from collections.abc import Iterable
from datetime import timedelta
from pathlib import Path
from pprint import pformat
from typing import Any

import requests
from requests import Response

import pkdb_data.management.api as api
import pkdb_data.management.query
from pkdb_data.management.envs import get_environment
from pkdb_data.management.index import IndexProcess, update_study_index
from pkdb_data.management.query import check_json_response, check_json_response_study
from pkdb_data.management.reference import create_reference_for_pmid
from pkdb_data.management.tsv import build_tsvs
from pkdb_data.management.utils import read_json, recursive_iter, set_keys

logger = logging.getLogger(__name__)


# -------------------------------
# Paths of JSON files
# -------------------------------
def _get_paths(data_dir: Path, filename: str) -> Iterable[str]:
    """Find paths of filename recursively in base_dir."""
    for root, _dirs, files in os.walk(data_dir, topdown=False):
        if filename in files:
            yield os.path.join(root, filename)


def get_reference_paths(data_dir: Path) -> Iterable[dict[str, Any]]:
    """Find paths of reference JSON files and corresponding PDFs."""
    for path in _get_paths(data_dir, "reference.json"):
        yield {"reference_path": path}


def get_study_paths(data_dir: Path) -> list[str]:
    """Find paths of study JSON files."""
    return sorted(_get_paths(data_dir=data_dir, filename="study.json"))


# -------------------------------
# Read JSON files
# -------------------------------
def read_reference_json(d: dict[str, Any]) -> dict[str, Any]:
    """Read JSON for reference."""
    path = d["reference_path"]
    d2: dict[str, Any] = {**d, "json": read_json(path)}
    return d2


def read_study_json(path: Path) -> dict[str, Any]:
    """Read study JSON information."""
    return {"json": read_json(path), "study_path": path}


# -------------------------------
# Helpers
# -------------------------------
def pop_comments(d: dict, *keys: str) -> None:
    """Pops comment in nested dictionary."""
    for key in keys:
        if key == "comments":
            d.pop("comments")
            return
        d = d[key]


def _log_step(step: str, time: float) -> None:
    """Log given step."""
    logger.info("- %.2f [s] : %s", time, step)


# -------------------------------
# Upload JSON in database
# -------------------------------
def allowed_filename(fname: str) -> bool:
    """Exclude files based on filter.

    Checks if the filename is in the allowed filenames.
    """
    forbidden_suffix = (".log", ".xlsx#", ".idea", "tsv#")
    forbidden_prefix = (".lock", ".~lock", "~$", ".DS_Store")
    return fname.endswith(forbidden_suffix) or fname.startswith(forbidden_prefix)


class UploadClient:
    """Base class for study uploads."""

    def __init__(self, api_url: str, auth_headers: dict[str, str], client: Any):
        """Initialize UploadClient."""
        self.api_url = api_url
        self.auth_headers = auth_headers
        self.client = client

    def upload_reference_json(self, json_reference: dict[str, Any]) -> bool:
        """Upload reference JSON."""
        success = True
        response: Response = pkdb_data.management.query.requests_with_client(
            self.client,
            requests,
            url=f"{self.api_url}/{api.REFERENCES}/",
            method="post",
            data=json_reference["json"],
            headers=self.auth_headers,
        )

        if check_json_response(response):
            instance_exists = any(
                "already exists" in values[0] for key, values in response.json().items()
            )
            if instance_exists:
                response = pkdb_data.management.query.requests_with_client(
                    self.client,
                    requests,
                    url=f"{self.api_url}/{api.REFERENCES}/{json_reference['json']['sid']}/",
                    method="patch",
                    data=json_reference["json"],
                    headers=self.auth_headers,
                )

                success = check_json_response(response)

        if not success:
            logger.error("reference: %s upload failed", json_reference["json"]["name"])
            logger.error(response.content)

        return success

    def delete_instance(self, instance_type: str, sid: str) -> Response:
        """Delete instance with id."""
        return pkdb_data.management.query.requests_with_client(
            self.client,
            requests,
            url=f"{self.api_url}/{instance_type}/{sid}/",
            method="delete",
            headers=self.auth_headers,
        )

    def upload_study_json(
        self, json_study_dict: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """Upload study JSON.

        :returns success code
        """
        json_study = json_study_dict["json"]
        if not json_study:
            logger.warning("No study information in `study.json`")
            return False, None
        # upload files (and get dict for file ids)
        study_dir = os.path.dirname(json_study_dict["study_path"])
        start_time = time.time()
        file_dict, success = self.upload_files(study_dir)

        for keys, item in recursive_iter(json_study_dict):
            if isinstance(item, str):
                for file, file_pk in file_dict.items():
                    items = item.split("||")
                    for n, i in enumerate(items):
                        if keys[-1] in ["figure", "source", "image"]:
                            file_name = i.strip()
                            if i.strip().endswith((".tsv", ".png")):
                                file_name = i.strip()

                            elif keys[-1] in ["figure", "image"]:
                                file_name = f"{json_study.get('name')}_{i.strip()}.png"

                            elif keys[-1] == "source":
                                file_name = f".{json_study.get('name')}_{i.strip()}.tsv"

                            if file_name == file:
                                items[n] = str(file_pk)

                    item = "||".join(items)

                set_keys(json_study_dict, item, *keys)

        files_upload_time = time.time() - start_time
        files_upload_time = timedelta(seconds=files_upload_time).total_seconds()
        _log_step("Upload files", time=files_upload_time)

        sid = json_study["sid"]
        # ---------------------------
        # post study core
        # ---------------------------

        start_time = time.time()
        study_core = copy.deepcopy(json_study)
        related_sets = [
            "groupset",
            "interventionset",
            "individualset",
            "outputset",
            "dataset",
        ]
        [study_core.pop(this_set, None) for this_set in related_sets]
        study_core["files"] = list(file_dict.values())

        response = pkdb_data.management.query.requests_with_client(
            self.client,
            requests,
            url=f"{self.api_url}/{api.STUDIES}/",
            method="post",
            data=study_core,
            headers=self.auth_headers,
        )

        success = success and check_json_response(response)
        if not success:
            return False, None

        study_core_upload_time = time.time() - start_time
        study_core_upload_time = timedelta(
            seconds=study_core_upload_time
        ).total_seconds()
        _log_step("Upload core study", time=study_core_upload_time)

        # ---------------------------
        # post study sets
        # ---------------------------
        start_time = time.time()
        study_sets = {}
        study_sets["groupset"] = json_study.get("groupset")
        study_sets["interventionset"] = json_study.get("interventionset")

        response = pkdb_data.management.query.requests_with_client(
            self.client,
            requests,
            url=f"{self.api_url}/{api.STUDIES}/{sid}/",
            method="patch",
            data=study_sets,
            headers=self.auth_headers,
        )
        success = success and check_json_response(response)
        if not success:
            return False, None

        study_group_inter_upload_time = time.time() - start_time
        study_group_inter_upload_time = timedelta(
            seconds=study_group_inter_upload_time
        ).total_seconds()
        _log_step("Upload groups", time=study_group_inter_upload_time)

        # is using group, has to be uploaded separately from the groupset
        start_time = time.time()
        if "individualset" in json_study:
            response = pkdb_data.management.query.requests_with_client(
                self.client,
                requests,
                url=f"{self.api_url}/{api.STUDIES}/{sid}/",
                method="patch",
                data={"individualset": json_study.get("individualset")},
                headers=self.auth_headers,
            )

            success = success and check_json_response(response)
            if not success:
                return False, None

        study_individual_upload_time = time.time() - start_time
        study_individual_upload_time = timedelta(
            seconds=study_individual_upload_time
        ).total_seconds()
        _log_step("Upload individuals", study_individual_upload_time)

        start_time = time.time()
        if "outputset" in json_study:
            response = pkdb_data.management.query.requests_with_client(
                self.client,
                requests,
                url=f"{self.api_url}/{api.STUDIES}/{sid}/",
                method="patch",
                data={
                    "outputset": json_study.get("outputset"),
                },
                headers=self.auth_headers,
            )

            success = success and check_json_response(response)
            if success:
                check_json_response_study(response)
            if not success:
                return False, None

        if "dataset" not in json_study:
            json_study["dataset"] = {}

        response = pkdb_data.management.query.requests_with_client(
            self.client,
            requests,
            url=f"{self.api_url}/{api.STUDIES}/{sid}/",
            method="patch",
            data={"dataset": json_study.get("dataset")},
            headers=self.auth_headers,
        )
        success = success and check_json_response(response)
        if success:
            check_json_response_study(response)

        if not success:
            return False, None

        study_outputset_upload_time = time.time() - start_time
        study_outputset_upload_time = timedelta(
            seconds=study_outputset_upload_time
        ).total_seconds()
        _log_step("Upload study", time=study_outputset_upload_time)

        # indexing study in separate thread
        # index_thread = IndexThread(sid, api_url, auth_headers, client)
        # index_thread.start()

        # indexing in separate process
        index_process = IndexProcess(sid, self.api_url, self.auth_headers, self.client)
        index_process.start()

        return success, sid

    def upload_files(self, file_path: Path) -> tuple[dict[str, Any], bool]:
        """Upload all files in directory of given file.

        :param file_path:
        :return: dict with all keys for files
        """
        data_dict = {}
        success = True
        head, sid = os.path.split(file_path)
        study_dir = os.path.join(head, sid)
        for root, _dirs, files in os.walk(study_dir, topdown=False):
            # exclude files
            special_files = {"reference.json", "study.json"}
            filtered_files = set(files) - set(special_files)
            files = [file for file in filtered_files if not allowed_filename(file)]
            for file in files:
                if not file.startswith((sid, f".{sid}")):
                    logger.error(
                        "All filenames besides %s have to start with study name. <%s> does "
                        "not start with <%s>",
                        special_files,
                        file,
                        sid,
                    )
                    success = False
                if not Path(file).suffix.islower():
                    logger.error(
                        "File extensions have to be lower case. Rename <%s>.", file
                    )
                    success = False

            for file in files:
                path: str = os.path.join(root, file)
                with open(path, "rb") as f:
                    response = pkdb_data.management.query.requests_with_client(
                        self.client,
                        requests,
                        url=f"{self.api_url}/{api.DATA_FILES}/",
                        method="post",
                        files={"file": f},
                        headers=self.auth_headers,
                    )
                if response.status_code == 201:
                    data_dict[file] = response.json()["id"]
                else:
                    success = False
                    logger.error("File upload failed: %s", file)
                    logger.error(response.content)
        return data_dict, success

    def upload_studies(self, study_paths: list[Path]) -> list[str]:
        """Upload studies from study folder paths."""
        failed_uploads = []
        for study_path in study_paths:
            upload_success = self.upload_study(study_path)

            if not upload_success:
                study_name = os.path.basename(study_path)
                failed_uploads.append(study_name)
        return failed_uploads

    def upload_study(self, study_dir_path: Path) -> bool:
        """Upload a complete study directory.

        Includes
        - study.json
        - reference.json
        - files
        """
        sid = None
        study_path = study_dir_path / "study.json"
        _, study_name = os.path.split(study_dir_path)
        logger.info("-" * 80)
        logger.info(
            "Upload [blue]%s[/] to [link=%s]%s[/link]",
            study_name,
            self.api_url,
            self.api_url,
        )
        logger.info("-" * 80)
        try:
            if not study_dir_path.exists() or not study_dir_path.is_dir():
                msg = (
                    f"Study directory does not exist or is not a directory: "
                    f"{study_dir_path}"
                )
                logger.error(msg)
                return False

            # handle study.json
            if not os.path.exists(study_path):
                logger.warning("`study.json` missing.")
                return False

            # create tsv from excel file
            file_name_excel = f"{study_dir_path.name}.xlsx"

            path_to_excel = study_dir_path / file_name_excel
            if path_to_excel.is_file():
                no_error_in_build_tsv = build_tsvs(path_to_excel)
                if not no_error_in_build_tsv:
                    return False
            else:
                logger.warning(
                    "Excel file is not required but should be provided for study. Add "
                    "<%s>.",
                    file_name_excel,
                )

            study_dict = read_study_json(study_path)

            if not study_dict:
                logger.warning("`study.json` is empty.")
                return False

            study_json = study_dict.get("json", None)
            if not study_json:
                return False

            if study_json.get("name", None) != Path(study_dir_path).stem:
                logger.warning(
                    "Field name <%s> in 'study.json' must be equal name of study folder "
                    "<%s>.",
                    study_json.get("name", "None"),
                    Path(study_dir_path).stem,
                )
                return False

            # delete django and elastic study
            if study_json:
                sid = study_json.get("sid")
                self.delete_instance(api.STUDIES, study_json.get("sid"))

            # try to create missing reference.json
            reference_path = os.path.join(study_dir_path, "reference.json")

            if study_json and not os.path.exists(reference_path):
                reference_sid = study_json.get("reference", None)
                if reference_sid:
                    create_reference_for_pmid(
                        study_name=study_name,
                        pmid=reference_sid,
                        output_path=study_dir_path,
                    )
                else:
                    logger.warning(
                        "No reference in 'study.json'. You have two options. \n"
                        "1. Add the corresponding pmid into the reference field. "
                        "This will automatically create a 'reference.json'. \n"
                        "2. Add an arbitrary identification string into the reference field. "
                        "This will create a template 'reference.json'. "
                        "Please fill in the respective information."
                    )

            # upload reference.json
            success_ref = True
            start_time = time.time()

            if os.path.exists(reference_path):
                reference_dict = {"reference_path": reference_path}

                reference_json = read_reference_json(reference_dict)
                if not reference_json["json"]:
                    return False

                if reference_json and study_dict.get("json"):
                    success_ref = self.upload_reference_json(reference_json)

            reference_upload_time = time.time() - start_time
            reference_upload_time = timedelta(
                seconds=reference_upload_time
            ).total_seconds()
            _log_step("Upload references", time=reference_upload_time)

            # upload study.json
            success_study, _ = self.upload_study_json(study_dict)

            success = success_ref and success_study

        except Exception:
            tb = traceback.format_exc()
            logger.error("Exception while uploading %r:\n%s", study_dir_path, tb)
            success = False

        # messages and cleanup
        if success:
            logger.info("-" * 80)
            logger.info(
                "[link=%s/%s/%s/]%s/%s/%s/[/link]",
                self.api_url,
                api.STUDIES,
                sid,
                self.api_url,
                api.STUDIES,
                sid,
            )
            frontend_url = get_environment().api_base
            # handling local development ports for frontend
            if ":8000" in frontend_url:
                frontend_url = frontend_url.replace(":8000", ":8081")
            logger.info(
                "[green bold]UPLOAD SUCCESSFUL[/]([link=%s/data/%s]%s/data/%s[/link])",
                frontend_url,
                sid,
                frontend_url,
                sid,
            )
        else:
            logger.error("UPLOAD ERROR (check errors and warnings)")
            if sid is not None:
                # only now we have a study id
                response = self.delete_instance(api.STUDIES, sid)
                check_json_response(response)

                # non-thread/non-process indexing
                update_study_index(sid, self.api_url, self.auth_headers)

        return success

    def upload_studies_from_data_dir(
        self, data_dir: Path, ignore_studies: list[Path] | None = None
    ) -> list[str]:
        """Upload studies in given data directory.

        :param data_dir: directory containing multiple study folders.
        :param ignore_studies: list of study_folder paths.
        :return:
        """
        if not os.path.exists(data_dir):
            logger.error("Data directory does not exist: %r", data_dir)
            raise FileNotFoundError

        study_folder_paths = {
            Path(study_path).parent for study_path in get_study_paths(data_dir)
        }
        if ignore_studies is not None:
            study_folder_paths = study_folder_paths - set(ignore_studies)

        return self.upload_studies(sorted(study_folder_paths))

    def upload_studies_for_substances(
        self,
        relative_paths: list[str],
        studies_path: Path | None = None,
        ignore_studies: list[Path] | None = None,
    ) -> None:
        """Upload studies."""
        logger.info("[white]%s[/]", " " * 80)
        for rel_path in relative_paths:
            logger.info("\t[blue]%s[/]", rel_path)
        logger.info("[white]%s[/]", " " * 80)
        logger.info("")

        # base path to studies (pkdb_data git repository)
        if not studies_path:
            studies_path = Path(".").parent.parent / "studies"
        if not studies_path.exists():
            logger.error("Studies path does not exist: %r", studies_path)

        failed_study_uploads = {}
        data_dirs = [studies_path / rel_path for rel_path in relative_paths]
        if not ignore_studies:
            ignore_studies = []
        ignore_studies = [studies_path.parent / rel_path for rel_path in ignore_studies]
        for data_dir in data_dirs:
            failed_uploads = self.upload_studies_from_data_dir(
                data_dir=data_dir, ignore_studies=ignore_studies
            )
            if failed_uploads:
                failed_study_uploads[data_dir] = failed_uploads

        logger.info("-" * 80)
        if failed_study_uploads:
            logger.error("Failed studies")
            logger.error(pformat(failed_study_uploads))
        else:
            logger.info("[green bold]ALL STUDIES UPLOADED SUCCESSFULLY[/]")
