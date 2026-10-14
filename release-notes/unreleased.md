# Unreleased

- The descriptions and comments of a study and of the notes of its tables in the local curation app no longer show a label such as Description 1 or Comment 1 by curator: each description and comment starts one line high, as high as the other fields, and grows with its text, and a comment shows its author once above its text, and screen readers still hear the name of each field (#954).

- On Windows, `pkdb upload --report` and `--resume` no longer stop a batch when another program has the report open for a moment while it is rewritten, such as a reader of the report, a virus scanner or a search indexer: Windows refuses to replace an open file, so the report write now retries for up to 5 seconds before the batch stops with a report error.
