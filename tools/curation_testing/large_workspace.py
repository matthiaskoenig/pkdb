"""Create a workspace of many generated studies for the speed tests of the curation app.

    uv run --project python python tools/curation_testing/large_workspace.py <target> [--studies 1000]

The target must not exist or be empty. Each study is a copy of caffeine/Draft2021 of the
fixture under another name, `<substance>/<Surname><Year>`, with a title of its own, one to
four curators, the review statuses in turn, an issue in every fifth and a release in every
ninth study, and the typo of the template fixed in every fourth study, so that the overview shows the variety of a real workspace. The same arguments
always create the same workspace. The studies are synthetic: they describe no real
publication.
"""

import argparse
import json
import random
import shutil
from pathlib import Path

from pkdb.studyformat.jsonio import dump_json

TEMPLATE = Path(__file__).resolve().parent / "fixture" / "caffeine" / "Draft2021"
TEMPLATE_NAME = "Draft2021"
TEMPLATE_DOI = "10.5555/pkdb.draft.2021"
SUBSTANCES = (
    "caffeine",
    "codeine",
    "dextromethorphan",
    "digoxin",
    "ibuprofen",
    "losartan",
    "metformin",
    "midazolam",
    "omeprazole",
    "paracetamol",
    "theophylline",
    "warfarin",
)
# Forty surnames: with the year, every index has a name of its own.
SURNAMES = (
    "Abernethy", "Bachmann", "Carrillo", "Dahlqvist", "Eriksen", "Fujita", "Gallego",
    "Hartmann", "Ishikawa", "Jansen", "Kowalski", "Lindgren", "Moreau", "Nakamura",
    "Okafor", "Petrov", "Quintana", "Rasmussen", "Schneider", "Tanaka", "Ueda",
    "Vasquez", "Weber", "Xavier", "Yilmaz", "Zimmermann", "Andersson", "Brennan",
    "Castillo", "Dubois", "Engel", "Fischer", "Gruber", "Horvath", "Iversen",
    "Jovanovic", "Keller", "Laurent", "Mueller", "Novak",
)  # fmt: skip
# The words of the titles; no surname is among them.
WORDS = (
    "pharmacokinetics", "bioavailability", "clearance", "healthy", "volunteers",
    "elderly", "tablets", "infusion", "plasma", "saliva", "urine", "interaction",
    "smoking", "genotype", "renal", "hepatic", "impairment", "single", "dose",
    "steady", "state", "food", "effect", "children", "pregnancy", "oral",
    "intravenous", "metabolites",
)  # fmt: skip
CURATORS = ("curator", "alice", "bob", "carol", "dave")
STATUSES = ("draft", "in_review", "approved")


def study_name(index: int) -> str:
    """The folder name of study `index`: `<Surname><Year>`, one of its own for every index."""
    return f"{SURNAMES[index % len(SURNAMES)]}{1960 + index // len(SURNAMES)}"


def _title(index: int) -> str:
    return " ".join(random.Random(index).sample(WORDS, 5)).capitalize()


def _copy(folder: Path, name: str, doi: str) -> None:
    """Copy the template to `folder` as the study `name` with the DOI `doi`."""
    folder.mkdir(parents=True)
    for source in sorted(TEMPLATE.iterdir()):
        target = folder / source.name.replace(TEMPLATE_NAME, name)
        if source.suffix in {".json", ".tsv"}:
            text = source.read_text(encoding="utf-8")
            text = text.replace(TEMPLATE_NAME, name).replace(TEMPLATE_DOI, doi)
            target.write_text(text, encoding="utf-8", newline="")
        else:
            shutil.copyfile(source, target)


def _update(path: Path, **changes: object) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(changes)
    path.write_text(dump_json(data), encoding="utf-8", newline="")


def create(target: Path, studies: int = 1000) -> Path:
    """Generate `studies` studies in `target`; the workspace folder."""
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"{target} is not empty")
    for index in range(studies):
        name = study_name(index)
        folder = target / SUBSTANCES[index % len(SUBSTANCES)] / name
        _copy(folder, name, f"10.5555/pkdb.speed.{index:04d}")
        _update(folder / "reference.json", title=_title(index))
        count = 1 + index % 4
        users = [CURATORS[(index + step) % len(CURATORS)] for step in range(count)]
        study: dict[str, object] = {
            "creator": users[0],
            "curators": [{"user": user, "rating": 0} for user in users],
        }
        if index % 5 == 0:
            study["issue"] = 1000 + index
        if index % 9 == 0:
            study["release"] = {"pkdb_id": f"PKDB{index:05d}", "date": "2026-01-15"}
        _update(folder / "study.json", **study)
        status = STATUSES[index % len(STATUSES)]
        review: dict[str, object] = {"status": status}
        if status == "approved":
            review["reviewers"] = [users[0]]
            review["approved_by"] = users[0]
            review["approved"] = "2026-02-10T09:30:00Z"
        _update(folder / "review.json", **review)
        if index % 4 == 2:
            # Every fourth study has the typo of the template fixed: fewer problems.
            table = folder / "outputs_Tab1.tsv"
            text = table.read_text(encoding="utf-8").replace("cafeine", "caffeine")
            table.write_text(text, encoding="utf-8", newline="")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a workspace of studies.")
    parser.add_argument("target", type=Path)
    parser.add_argument("--studies", type=int, default=1000)
    arguments = parser.parse_args()
    print(create(arguments.target.resolve(), arguments.studies))


if __name__ == "__main__":
    main()
