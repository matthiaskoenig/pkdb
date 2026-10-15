"""Contract fixtures of the website: real answers of the study view routes (#963).

Each fixture is a JSON file in frontend/tests/fixtures/website-views/. A backend test builds the
answer with the real routes and compares it with the file, and the website's frontend tests
read the same file. A change on one side fails a test on that side: regenerate the files with
PKDB_UPDATE_CONTRACT=1 and let the frontend tests judge the new answers. Never edit the files
by hand.
"""

import json
import math
import os
from pathlib import Path

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "frontend"
    / "tests"
    / "fixtures"
    / "website-views"
)
UPDATE = "PKDB_UPDATE_CONTRACT"
REGENERATE = (
    f"{UPDATE}=1 uv run --project backend pytest -q "
    "backend/tests/api/test_frontend_search_contract.py -k website_contract"
)


def _normalized(value):
    """JSON values with floats rounded to 6 significant digits, so that platforms agree."""
    if isinstance(value, float):
        return float(f"{value:.6g}") if math.isfinite(value) else value
    if isinstance(value, dict):
        return {key: _normalized(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalized(item) for item in value]
    return value


def check_contract(name: str, value: object) -> None:
    """Compare `value` with the fixture `name`, or write it when PKDB_UPDATE_CONTRACT is 1."""
    path = FIXTURES / f"{name}.json"
    data = _normalized(json.loads(json.dumps(value)))
    if os.environ.get(UPDATE) == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")
        return
    assert path.is_file(), f"{path} is missing; run {REGENERATE}"
    assert json.loads(path.read_text(encoding="utf-8")) == data, (
        f"{path.name} differs from the answer of the backend; run {REGENERATE} "
        "and run the frontend unit tests against the new fixture"
    )
