from datetime import UTC, datetime

import pytest

from pkdb.identity import Author
from pkdb.schemas.review import ReviewTarget
from pkdb.studyformat.issues import make_issue, row_issue
from pkdb.studyformat.load import load_study
from pkdb.studyformat.review_edit import (
    ApprovalRefused,
    ReviewError,
    acknowledge,
    add_item,
    dismiss,
    matching_warnings,
    read_review,
    reopen,
    reply,
    resolve,
    set_status,
    target_for_issue,
    warning_locations,
)
from pkdb.studyformat.revision import RevisionConflict
from pkdb.studyformat.validation import validate_folder

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
PERSON = Author("curator")
AGENT = Author("curator", "claude-opus-5-5")


def test_item_lifecycle(valid_study):
    item, revision = add_item(
        valid_study,
        AGENT,
        kind="uncertainty",
        text="Digitized; check.",
        target=ReviewTarget(file="timecourses_Fig1.tsv", rows={"label": "drug_plasma"}),
        now=NOW,
    )
    assert item.agent == "claude-opus-5-5" and item.author == "curator"
    revision = reply(
        valid_study, PERSON, item.id, "Checked two points.", revision=revision, now=NOW
    )
    revision = resolve(
        valid_study, PERSON, item.id, "All good.", revision=revision, now=NOW
    )
    stored = read_review(valid_study).review.items[0]
    assert stored.state == "resolved" and stored.resolved_by == "curator"
    assert len(stored.thread) == 2
    with pytest.raises(ReviewError, match="resolved, not open"):
        resolve(valid_study, PERSON, item.id, revision=revision, now=NOW)
    revision = reopen(valid_study, PERSON, item.id, revision=revision, now=NOW)
    assert read_review(valid_study).review.items[0].resolved is None
    with pytest.raises(ReviewError, match="open already"):
        reopen(valid_study, PERSON, item.id, revision=revision, now=NOW)


def test_unknown_item(valid_study):
    with pytest.raises(ReviewError, match="does not exist"):
        reply(valid_study, PERSON, "01ARZ3NDEKTSV4RRFFQ69G5FAV", "Hi", now=NOW)


def test_stale_revision(valid_study):
    _, first = add_item(valid_study, PERSON, kind="question", text="One?", now=NOW)
    add_item(valid_study, PERSON, kind="question", text="Two?", revision=first, now=NOW)
    with pytest.raises(RevisionConflict):
        add_item(
            valid_study,
            PERSON,
            kind="question",
            text="Three?",
            revision=first,
            now=NOW,
        )


def test_approval_rules(valid_study, sf_vocabulary):
    item, revision = add_item(
        valid_study, PERSON, kind="question", text="Open?", now=NOW
    )
    approve = dict(vocabulary=sf_vocabulary, now=NOW)
    with pytest.raises(ApprovalRefused, match="open"):
        set_status(valid_study, PERSON, "approved", revision=revision, **approve)
    revision = resolve(valid_study, PERSON, item.id, revision=revision, now=NOW)
    with pytest.raises(ApprovalRefused, match="person"):
        set_status(valid_study, AGENT, "approved", revision=revision, **approve)
    revision = set_status(valid_study, PERSON, "approved", revision=revision, **approve)
    review = read_review(valid_study).review
    assert (review.status, review.approved_by, review.reviewers) == (
        "approved",
        "curator",
        ["curator"],
    )
    set_status(valid_study, PERSON, "in_review", revision=revision, **approve)
    review = read_review(valid_study).review
    assert review.approved_by is None and review.approved is None


def test_approval_refused_with_validation_errors(valid_study, sf_vocabulary):
    (valid_study / "Example_Fig1.png").unlink()  # missing_image is an error
    with pytest.raises(ApprovalRefused, match="error"):
        set_status(valid_study, PERSON, "approved", vocabulary=sf_vocabulary, now=NOW)


def _refusal(folder, vocabulary) -> str:
    with pytest.raises(ApprovalRefused) as refused:
        set_status(folder, PERSON, "approved", vocabulary=vocabulary, now=NOW)
    return str(refused.value)


def test_approval_refusal_counts_the_open_items(valid_study, sf_vocabulary):
    _, revision = add_item(valid_study, PERSON, kind="question", text="One?", now=NOW)
    assert _refusal(valid_study, sf_vocabulary) == "1 review item is open"
    add_item(
        valid_study, PERSON, kind="question", text="Two?", revision=revision, now=NOW
    )
    assert _refusal(valid_study, sf_vocabulary) == "2 review items are open"


