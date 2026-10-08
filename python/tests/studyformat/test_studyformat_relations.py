import json

import pytest

from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.load import load_study
from pkdb.studyformat.relations import check_relations

CMAX = {
    "subjects": "all",
    "interventions": "D1",
    "measurement": "cmax",
    "mean": "2",
    "unit": "mg/l",
}
POINT = {
    "label": "a",
    "subjects": "all",
    "interventions": "D1",
    "measurement": "concentration",
    "time_unit": "h",
}
ITEM = {
    "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
    "kind": "question",
    "text": "Check this.",
    "author": "curator",
    "created": "2026-10-05T10:12:00Z",
}


@pytest.fixture
def run(make_study, valid_files):
    def check(**files):
        study = load_study(make_study({**valid_files, **files}))
        return {
            (
                issue.code,
                issue.source.file if issue.source else None,
                issue.source.header if issue.source else None,
            )
            for issue in check_relations(study)
        }

    return check


def test_valid_study_passes(run):
    assert run() == set()


def test_unknown_and_duplicate_references(run, tsv):
    found = run(
        **{
            "outputs_Tab2.tsv": tsv(
                "outputs", {**CMAX, "subjects": "S9", "interventions": "D1,D2"}
            ),
            "scatters_Fig2.tsv": tsv(
                "scatters",
                {
                    "name": "s",
                    "subjects": "S1",
                    "x_measurement": "age",
                    "x_mean": "1",
                    "y_interventions": "D1,D1",
                    "y_measurement": "cmax",
                    "y_mean": "2",
                },
                {
                    "name": "s",
                    "subjects": "S2",
                    "x_measurement": "age",
                    "x_mean": "2",
                    "y_measurement": "cmax",
                    "y_mean": "3",
                },
            ),
        }
    )
    assert found == {
        ("unknown_reference", "outputs_Tab2.tsv", "subjects"),
        ("unknown_reference", "outputs_Tab2.tsv", "interventions"),
        ("duplicate_reference", "scatters_Fig2.tsv", "y_interventions"),
    }


def test_unknown_reference_candidates(make_study, valid_files, tsv):
    files = {
        **valid_files,
        "outputs_Tab2.tsv": tsv("outputs", {**CMAX, "subjects": "S11"}),
    }
    issue = next(
        i
        for i in check_relations(load_study(make_study(files)))
        if i.code == "unknown_reference"
    )
    assert issue.suggestions[0].candidates == ["S1"]


def test_broken_subjects_table_suppresses_reference_noise(run):
    found = run(**{"subjects.tsv": "group\nall\n"})
    assert not any(code == "unknown_reference" for code, _, _ in found)


def test_missing_subjects_table_suppresses_reference_noise(make_study, valid_files):
    files = {name: data for name, data in valid_files.items() if name != "subjects.tsv"}
    study = load_study(make_study(files))
    assert "subjects" in study.broken
    assert not any(
        issue.code == "unknown_reference" for issue in check_relations(study)
    )


def test_subject_tree(run, tsv):
    found = run(
        **{
            "subjects.tsv": tsv(
                "subjects",
                {"name": "all", "parent": "S1", "count": "2"},
                {"name": "S1", "parent": "all", "count": "5"},
                {"name": "S2", "count": "1"},
                {"name": "x", "parent": "y"},
                {"name": "y", "parent": "x"},
                {"name": "S1"},
            )
        }
    )
    assert {
        ("root_parent", "subjects.tsv", "parent"),
        ("missing_parent", "subjects.tsv", "parent"),
        ("subject_cycle", "subjects.tsv", "parent"),
        ("subject_count_exceeds_parent", "subjects.tsv", "count"),
        ("duplicate_name", "subjects.tsv", "name"),
    } <= found


def test_missing_root(run, tsv):
    found = run(**{"subjects.tsv": tsv("subjects", {"name": "S1", "count": "1"})})
    assert ("missing_root", "subjects.tsv", None) in found


