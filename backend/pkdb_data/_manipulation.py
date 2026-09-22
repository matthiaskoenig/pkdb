"""Manipulation of `study.json` files.

-------------------------------------------------------------------------------------
READ THIS, SERIOUSLY READ THIS
-------------------------------------------------------------------------------------

These module allows to manipulate 'study.json' files.
Use this module with extreme caution and check results before
commit of changes in the repository !!!
!!! If you screw this up you have to fix it !!!

Importantly on all operations the order in the JSON must be maintained!,
i.e. changes must be inserted at the right positions in the OrderedDicts!
All changes to the files must be minimal an should be checked with
git diff before commits !
-------------------------------------------------------------------------------------
"""

import json
import logging
import os
from collections import OrderedDict
from pathlib import Path

from pkdb_data.management.utils import read_json

logger = logging.getLogger(__name__)


class JsonManipulator:
    """Class for manipulating JSON files.

    These are mainly study.json files in pkdb_data.
    To apply the manipulator to other files change the `json_name` attribute
    on the class before creating instances of the manipulator
    """

    json_name = "study.json"

    def __init__(self, json_path: Path) -> None:
        """Construct JSON manipulator for given study.

        :param json_path: JSON study path
        """
        if not json_path.exists():
            raise OSError(f"Study JSON does not exist {json_path!r}")

        self.path: Path = json_path
        json_data = read_json(json_path)
        if not json_data:
            raise OSError
        self.json: dict = json_data

    def __repr__(self) -> str:
        """Get representation."""
        return f"<{self.__class__}:{self.path}>"

    def __str__(self) -> str:
        """Get string."""
        return f"<{self.__class__}:{self.path}>"

    def study_sid(self) -> str | None:
        """Study sid from json file."""
        if self.json is None:
            logger.error("Study does not have JSON content: %r", self.path)
            return None

        sid_data = self.json.get("sid", None)
        sid: str | None
        if sid_data is None:
            logger.error("Study does not have sid: %r", self.path)
            sid = None
        else:
            sid = str(sid_data)
        return sid

    @classmethod
    def from_study_dir(cls, study_path: Path) -> "JsonManipulator":
        """Create JSON Manipulator from given study directory.

        :param study_path: directory with studies.
        :return: Instance of the JSON Manipulator.
        """
        if not study_path.exists():
            raise OSError(f"Study directory does not exist {study_path!r}")
        if not study_path.is_dir():
            raise OSError(f"Study directory is not a directory {study_path!r}")

        return JsonManipulator(json_path=study_path / cls.json_name)

    def to_json(self, overwrite: bool = False) -> str:
        """Convert the content back to JSON.

        Make sure the order is preserved!

        :return:
        """
        json_str = json.dumps(self.json, indent=2, ensure_ascii=False)
        if overwrite:
            with open(self.path, "w") as f_json:
                f_json.write(json_str)
        return json_str

    @staticmethod
    def get_all_study_jsons(
        base_path: Path | None,
    ) -> list[Path]:
        """Get the study JSONs in the directory."""
        if not base_path:
            base_path = Path(__file__).parent.parent / "studies"

        study_jsons = []

        for root, _dirs, files in os.walk(str(base_path)):
            for filename in files:
                # Join the two strings in order to form the full filepath.
                if filename == "study.json":
                    filepath = os.path.join(root, filename)
                    study_jsons.append(filepath)  # Add it to the list.

        return [Path(fname) for fname in sorted(study_jsons)]

    def delete_field(self, field: str) -> None:
        """Delete PKDB version field on study."""
        if field not in self.json:
            logger.warning("Field %r does not exist, cannot be deleted.", field)
        else:
            del self.json[field]
            logger.warning("Field %r deleted.", field)

    def add_field_date(self, date: str | None) -> None:
        """Add date field after sid."""
        if not date:
            return

        field = "date"
        if "date" in self.json:
            logger.warning("%r already in study: updated to %r", field, date)
            self.json[field] = date
        else:
            # we add the date after the sid field
            sid_index = list(self.json.keys()).index("sid")

            json_new = OrderedDict()
            for k, key in enumerate(self.json.keys()):
                json_new[key] = self.json[key]
                if k == sid_index:
                    json_new[field] = date
            self.json = json_new
            logger.warning("Field %r: %r added.", field, date)


def _find_studies_without_count_mapping(substance: str | None = None) -> None:
    """Find studies which miss the count mapping and are encoded by Florian.

    Allows to provide a substance folder.
    """
    base_dir = Path(__file__).parent.parent / "studies"

    studies_dir: Path
    studies_dir = base_dir / substance if substance is not None else base_dir

    json_paths = JsonManipulator.get_all_study_jsons(base_path=studies_dir)

    # get study dates
    for json_path in json_paths:
        # create the manipulator
        json_man = JsonManipulator(json_path)
        sid = json_man.study_sid()

        if not json_man.json:
            logger.warning("No JSON content in %r", sid)
            continue

        # pprint(json_man.json)

        json: dict = json_man.json
        if "groupset" in json:
            groupset = json["groupset"]
            if "groups" in groupset:
                groups = groupset["groups"]
                for g in groups:
                    if "characteristica" in g:
                        characteristica = g["characteristica"]
                        if (
                            len(characteristica) > 0
                            and characteristica[0]["measurement_type"].startswith(
                                "col=="
                            )
                            and "count" not in characteristica[0]
                        ):
                            logger.error(json_man.path)
                            logger.error("Count mapping missing in %s:%s", sid, g)


