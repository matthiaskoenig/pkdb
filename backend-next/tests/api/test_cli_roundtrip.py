import json

from pkdb.cli import main


def test_cli_validation_and_publication_roundtrip(
    client, creator_headers, valid_bundle, tmp_path, monkeypatch, capsys
):
    root = tmp_path / valid_bundle.study["name"]
    root.mkdir()
    (root / "study.json").write_text(json.dumps(valid_bundle.study))
    (root / "reference.json").write_text(json.dumps(valid_bundle.reference))
    for name, path in valid_bundle.files.items():
        (root / name).write_bytes(path.read_bytes())
    monkeypatch.setenv(
        "PKDB_API_TOKEN", creator_headers["Authorization"].removeprefix("Token ")
    )
    for command in ("validate", "upload"):
        assert (
            main([command, str(root), "--api-url", "http://testserver"], client=client)
            == 0
        )
        assert json.loads(capsys.readouterr().out)["ok"] is True
    response = client.get(
        f"/api/v2/studies/{valid_bundle.study['sid']}", headers=creator_headers
    )
    assert response.status_code == 200
    assert response.json()["sid"] == valid_bundle.study["sid"]