def test_series_rules(run, tsv):
    rows = [
        {**POINT, "time": "0", "mean": "1"},
        {**POINT, "time": "0", "mean": "2"},
        {**POINT, "time": "1", "mean": "2", "substance": "drug"},
    ]
    found = run(**{"timecourses_Fig1.tsv": tsv("timecourses", *rows)})
    assert found == {
        ("duplicate_time", "timecourses_Fig1.tsv", "time"),
        ("inconsistent_series", "timecourses_Fig1.tsv", "substance"),
    }


def test_labels_and_scatter_names_are_unique_across_files(run, tsv, valid_files):
    other = tsv(
        "timecourses", {**POINT, "label": "drug_plasma", "time": "0", "mean": "1"}
    )
    found = run(**{"timecourses_Fig3.tsv": other, "Example_Fig3.png": b"png"})
    assert found == {("duplicate_label", "timecourses_Fig3.tsv", "label")}


def test_timecourse_labels_differ_from_scatter_axis_labels(run, tsv):
    # Scatter axes are labelled <name>_x and <name>_y in the canonical study.
    rows = [
        {**POINT, "label": "age_vs_cmax_y", "time": "0", "mean": "1"},
        {**POINT, "label": "age_vs_cmax_y", "time": "1", "mean": "2"},
        {**POINT, "label": "age_vs_cmax_z", "time": "0", "mean": "1"},
        {**POINT, "label": "age_vs_cmax_z", "time": "1", "mean": "2"},
    ]
    study = {"timecourses_Fig1.tsv": tsv("timecourses", *rows)}
    assert run(**study) == {("duplicate_label", "timecourses_Fig1.tsv", "label")}


def test_timecourse_label_conflicts_are_reported_once_per_label(
    make_study, valid_files, tsv
):
    rows = [
        {**POINT, "label": "age_vs_cmax_x", "time": str(time), "mean": "1"}
        for time in range(3)
    ]
    files = {**valid_files, "timecourses_Fig1.tsv": tsv("timecourses", *rows)}
    issues = check_relations(load_study(make_study(files)))
    [issue] = [issue for issue in issues if issue.code == "duplicate_label"]
    assert issue.source is not None
    assert (issue.source.row, issue.source.cell) == (2, "C2")
    assert "age_vs_cmax" in issue.message and "scatters_Fig2.tsv" in issue.message


def test_parent_must_be_a_group(make_study, valid_files, tsv):
    subjects = tsv(
        "subjects",
        {"name": "all", "count": "2", "source": "Tab1"},
        {"name": "S1", "parent": "all", "count": "1", "source": "TabA"},
        {"name": "S2", "parent": "S1", "count": "1", "source": "TabA"},
        {"name": "unknown", "parent": "all"},
        {"name": "S3", "parent": "unknown", "count": "1"},
    )
    files = {**valid_files, "subjects.tsv": subjects}
    issues = check_relations(load_study(make_study(files)))
    [issue] = [issue for issue in issues if issue.code == "parent_not_group"]
    assert (issue.severity, issue.category) == ("error", "reference")
    assert issue.source is not None
    assert (issue.source.row, issue.source.header, issue.source.cell) == (
        4,
        "parent",
        "C4",
    )
    assert "'S1'" in issue.message


def test_duplicates(run, tsv):
    rows = [CMAX, CMAX, {**CMAX, "mean": "3"}]
    found = run(**{"outputs_Tab2.tsv": tsv("outputs", *rows)})
    assert found == {
        ("duplicate_row", "outputs_Tab2.tsv", None),
        ("duplicate_observation", "outputs_Tab2.tsv", None),
    }


def test_unused_names(run, tsv, valid_files):
    subjects = valid_files["subjects.tsv"] + "\tS3\tall\t1\t\t\n"
    interventions = tsv(
        "interventions",
        {"name": "D1", "measurement": "dosing", "mean": "1"},
        {"name": "D2", "measurement": "dosing", "mean": "1"},
    )
    found = run(**{"subjects.tsv": subjects, "interventions.tsv": interventions})
    assert found == {
        ("unused_subject", "subjects.tsv", "name"),
        ("unused_intervention", "interventions.tsv", "name"),
    }