def _fix_1() -> None:
    """Fix issues 1.

    Fix removes the pkdb_version field and
    adds the date information on the studies.
    """
    from pprint import pprint

    base_dir = Path(__file__).parent.parent / "studies"

    # test study
    # json_path = studies_dir / 'Abernethy1985' / "study.json"
    # json_paths = [json_path]

    # all caffeine studies
    # studies_dir = base_dir / 'caffeine'
    studies_dir = base_dir
    json_paths = JsonManipulator.get_all_study_jsons(base_path=studies_dir)

    # get study dates
    study_infos_json = read_json(base_dir / "study_identifiers.json")
    study_infos: dict = study_infos_json if study_infos_json else {}

    pprint(study_infos)

    for json_path in json_paths:
        # create the manipulator
        json_man = JsonManipulator(json_path)
        logger.warning(json_man)
        sid = json_man.study_sid()
        if not sid:
            continue

        if sid in study_infos:
            (_, date) = study_infos[sid]
        else:
            if sid.startswith("PKDB"):
                logger.error("PKDB studies require date information: %r", sid)
                raise OSError
            date = None

        # apply manipulations
        json_man.delete_field("pkdb_version")
        json_man.add_field_date(date=date)
        # pprint(json_man.json)

        # store file
        _ = json_man.to_json(overwrite=True)


def _fix_2(substance: str | None = None) -> None:
    """Fix issues 2.

    - removes groupby fields from individuals and groups
    - renames "figure" to "image" in outputs and timecourses

    - adds output_type: timecourse to timecourse
    - adds output_type: output to output
    - renames groupby on timecourse to label, or adds label if not existing
    - moves timecourses to outputs
    - removes timecourses
    adds the date information on the studies.
    :return:
    """
    if substance is None:
        logger.error("No substance provided")
        return

    base_dir = Path(__file__).parent.parent / "studies" / substance
    studies_dir = base_dir
    json_paths = JsonManipulator.get_all_study_jsons(base_path=studies_dir)

    for json_path in json_paths:
        # create the manipulator
        json_man = JsonManipulator(json_path)
        logger.warning(json_man)
        sid = json_man.study_sid()
        logger.info("study: %s | %s", sid, json_man.path)
        if sid is None:
            logger.error(
                "Do not apply script if information is missing: %s | %s",
                sid,
                json_man.path,
            )
            continue

        # apply manipulations
        json_data = json_man.json
        # [1] removes groupby fields from individuals and groups
        groupset = json_data.get("groupset", None)
        if groupset:
            groups = groupset.get("groups", None)
            if groups:
                for group in groups:
                    if "groupby" in group:
                        logger.warning("delete 'groupby' on group")
                        del group["groupby"]

        individualset = json_data.get("individualset")
        if individualset:
            individuals = json_data.get("groupset", {}).get("individuals")
            if individuals:
                for individual in individuals:
                    if "groupby" in individual:
                        logger.warning("delete 'groupby' on individual")
                        del individual["groupby"]

        # [2] renames "figure" to "image" in outputs and timecourses
        outputset = json_data.get("outputset", None)
        if outputset:
            for key in ["outputs", "timecourses"]:
                items = outputset.get(key, None)
                if items:
                    for item in items:
                        if "figure" in item:
                            logger.warning("renaming 'figure' -> 'image' on %s", key)
                            item["image"] = item["figure"]

                            del item["figure"]

                        # [3]
                        # - adds output_type: timecourse to timecourse
                        # - adds output_type: output to output
                        if "output_type" not in item:
                            output_type = key[:-1]
                            logger.warning("Adding 'output_type' = %r", output_type)
                            item["output_type"] = output_type

                        # [4] add label to timecourse
                        if key == "timecourses" and "label" not in item:
                            if "groupby" in item:
                                logger.warning(
                                    "renaming 'groupby' -> 'label' on timecourse"
                                )
                                item["label"] = item["groupby"]
                                del item["groupby"]
                            else:
                                logger.warning("adding 'label' on timecourse")
                                item["label"] = "col==label"

            # - move timecourse to outputs
            # - remove timecourses

            timecourses = outputset.get("timecourses", None)
            if timecourses is not None:
                outputs = outputset.get("outputs", None)
                if timecourses and outputs is None:
                    outputs = []
                for timecourse in timecourses:
                    outputs.append(timecourse)
                outputset["outputs"] = outputs
                logger.warning("move timecourses to outputs")
                del outputset["timecourses"]

        # store file
        _ = json_man.to_json(overwrite=True)


if __name__ == "__main__":
    from pkdb_data.log import enable_rich_logging

    enable_rich_logging()
    # TODO: log to file

    _find_studies_without_count_mapping()
    # _find_studies_without_count_mapping("caffeine")
    # _fix_2("midazolam")
