# Unreleased

- `pkdb upload` of a parent folder uploads the other studies when some of them share a study identifier or a publication and source (#PR). Before, one such pair, such as two pkdb_data folders whose `study.json` names the same PubMed ID, stopped the whole batch with `Multiple studies claim reference ...` before any upload; now each study of the pair fails with `identity_conflict` and names the others, because PK-DB keeps one study per publication and source and the order of the uploads would decide which one.