def test_approval_refusal_counts_the_validation_errors(valid_study, sf_vocabulary):
    (valid_study / "Example_Fig1.png").unlink()  # missing_image of timecourses_Fig1.tsv
    assert _refusal(valid_study, sf_vocabulary) == "Validation has 1 error"
    (valid_study / "Example_Fig2.png").unlink()  # missing_image of scatters_Fig2.tsv
    assert _refusal(valid_study, sf_vocabulary) == "Validation has 2 errors"


def _outside_range(folder, vocabulary):
    """Make the mean of the timecourse row at time 1 lie outside its range; the warning."""
    timecourses = folder / "timecourses_Fig1.tsv"
    lines = timecourses.read_text().splitlines()
    header = lines[0].split("\t")
    row = lines[2].split("\t")
    row[header.index("min")], row[header.index("max")] = "3", "4"  # mean outside
    lines[2] = "\t".join(row)
    timecourses.write_text("\n".join(lines) + "\n")
    return next(
        i
        for i in validate_folder(folder, vocabulary).issues
        if i.code == "outside_range"
    )


def test_acknowledge_targets_exactly_the_row(valid_study, sf_vocabulary):
    issue = _outside_range(valid_study, sf_vocabulary)
    target = target_for_issue(load_study(valid_study), issue)
    assert target is not None
    assert target.file == "timecourses_Fig1.tsv" and target.column == "mean"
    assert target.rows == {"label": "drug_plasma", "time": "1"}
    acknowledge(valid_study, PERSON, issue, "As printed.", now=NOW)
    codes = [i.code for i in validate_folder(valid_study, sf_vocabulary).issues]
    assert "outside_range" not in codes
    stored = read_review(valid_study).review.items[0]
    assert (stored.kind, stored.state, stored.acknowledges) == (
        "issue",
        "resolved",
        "outside_range",
    )


def test_acknowledge_refuses_errors(valid_study, sf_vocabulary):
    (valid_study / "Example_Fig1.png").unlink()
    issue = next(
        i
        for i in validate_folder(valid_study, sf_vocabulary).issues
        if i.code == "missing_image"
    )
    with pytest.raises(ReviewError):
        acknowledge(valid_study, PERSON, issue, "No.", now=NOW)


def _codes(folder, vocabulary):
    return [issue.code for issue in validate_folder(folder, vocabulary).issues]


def test_dismissing_an_acknowledgement_brings_its_warning_back(
    valid_study, sf_vocabulary
):
    issue = _outside_range(valid_study, sf_vocabulary)
    item, revision = acknowledge(valid_study, PERSON, issue, "As printed.", now=NOW)
    assert "outside_range" not in _codes(valid_study, sf_vocabulary)
    revision = dismiss(
        valid_study, PERSON, item.id, "Not as printed.", revision=revision, now=NOW
    )
    stored = read_review(valid_study).review.items[0]
    assert (stored.state, stored.resolved_by, len(stored.thread)) == (
        "dismissed",
        "curator",
        1,
    )
    assert "outside_range" in _codes(valid_study, sf_vocabulary)
    with pytest.raises(ReviewError, match="dismissed"):
        dismiss(valid_study, PERSON, item.id, revision=revision, now=NOW)
    revision = reopen(valid_study, PERSON, item.id, revision=revision, now=NOW)
    revision = dismiss(valid_study, PERSON, item.id, revision=revision, now=NOW)
    assert read_review(valid_study).review.items[0].state == "dismissed"


APPROVED = "The study is approved; set the status to in_review first"


def _approve(folder, vocabulary):
    return set_status(folder, PERSON, "approved", vocabulary=vocabulary, now=NOW)


def test_approved_study_refuses_open_items(valid_study, sf_vocabulary):
    item, revision = add_item(
        valid_study, PERSON, kind="question", text="Why?", now=NOW
    )
    revision = resolve(valid_study, PERSON, item.id, revision=revision, now=NOW)
    revision = _approve(valid_study, sf_vocabulary)
    with pytest.raises(ReviewError, match=APPROVED):
        add_item(valid_study, PERSON, kind="issue", text="Late.", now=NOW)
    with pytest.raises(ReviewError, match=APPROVED):
        reopen(valid_study, PERSON, item.id, now=NOW)
    assert read_review(valid_study).revision == revision
    # A resolved acknowledgement keeps the study valid, so it stays allowed.
    issue = _outside_range(valid_study, sf_vocabulary)
    acknowledge(valid_study, PERSON, issue, "As printed.", now=NOW)
    review = read_review(valid_study).review
    assert review.status == "approved" and len(review.items) == 2
    assert "approved_with_open_items" not in _codes(valid_study, sf_vocabulary)


