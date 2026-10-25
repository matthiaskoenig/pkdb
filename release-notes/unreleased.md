# Unreleased

- The measurements `muliple_dosing_cmin` and `muliple_dosing_cmax` are renamed to `multiple_dosing_cmin` and `multiple_dosing_cmax`; their SIDs stay the same, so the stored measurements take the new names without a database migration. The misspelled names stay as deprecated terms: study folders that use them still validate, with the warning `deprecated_measurement`, until they are renamed. `docs/vocabulary.md` describes how to rename a term.
