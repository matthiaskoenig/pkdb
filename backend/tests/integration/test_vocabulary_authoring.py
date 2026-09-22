"""Exercise authored Python definitions through generated JSON and database loading."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from pkdb.db.bootstrap import bootstrap, load_vocabulary


def test_authored_term_reaches_backend_and_invalid_edit_preserves_json(
    tmp_path, db_session
):
    root = Path(__file__).resolve().parents[3]
    workspace = tmp_path / "repository"
    definitions_root = workspace / "backend/info_nodes"
    shutil.copytree(root / "backend/info_nodes", definitions_root)
    script = workspace / "scripts/update_vocabulary.py"
    script.parent.mkdir()
    shutil.copy2(root / "scripts/update_vocabulary.py", script)
    definitions = definitions_root / "definitions/anthropometry.py"
    definitions.write_text(
        definitions.read_text() + "\nANTHROPOMETRY_NODES.extend([\n"
        '    MeasurementType(sid="local-response", description="Test response",\n'
        '                    parents=["physiological measurement"],\n'
        "                    dtype=DType.CATEGORICAL),\n"
        '    Choice(sid="local-responder", name="responder", description="Response",\n'
        '           parents=["local-response"]),\n'
        "])\n"
    )
    substances = definitions_root / "definitions/substance.py"
    substances.write_text(
        substances.read_text() + "\nSUBSTANCE_NODES.append(Substance(\n"
        '    sid="local-drug", description="Explicit chemical properties",\n'
        '    mass=123.4, formula="C6H7NO2", charge=0,\n'
        '    annotations=[(BQB.IS, "chebi/CHEBI:999999999")],\n'
        "))\n"
    )
    output = workspace / "backend/bootstrap"
    output.mkdir()
    (output / "users.json").write_text("[]\n")
    command = [sys.executable, str(script), "--offline"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stderr
    snapshot = json.loads((output / "vocabulary.json").read_text())
    node = next(n for n in snapshot["nodes"] if n["sid"] == "local-response")
    assert set(node["definition"]["choices"]) == {"NR", "responder"}
    with db_session.begin():
        report = bootstrap(output, db_session)
        assert not report.errors
        rule = load_vocabulary(db_session).measurement_map()["local-response"]
        assert rule.dtype == "categorical" and set(rule.choices) == {"NR", "responder"}
        substance = load_vocabulary(db_session).substance_map()["local-drug"]
        assert substance.mass == 123.4 and substance.formula == "C6H7NO2"
        assert substance.charge == 0
    before = {p.name: p.read_bytes() for p in output.glob("*.json")}
    definitions.write_text(
        definitions.read_text().replace(
            'parents=["physiological measurement"],', 'parents=["missing-parent"],'
        )
    )
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    assert result.returncode != 0
    assert "Unknown parent missing-parent" in result.stderr
    assert {p.name: p.read_bytes() for p in output.glob("*.json")} == before