def test_missing_images(run, tsv, valid_files):
    found = run(
        **{
            "outputs_Tab9.tsv": tsv("outputs", CMAX),
            "characteristica.tsv": valid_files["characteristica.tsv"].replace(
                "TabA", "Tab7"
            ),
        }
    )
    assert found == {
        ("missing_image", "outputs_Tab9.tsv", None),
        ("missing_image", "characteristica.tsv", "source"),
    }


def test_study_rules(run, valid_files):
    study = json.loads(valid_files["study.json"])
    found = run(
        **{
            "study.json": dump_json(
                {**study, "access": "public", "reference": {"pmid": "999"}}
            ),
        }
    )
    assert found == {
        ("public_requires_release", "study.json", None),
        ("reference_mismatch", "reference.json", None),
    }


def test_review_rules(run):
    items = [
        {
            **ITEM,
            "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2A1",
            "target": {"file": "outputs_Tab2.tsv", "rows": {"subjects": "S9"}},
        },
        {
            **ITEM,
            "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2A2",
            "target": {"file": "outputs_Tab5.tsv"},
        },
        {
            **ITEM,
            "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2A3",
            "target": {"file": "outputs_Tab2.tsv", "column": "group"},
        },
        {
            **ITEM,
            "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2A4",
            "target": {"file": "Example.pdf"},
        },
    ]
    found = run(
        **{
            "review.json": dump_json(
                {
                    "status": "approved",
                    "reviewers": ["mkoenig"],
                    "approved_by": "mkoenig",
                    "approved": "2026-10-06T12:00:00Z",
                    "items": items,
                }
            )
        }
    )
    assert found == {
        ("approved_with_open_items", "review.json", None),
        ("review_target_unmatched", "review.json", None),
        ("unknown_review_target", "review.json", None),
    }


def review_messages(make_study, valid_files, *targets, status="draft"):
    items = [
        {**ITEM, "id": f"01JA2XK7Q8M3R5T6V9W0Y1Z2A{index}", "target": target}
        for index, target in enumerate(targets)
    ]
    approval = (
        {
            "reviewers": ["mkoenig"],
            "approved_by": "mkoenig",
            "approved": "2026-10-06T12:00:00Z",
        }
        if status == "approved"
        else {}
    )
    review = dump_json({"status": status, **approval, "items": items})
    study = load_study(make_study({**valid_files, "review.json": review}))
    return [issue.message for issue in check_relations(study)]


def test_rows_and_columns_of_plain_files_are_explained(make_study, valid_files):
    messages = review_messages(
        make_study,
        valid_files,
        {"file": "Example.pdf", "column": "page"},
        {"file": "study.json", "rows": {"name": "x"}},
        {"file": "notes.txt"},
    )
    assert messages == [
        "Review item 01JA2XK7Q8M3R5T6V9W0Y1Z2A0 targets rows or a column of Example.pdf; rows and column apply only to table files",
        "Review item 01JA2XK7Q8M3R5T6V9W0Y1Z2A1 targets rows or a column of study.json; rows and column apply only to table files",
        "Review item 01JA2XK7Q8M3R5T6V9W0Y1Z2A2 targets notes.txt, which is not a file of this study",
    ]


def test_approval_with_open_items_names_the_rule(make_study, valid_files):
    messages = review_messages(
        make_study, valid_files, {"file": "Example.pdf"}, {}, status="approved"
    )
    assert messages == [
        "A study can only be approved when no review item is open; 2 are open"
    ]


def test_approval_with_one_open_item_uses_the_singular(make_study, valid_files):
    messages = review_messages(make_study, valid_files, {}, status="approved")
    assert messages == [
        "A study can only be approved when no review item is open; 1 is open"
    ]