def test_add_item_refuses_a_target_outside_the_study(valid_study):
    before = read_review(valid_study).revision
    with pytest.raises(ReviewError, match="not a file of this study") as error:
        add_item(
            valid_study,
            PERSON,
            kind="question",
            text="Where?",
            target=ReviewTarget(file="timecourses_Fig9.tsv"),
            now=NOW,
        )
    assert [issue.code for issue in error.value.issues] == ["unknown_review_target"]
    assert read_review(valid_study).revision == before
    item, _ = add_item(
        valid_study,
        PERSON,
        kind="question",
        text="Which panel?",
        target=ReviewTarget(file="Example_Fig1.png"),
        now=NOW,
    )
    assert item.target == ReviewTarget(file="Example_Fig1.png")


def test_approving_an_approved_study_keeps_the_approval(valid_study, sf_vocabulary):
    revision = _approve(valid_study, sf_vocabulary)
    later = datetime(2026, 10, 7, 9, 30, tzinfo=UTC)
    again = set_status(
        valid_study,
        Author("second"),
        "approved",
        vocabulary=sf_vocabulary,
        revision=revision,
        now=later,
    )
    assert again == revision
    review = read_review(valid_study).review
    assert (review.approved_by, review.approved, review.reviewers) == (
        "curator",
        NOW,
        ["curator"],
    )
    with pytest.raises(RevisionConflict):
        set_status(
            valid_study,
            PERSON,
            "approved",
            vocabulary=sf_vocabulary,
            revision="0" * 64,
            now=later,
        )


def test_target_filter_adds_columns_until_it_matches_one_row(
    make_study, valid_files, tsv
):
    timecourse = {
        "label": "drug_plasma",
        "interventions": "D1",
        "measurement": "concentration",
        "substance": "drug",
        "tissue": "plasma",
        "time": "1",
        "time_unit": "h",
        "unit": "mg/l",
    }
    files = {
        **valid_files,
        "timecourses_Fig1.tsv": tsv(
            "timecourses",
            {**timecourse, "subjects": "S1", "mean": "2"},
            {**timecourse, "subjects": "S2", "mean": "3"},
        ),
    }
    study = load_study(make_study(files))
    table = study.table("timecourses_Fig1.tsv")
    assert table is not None
    row = next(row for row in table.rows if row.cells["subjects"] == "S2")
    issue = row_issue(table, row, "outside_range", "Out of range.", "mean")
    target = target_for_issue(study, issue)
    assert target is not None
    assert target.rows == {"label": "drug_plasma", "time": "1", "subjects": "S2"}
    assert target.column == "mean"
    assert table.matching_lines(target.rows) == {row.line}


def test_matching_warnings_and_their_locations():
    table = "timecourses_Fig1.tsv"
    at_mean = make_issue(
        "outside_range", "Out.", file=table, line=3, header="mean", severity="warning"
    )
    at_sd = make_issue(
        "outside_range", "Out.", file=table, line=3, header="sd", severity="warning"
    )
    below = make_issue(
        "outside_range", "Out.", file=table, line=4, header="mean", severity="warning"
    )
    error = make_issue(
        "outside_range", "Out.", file=table, line=3, header="mean", severity="error"
    )
    other_code = make_issue("missing_image", "No.", file=table, severity="warning")
    other_file = make_issue(
        "outside_range", "Out.", file="subjects.tsv", line=3, severity="warning"
    )
    project = [
        make_issue("unknown_dataset", text, file="Example_Fig1.wpd.json")
        for text in ("Legend.", "Axis labels.")
    ]
    issues = [at_mean, at_sd, below, error, other_code, other_file, *project]
    matches = matching_warnings(issues, "outside_range", table)
    assert matches == [at_mean, at_sd, below]
    assert matching_warnings(issues, "outside_range", table, line=3) == [at_mean, at_sd]
    assert matching_warnings(issues, "outside_range", table, column="mean") == [
        at_mean,
        below,
    ]
    assert matching_warnings(issues, "outside_range", table, 3, "sd") == [at_sd]
    assert matching_warnings(issues, "outside_range", "reference.json") == []
    assert warning_locations(matches) == {(3, "mean"), (3, "sd"), (4, "mean")}
    file_level = matching_warnings(issues, "unknown_dataset", "Example_Fig1.wpd.json")
    assert file_level == project
    assert warning_locations(file_level) == {(None, None)}
