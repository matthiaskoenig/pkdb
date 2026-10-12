"""The words of every request of the local curation app."""

import pytest

from pkdb.curation.actions import action_of

DEMO = "caffeine/Demo2020"


@pytest.mark.parametrize(
    ("method", "path", "body", "text", "failure"),
    [
        (
            "POST",
            "/local/studies/tables",
            {"study": DEMO, "action": "open"},
            "Open tables (POST /local/studies/tables)",
            "Could not open the tables of caffeine/Demo2020.",
        ),
        (
            "POST",
            "/local/studies/tables",
            {"study": DEMO, "action": "sync"},
            "Sync the workbook (POST /local/studies/tables)",
            "Could not sync the workbook of caffeine/Demo2020.",
        ),
        (
            "POST",
            "/local/studies/review",
            {"study": DEMO, "action": "status"},
            "Set the review status (POST /local/studies/review)",
            "Could not set the review status of caffeine/Demo2020.",
        ),
        (
            "POST",
            "/local/studies/metadata",
            {"study": DEMO},
            "Save study.json (POST /local/studies/metadata)",
            "Could not save study.json of caffeine/Demo2020.",
        ),
        (
            "POST",
            "/local/studies/tables/preview",
            {"study": DEMO},
            "Preview a table (POST /local/studies/tables/preview)",
            "Could not preview the new table of caffeine/Demo2020.",
        ),
        (
            "POST",
            "/local/reference/save",
            {"id": DEMO, "token": "t"},
            "Save reference.json (POST /local/reference/save)",
            "Could not save reference.json of caffeine/Demo2020.",
        ),
        (
            "POST",
            "/local/files/open",
            {"study_id": DEMO, "file": "Demo2020.pdf"},
            "Open file (POST /local/files/open)",
            "Could not open Demo2020.pdf of caffeine/Demo2020.",
        ),
        (
            "POST",
            "/local/files/open",
            {"study_id": DEMO},
            "Open folder (POST /local/files/open)",
            "Could not open the folder of caffeine/Demo2020.",
        ),
        (
            "POST",
            "/local/jobs",
            {"ids": [DEMO], "action": "upload"},
            "Upload (POST /local/jobs)",
            "Could not start the upload.",
        ),
        (
            "POST",
            "/local/settings",
            {"user": "curator"},
            "Save the settings (POST /local/settings)",
            "Could not save the settings.",
        ),
        (
            "POST",
            "/local/pause",
            {"paused": False},
            "Restart automatic actions (POST /local/pause)",
            "Could not restart the automatic actions.",
        ),
        (
            "POST",
            "/local/unknown",
            {},
            "Request (POST /local/unknown)",
            "Could not complete the request.",
        ),
        (
            "GET",
            "/local/state",
            None,
            "Read the workspace state (GET /local/state)",
            "Could not read the workspace state.",
        ),
        (
            "GET",
            "/local/studies/caffeine/Demo2020/tables/outputs_Tab2.tsv",
            None,
            "Read a table (GET /local/studies/caffeine/Demo2020/tables/outputs_Tab2.tsv)",
            "Could not read outputs_Tab2.tsv of caffeine/Demo2020.",
        ),
        (
            "GET",
            "/local/studies/caf%20feine/Demo2020",
            None,
            "Read the study (GET /local/studies/caf%20feine/Demo2020)",
            "Could not read caf feine/Demo2020.",
        ),
    ],
)
def test_every_request_has_a_label_and_a_failure(method, path, body, text, failure):
    action = action_of(method, path, body)
    assert (action.text(), action.failure()) == (text, failure)


def test_only_writes_and_opened_files_of_a_study_are_recorded():
    recorded = {
        path: action_of("POST", path, body).recorded
        for path, body in [
            ("/local/studies/metadata", {"study": DEMO}),
            ("/local/studies/review", {"study": DEMO, "action": "add"}),
            ("/local/studies/tables", {"study": DEMO, "action": "open"}),
            ("/local/reference/save", {"id": DEMO}),
            ("/local/files/open", {"study_id": DEMO}),
            ("/local/studies/tables/preview", {"study": DEMO}),
            ("/local/reference/preview", {"id": DEMO}),
            ("/local/settings", {}),
        ]
    }
    assert recorded == {
        "/local/studies/metadata": True,
        "/local/studies/review": True,
        "/local/studies/tables": True,
        "/local/reference/save": True,
        "/local/files/open": True,
        "/local/studies/tables/preview": False,
        "/local/reference/preview": False,
        "/local/settings": False,
    }
    assert action_of("POST", "/local/studies/tables", {"study": DEMO}).study == DEMO
    assert action_of("GET", f"/local/studies/{DEMO}").recorded is False


def test_a_body_of_any_shape_still_names_the_action():
    action = action_of("POST", "/local/studies/tables", ["not", "an", "object"])
    assert (action.label, action.failure(), action.study, action.recorded) == (
        "Change the tables",
        "Could not change the tables of the study.",
        None,
        False,
    )
    review = action_of("POST", "/local/studies/review", {"study": 3, "action": None})
    assert review.text() == "Change review.json (POST /local/studies/review)"
