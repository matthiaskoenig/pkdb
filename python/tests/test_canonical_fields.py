"""Study format 2 fields of the canonical model: statistics, schedules, release and review."""

import subprocess
import sys

import pytest
from pydantic import ValidationError

from pkdb.schemas import review
from pkdb.schemas.study import Intervention, Metadata, Statistics
from pkdb.studyformat import models

INTERVENTION = {
    "key": "dose",
    "name": "dose",
    "measurement_type": "dosing",
    "substance": "caffeine",
    "unit": "mg",
    "time_unit": "h",
}
METADATA = {"name": "Example", "creator": "mkoenig"}
REVIEW = {
    "status": "in_review",
    "reviewers": ["mkoenig"],
    "items": [
        {
            "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
            "kind": "uncertainty",
            "state": "resolved",
            "target": {"file": "timecourses_Fig2.tsv", "column": "sd"},
            "text": "The legend does not say whether the error bars are SD or SE.",
            "author": "mkoenig",
            "created": "2026-10-05T10:12:00Z",
            "resolved_by": "mkoenig",
            "resolved": "2026-10-06T08:00:00Z",
        }
    ],
}


def test_statistics_carry_geometric_values_and_error_bars():
    statistics = Statistics(
        mean=10.0,
        gmean=9.5,
        gsd=1.3,
        gcv=0.27,
        error_bar=12.0,
        error_type="sd",
    )
    assert (statistics.gmean, statistics.gsd, statistics.gcv) == (9.5, 1.3, 0.27)
    assert (statistics.error_bar, statistics.error_type) == (12.0, "sd")
    assert Statistics().model_dump(exclude_none=True) == {}


@pytest.mark.parametrize("error_type", ["sd", "se", "gsd"])
def test_error_types_are_sd_se_or_gsd(error_type):
    assert Statistics(error_type=error_type).error_type == error_type


@pytest.mark.parametrize("error_type", ["cv", "SD", "", "range"])
def test_other_error_types_are_rejected(error_type):
    with pytest.raises(ValidationError):
        Statistics(error_type=error_type)


@pytest.mark.parametrize("field", ["gmean", "gsd", "gcv", "error_bar"])
def test_new_statistics_are_finite_numbers(field):
    for value in (float("nan"), float("inf"), "1.0"):
        with pytest.raises(ValidationError):
            Statistics.model_validate({field: value})


def test_intervention_schedule_with_time_list():
    intervention = Intervention.model_validate({**INTERVENTION, "time": [0, 12, 40]})
    assert intervention.time == [0, 12, 40]
    assert intervention.interval is None and intervention.doses is None


def test_intervention_schedule_with_interval_and_doses():
    intervention = Intervention.model_validate(
        {**INTERVENTION, "time": 0, "interval": 24, "doses": 7, "subject": "all"}
    )
    assert (intervention.time, intervention.interval, intervention.doses) == (
        0,
        24,
        7,
    )
    assert intervention.subject == "all"


def test_intervention_keeps_accepting_schedule_text_for_now():
    assert Intervention.model_validate({**INTERVENTION, "time": "S0T24R7"}).time == (
        "S0T24R7"
    )


@pytest.mark.parametrize("time", [[], [0], [0, "12"], [0, float("nan")]])
def test_intervention_time_lists_have_two_finite_numbers(time):
    with pytest.raises(ValidationError):
        Intervention.model_validate({**INTERVENTION, "time": time})


@pytest.mark.parametrize("doses", [0, -1, 1.5, "7", True])
def test_intervention_doses_are_whole_numbers_of_at_least_one(doses):
    with pytest.raises(ValidationError):
        Intervention.model_validate({**INTERVENTION, "doses": doses})


def test_intervention_interval_is_a_finite_number():
    for interval in (float("inf"), "24"):
        with pytest.raises(ValidationError):
            Intervention.model_validate({**INTERVENTION, "interval": interval})


def test_intervention_subject_is_a_name():
    with pytest.raises(ValidationError):
        Intervention.model_validate({**INTERVENTION, "subject": ""})


def test_metadata_carries_issue_release_and_review():
    metadata = Metadata.model_validate(
        {
            **METADATA,
            "issue": 2158,
            "release": {"pkdb_id": "PKDB01237", "date": "2026-09-28"},
            "review": REVIEW,
        }
    )
    assert metadata.issue == 2158
    assert metadata.release == review.Release(pkdb_id="PKDB01237", date="2026-09-28")
    assert metadata.review == review.Review.model_validate(REVIEW)
    assert Metadata.model_validate(metadata.model_dump(mode="json")) == metadata


def test_metadata_without_release_or_review():
    metadata = Metadata.model_validate(METADATA)
    assert (metadata.issue, metadata.release, metadata.review) == (None, None, None)


@pytest.mark.parametrize(
    "change",
    [
        {"issue": 0},
        {"issue": -3},
        {"issue": "12"},
        {"release": {"pkdb_id": "PKDB1237", "date": "2026-09-28"}},
        {"release": {"pkdb_id": "PKDB01237"}},
        {"review": {"status": "done"}},
        {"review": {**REVIEW, "extra": 1}},
    ],
)
def test_metadata_rejects_invalid_issue_release_and_review(change):
    with pytest.raises(ValidationError):
        Metadata.model_validate({**METADATA, **change})


def test_study_format_models_reuse_the_shared_release_and_review():
    for name in ("Release", "ReviewTarget", "ThreadEntry", "ReviewItem", "Review"):
        assert getattr(models, name) is getattr(review, name)


def test_schemas_do_not_load_study_format():
    code = """
import sys
import pkdb.schemas.review, pkdb.schemas.study
assert not any(name.startswith('pkdb.studyformat') for name in sys.modules)
"""
    subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )
