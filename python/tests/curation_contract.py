"""Contract fixtures: real answers of the local curation API that the front-end tests read.

Each fixture is a JSON file in frontend/tests/fixtures/curation-contract/. A Python test builds
the answer with the real engine and library and compares it with the file, and
frontend/tests/unit/curation-contract.spec.ts reads the same file. A change on one side fails a
test on that side: regenerate the files with PKDB_UPDATE_CONTRACT=1 and let the front-end tests
judge the new answers. Never edit the files by hand.
"""

import json
import math
import os
from pathlib import Path

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "tests"
    / "fixtures"
    / "curation-contract"
)
UPDATE = "PKDB_UPDATE_CONTRACT"
REGENERATE = f"{UPDATE}=1 uv run --locked pytest -q tests/test_curation_contract.py"


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
        f"{path.name} differs from the answer of the local API; run {REGENERATE} "
        "and run the front-end unit tests against the new fixture"
    )
