# Unreleased

- The client gives an idle connection to PK-DB up after two seconds instead of five (#PR). uvicorn closes a connection after five idle seconds, so a write sent on a connection that it closed at that moment got no answer, ended as `unreachable` with an unknown outcome and stopped the batch; this happened once in an upload of all pkdb_data studies with eight jobs.

- `pkdb upload` of a parent folder uploads the other studies when some of them share a study identifier or a publication and source (#904). Before, one such pair, such as two pkdb_data folders whose `study.json` names the same PubMed ID, stopped the whole batch with `Multiple studies claim reference ...` before any upload; now each study of the pair fails with `identity_conflict` and names the others, because PK-DB keeps one study per publication and source and the order of the uploads would decide which one.
