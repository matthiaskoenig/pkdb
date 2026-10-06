from datetime import UTC, datetime

import pytest

from pkdb.identity import Author
from pkdb.schemas.review import ReviewTarget
from pkdb.studyformat.load import load_study
from pkdb.studyformat.review_edit import (
    ApprovalRefused,
    ReviewError,
    acknowledge,
    add_item,
    dismiss,
    read_review,
    reopen,
    reply,
    resolve,
    set_status,
    target_for_issue,
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
    with pytest.raises(ReviewError):
        dismiss(valid_study, PERSON, item.id, revision=revision, now=NOW)
    revision = reopen(valid_study, PERSON, item.id, revision=revision, now=NOW)
    assert read_review(valid_study).review.items[0].resolved is None


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


def test_acknowledge_targets_exactly_the_row(valid_study, sf_vocabulary):
    timecourses = valid_study / "timecourses_Fig1.tsv"
    lines = timecourses.read_text().splitlines()
    header = lines[0].split("\t")
    row = lines[2].split("\t")
    row[header.index("min")], row[header.index("max")] = "3", "4"  # mean outside
    lines[2] = "\t".join(row)
    timecourses.write_text("\n".join(lines) + "\n")
    issue = next(
        i
        for i in validate_folder(valid_study, sf_vocabulary).issues
        if i.code == "outside_range"
    )
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
