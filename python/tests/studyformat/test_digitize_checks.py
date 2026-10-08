import io
import json
import tarfile

from digitize_fixtures import GOOD, png, project

from pkdb.studyformat.digitize import import_project
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.validation import validate_folder


def study_with(make_study, valid_files, data):
    folder = make_study(
        {
            **valid_files,
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(data),
        }
    )
    assert format_folder(folder).ok
    return folder


def codes(folder, vocabulary):
    return [issue.code for issue in validate_folder(folder, vocabulary).issues]


def test_matching_digitization_is_valid(make_study, valid_files, sf_vocabulary):
    folder = study_with(make_study, valid_files, project(GOOD))
    found = codes(folder, sf_vocabulary)
    assert not {
        "digitized_mismatch",
        "unknown_dataset",
        "digitization_outside_image",
    } & set(found)


def test_moved_point_is_a_mismatch_at_its_row(make_study, valid_files, sf_vocabulary):
    folder = study_with(
        make_study, valid_files, project([(0, 100), (10, 70), (20, 90)])
    )
    sources = [
        i.source
        for i in validate_folder(folder, sf_vocabulary).issues
        if i.code == "digitized_mismatch"
        and i.source
        and i.source.file.endswith(".tsv")
    ]
    assert len(sources) == 1 and sources[0].file == "timecourses_Fig1.tsv"
    assert sources[0].header == "mean"
    messages = [
        i.message
        for i in validate_folder(folder, sf_vocabulary).issues
        if i.code == "digitized_mismatch"
    ]
    assert messages == [
        "1 point of dataset 'drug_plasma' has no mapped row within 2 pixels",
        "mean 2 at 1 h lies 10.0 pixels from the nearest point of dataset "
        "'drug_plasma' in Example_Fig1.wpd.json",
    ]


def test_mismatch_counts_unmatched_points_in_plural(
    make_study, valid_files, sf_vocabulary
):
    folder = study_with(make_study, valid_files, project([*GOOD, (30, 50), (40, 50)]))
    messages = [
        i.message
        for i in validate_folder(folder, sf_vocabulary).issues
        if i.code == "digitized_mismatch"
    ]
    assert messages == [
        "2 points of dataset 'drug_plasma' have no mapped row within 2 pixels"
    ]


def test_unknown_dataset_and_outside_image(make_study, valid_files, sf_vocabulary):
    folder = study_with(
        make_study, valid_files, project([*GOOD, (150, 50)], extra=("legend",))
    )
    found = codes(folder, sf_vocabulary)
    assert "unknown_dataset" in found
    assert "digitization_outside_image" in found


def test_digitization_without_image_is_missing_image(
    make_study, valid_files, sf_vocabulary
):
    files = {k: v for k, v in valid_files.items() if k != "Example_Fig3.png"}
    folder = make_study({**files, "Example_Fig3.wpd.json": json.dumps(project(GOOD))})
    issues = [
        i
        for i in validate_folder(folder, sf_vocabulary).issues
        if i.code == "missing_image"
        and i.source
        and i.source.file == "Example_Fig3.wpd.json"
    ]
    assert issues


def test_import_tar_project_writes_canonical_file_and_image(
    make_study, valid_files, tmp_path
):
    files = {k: v for k, v in valid_files.items() if k != "Example_Fig1.png"}
    folder = make_study(files)
    archive = tmp_path / "project.tar"
    with tarfile.open(archive, "w") as tar:
        for name, data in (
            (
                "project/info.json",
                json.dumps(
                    {"version": [4, 0], "json": "wpd.json", "images": ["fig.png"]}
                ).encode(),
            ),
            ("project/wpd.json", json.dumps(project(GOOD)).encode()),
            ("project/fig.png", png(100, 100)),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    result = import_project(folder, "Fig1", archive)
    assert result.issues == [] and result.wrote_image
    assert (folder / "Example_Fig1.png").read_bytes() == png(100, 100)
    written = json.loads((folder / "Example_Fig1.wpd.json").read_text())
    assert written["datasetColl"][0]["data"][1]["value"] == [1, 2]


def test_import_rejects_points_outside_the_existing_image(
    make_study, valid_files, tmp_path
):
    folder = make_study({**valid_files, "Example_Fig1.png": png(50, 50)})
    file = tmp_path / "wpd.json"
    file.write_text(json.dumps(project(GOOD)))
    result = import_project(folder, "Fig1", file)
    assert [issue.code for issue in result.issues] == ["digitization_outside_image"]
    assert not (folder / "Example_Fig1.wpd.json").exists()


def _archive(path, image):
    with tarfile.open(path, "w") as tar:
        for name, data in (
            ("project/wpd.json", json.dumps(project(GOOD)).encode()),
            ("project/fig.png", image),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


def test_import_refuses_a_project_digitized_on_another_image_size(
    make_study, valid_files, tmp_path
):
    folder = make_study({**valid_files, "Example_Fig1.png": png(100, 100)})
    archive = _archive(tmp_path / "project.tar", png(200, 150))
    result = import_project(folder, "Fig1", archive)
    assert [(issue.code, issue.message) for issue in result.issues] == [
        (
            "digitization_invalid",
            "The project was digitized on an image of 200x150, "
            "the study image Example_Fig1.png is 100x100",
        )
    ]
    assert not result.wrote_image
    assert not (folder / "Example_Fig1.wpd.json").exists()
    assert (folder / "Example_Fig1.png").read_bytes() == png(100, 100)
    same = _archive(tmp_path / "same.tar", png(100, 100))
    assert import_project(folder, "Fig1", same).issues == []
    assert (folder / "Example_Fig1.wpd.json").exists()


def test_file_level_digitization_warnings_carry_their_dataset_as_key(
    make_study, valid_files, sf_vocabulary
):
    folder = study_with(
        make_study, valid_files, project([*GOOD, (30, 50)], extra=("legend",))
    )
    keys = {
        (issue.code, issue.source.key)
        for issue in validate_folder(folder, sf_vocabulary).issues
        if issue.source
        and issue.source.file == "Example_Fig1.wpd.json"
        and issue.code in {"unknown_dataset", "digitized_mismatch"}
    }
    assert keys == {
        ("unknown_dataset", "legend"),
        ("digitized_mismatch", "drug_plasma"),
    }