def test_scatter_mixing_groups_and_individuals_is_reported_at_the_other_rows(
    make_study, valid_files, tsv
):
    point = {
        "name": "age_vs_cmax",
        "x_measurement": "age",
        "x_unit": "yr",
        "y_interventions": "D1",
        "y_measurement": "cmax",
        "y_substance": "drug",
        "y_tissue": "plasma",
        "y_unit": "mg/l",
    }
    scatter = tsv(
        "scatters",
        {**point, "subjects": "S1", "x_mean": "30", "y_mean": "2"},
        {**point, "subjects": "all", "x_mean": "35", "y_mean": "2.5"},
        {**point, "subjects": "S2", "x_mean": "40", "y_mean": "3"},
        # Another scatter of groups only is fine.
        {**point, "name": "groups", "subjects": "all", "x_mean": "35", "y_mean": "2"},
    )
    study = load_study(make_study({**valid_files, "scatters_Fig2.tsv": scatter}))
    [issue] = check_relations(study)
    assert issue.code == "mixed_scatter_subjects"
    assert issue.severity == "error" and issue.category == "reference"
    assert issue.source is not None
    assert (issue.source.file, issue.source.row, issue.source.header) == (
        "scatters_Fig2.tsv",
        3,
        "subjects",
    )
    assert issue.message == (
        "Scatter 'age_vs_cmax' mixes groups and individuals: 'all' is a group, "
        "but 'S1' in line 2 is an individual"
    )


def test_scatter_with_as_many_groups_as_individuals_follows_its_first_row(
    make_study, valid_files, tsv
):
    point = {
        "name": "age_vs_cmax",
        "x_measurement": "age",
        "x_unit": "yr",
        "y_measurement": "cmax",
        "y_unit": "mg/l",
    }
    scatter = tsv(
        "scatters",
        {**point, "subjects": "all", "x_mean": "35", "y_mean": "2.5"},
        {**point, "subjects": "S1", "x_mean": "30", "y_mean": "2"},
    )
    study = load_study(make_study({**valid_files, "scatters_Fig2.tsv": scatter}))
    [issue] = [i for i in check_relations(study) if i.code == "mixed_scatter_subjects"]
    assert issue.source is not None and issue.source.row == 3


def test_names_of_one_cell_are_reported_a_bounded_number_of_times(
    make_study, valid_files, tsv
):
    from pkdb.studyformat.issues import REPEATED_ISSUES

    unknown = ",".join(f"X{i}" for i in range(10_000))
    repeated = ",".join(["D1"] * 10_000)
    files = {
        **valid_files,
        "outputs_Tab2.tsv": tsv(
            "outputs",
            {**CMAX, "interventions": unknown},
            {**CMAX, "mean": "3", "interventions": repeated},
        ),
    }
    issues = check_relations(load_study(make_study(files)))
    for code, total, row in (
        ("unknown_reference", 10_000, 2),
        ("duplicate_reference", 9_999, 3),
    ):
        found = [i for i in issues if i.code == code]
        assert len(found) == REPEATED_ISSUES + 1, code
        assert {i.source.row for i in found if i.source} == {row}
        assert found[-1].message.startswith(f"{total:,} names of this cell")


def test_every_review_item_with_an_unknown_target_is_reported(make_study, valid_files):
    # Review items are curation targets of their own, like rows, so none is folded
    # into a summary.
    from pkdb.studyformat.issues import REPEATED_ISSUES

    count = REPEATED_ISSUES + 5
    review = {
        "status": "draft",
        "items": [
            {
                **ITEM,
                "id": f"01JA2XK7Q8M3R5T6V9W0Y{i:05d}"[:26],
                "target": {"file": f"missing{i}.tsv"},
            }
            for i in range(count)
        ],
    }
    folder = make_study({**valid_files, "review.json": dump_json(review)})
    found = [
        i
        for i in check_relations(load_study(folder))
        if i.code == "unknown_review_target"
    ]
    assert len(found) == count
