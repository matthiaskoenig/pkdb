"""The substances that a study names in its tables and the substance folders they match."""

from pathlib import Path

import pytest
from issue_fixtures import study, table

from pkdb.studyformat.substances import (
    folder_index,
    folder_substances,
    study_substances,
)

# Spelled as on disk; the tables may spell them otherwise.
FOLDERS = folder_index(["caffeine", "codeine", "Midazolam"])
DOSING = {"name": "D1", "measurement": "dosing"}


def test_a_study_that_names_only_its_own_substance_has_its_folder(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    table(folder, "interventions.tsv", [DOSING | {"substance": "caffeine"}])
    assert study_substances(folder) == ("caffeine",)
    assert folder_substances("caffeine", study_substances(folder), FOLDERS) == [
        "caffeine"
    ]
    # The own substance in another case is no other substance.
    assert folder_substances("caffeine", ["CAFFEINE"], FOLDERS) == ["caffeine"]


def test_an_intervention_that_names_another_substance_folder_adds_it(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    table(
        folder,
        "interventions.tsv",
        [
            DOSING | {"substance": "caffeine"},
            DOSING | {"name": "D2", "substance": " midazolam "},
        ],
    )
    assert study_substances(folder) == ("caffeine", "midazolam")
    # After the own substance, spelled as the folder.
    assert folder_substances("caffeine", study_substances(folder), FOLDERS) == [
        "caffeine",
        "Midazolam",
    ]


def test_two_spellings_of_a_substance_count_once(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    table(
        folder,
        "interventions.tsv",
        [
            DOSING | {"substance": "Midazolam"},
            DOSING | {"name": "D2", "substance": "midazolam"},
        ],
    )
    # In the first spelling.
    assert study_substances(folder) == ("Midazolam",)


def test_a_substance_without_a_folder_is_left_out(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    table(
        folder,
        "outputs_Tab1.tsv",
        [{"subjects": "all", "measurement": "auc", "substance": "codeine"}],
    )
    point = {"label": "a", "subjects": "all", "measurement": "concentration"}
    table(
        folder,
        "timecourses_Fig1.tsv",
        [point | {"time": "1", "time_unit": "hr", "substance": "paraxanthine"}],
    )
    # Baseline values of the subjects are no data about a substance.
    table(
        folder,
        "characteristica.tsv",
        [
            {
                "source": "Tab1",
                "subjects": "all",
                "measurement": "age",
                "substance": "Midazolam",
            }
        ],
    )
    assert study_substances(folder) == ("codeine", "paraxanthine")
    assert folder_substances("caffeine", study_substances(folder), FOLDERS) == [
        "caffeine",
        "codeine",
    ]


def test_the_scatters_name_substances_on_both_axes(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    axes = {"name": "s", "subjects": "all", "x_measurement": "auc", "x_mean": "1"}
    axes |= {"y_measurement": "auc", "y_mean": "2"}
    table(
        folder,
        "scatters_Fig2.tsv",
        [axes | {"x_substance": "codeine", "y_substance": "midazolam"}],
    )
    assert study_substances(folder) == ("codeine", "midazolam")


def test_a_table_that_cannot_be_read_names_none(tmp_path):
    folder = study(tmp_path, "caffeine/A")
    table(
        folder,
        "outputs_Tab1.tsv",
        [{"subjects": "all", "measurement": "auc", "substance": "codeine"}],
    )
    # Not UTF-8, and a folder with the name of a table.
    (folder / "interventions.tsv").write_bytes(
        b"name\tmeasurement\tsubstance\nD1\tdosing\t\xffmidazolam\n"
    )
    (folder / "timecourses_Fig1.tsv").mkdir()
    assert study_substances(folder) == ("codeine",)


def test_a_folder_that_is_gone_names_none(tmp_path):
    assert study_substances(tmp_path / "studies" / "caffeine" / "Gone") == ()


def test_a_strict_read_raises_when_a_table_cannot_be_read_now(tmp_path, monkeypatch):
    folder = study(tmp_path, "caffeine/A")
    table(
        folder,
        "outputs_Tab1.tsv",
        [{"subjects": "all", "measurement": "auc", "substance": "codeine"}],
    )
    table(folder, "interventions.tsv", [DOSING | {"substance": "midazolam"}])
    real = Path.open

    def locked(path, *args, **kwargs):
        if path.name == "interventions.tsv":
            # As Windows refuses a file that another program has open.
            raise PermissionError("in use")
        return real(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", locked)
    # The issue labels count the tables that can be read.
    assert study_substances(folder) == ("codeine",)
    # The curation app reads the study again later instead.
    with pytest.raises(PermissionError):
        study_substances(folder, strict=True)
    with pytest.raises(OSError):
        study_substances(tmp_path / "studies" / "caffeine" / "Gone", strict=True)
