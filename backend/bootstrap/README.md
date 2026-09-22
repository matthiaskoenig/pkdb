# Generated vocabulary

The authoritative editable definitions are in `../pkdb_data/info_nodes/definitions/`.
Do not edit `vocabulary.json` or `provenance.json` manually. Regenerate them from the
repository root with:

```bash
uv run --project backend --python 3.14 python scripts/update_vocabulary.py
```

Use `--check` to detect stale generated files. See [the vocabulary guide](../../docs/vocabulary.md)
for authoring, cached metadata, and loading updated terms into Docker.

`users.json` is maintained separately and is not changed by generation. Compose loads
the vocabulary automatically at startup. `pkdb bootstrap-study PATH` prepares disabled
attribution accounts without changing existing credentials or roles.
