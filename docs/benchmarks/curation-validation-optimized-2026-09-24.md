# Validation optimization results — 2026-09-24

The implementation reduces parsing and provenance-copy overhead without changing scientific rules:

- Header locations copy already validated coordinates instead of serializing and validating a new model for each cell. Private lookup maps remain independent, and unset-field serialization retains its prior behavior.
- Source-location private maps use per-instance copied defaults, avoiding repeated factory-signature inspection. Deep copies reuse immutable coordinate values while recursively copying mutable lookup maps with memoization; subclasses retain Pydantic's generic copy behavior.
- A preparation opens each XLSX workbook once and closes it on success or failure. The cache belongs to one bundle; later saves open a fresh workbook.
- XLSX iteration visits stored XML rows without constructing empty rows across large gaps. It keeps openpyxl's value decoding, physical coordinates, header conventions, comments, and row limits. Column letters are calculated once per table.

The sparse reader uses a small adapter around openpyxl's internal read-only parser. Its compatibility tests must run when upgrading openpyxl. Source snapshots, source hashes, upload checks, and scientific calculations are unchanged.

## Measurement method

Eight apixaban studies were copied to a fixed temporary workspace. The original implementation and optimized implementation each ran three times per study using Python 3.14.4 and bundled vocabulary, with no network requests. Timings exclude imports, output fingerprinting, server validation, and upload. Medians are local wall-clock observations, not guarantees for other machines or studies.

The original live-workspace benchmark cannot be compared directly for Frost2013a: a previously missing `Frost2013a_Tab3.png` appeared during the work, allowing scientific validation to reach a later error. The fixed-input comparison includes that image in both versions. Neither implementation modified the study sources.

## Measured results

| Study | Before (s) | After (s) | Speedup |
| --- | ---: | ---: | ---: |
| Abdollahizad2025 | 1.090 | 1.000 | 1.09× |
| Bashir2018 | 2.218 | 1.754 | 1.26× |
| Chang2016 | 1.984 | 1.627 | 1.22× |
| Cui2013 | 1.742 | 1.040 | 1.67× |
| Frost2013 | 3.370 | 1.869 | 1.80× |
| Frost2013a | 27.479 | 12.356 | 2.22× |
| Frost2014 | 6.930 | 3.284 | 2.11× |
| Frost2014a | 5.102 | 1.443 | 3.53× |

The sum of the eight study medians falls from **49.915 s to 24.374 s**: **51.2% less time (2.05× faster)**. Summed parsing time over the 24 runs falls from **107.237 s to 28.350 s (73.6% less)**. Scientific validation changes from 45.778 s to 43.137 s; read/snapshot work from 3.402 s to 3.596 s. The remaining work is predominantly scientific validation. Stage totals include all runs; the table contains per-study medians. Small differences are subject to host load and cache effects.

All **48 output fingerprints** agree within their respective study across both implementations and all repeats. Source file hashes in the fixed workspace were also checked after timing and remained unchanged. This establishes equivalence for this sample, not the entire corpus.

Regression checks: **146 Python client tests** and **80 importer/scientific-rule tests** pass, including sparse rows, dates/formulas, comments, physical cell coordinates, row limits, workbook cleanup, fresh reads after saved changes, isolated provenance maps, memoized copy graphs, and source-location subclasses. Ruff and whitespace checks pass.

Evidence: [before timings and hashes](curation-validation-optimized-2026-09-24-before.json), [after timings and hashes](curation-validation-optimized-2026-09-24-after.json), and [input file hashes](curation-validation-optimized-2026-09-24-inputs.json).

## Remaining costs

The [optimized profile](curation-validation-optimized-2026-09-24-profile.txt) contains 8 workbook opens for 47 table reads, and about 6,000 stored worksheet rows rather than millions of gap rows. Its instrumented pass takes 78.5 s; cumulative times overlap and must not be added. Scientific preparation accounts for 45.8 s cumulative. Recursive copying still accounts for 38.4 s across the whole pipeline, normalization for 13.8 s, and PK derivation for 3.3 s. Further copy reduction would require a stronger immutable-provenance contract; this change preserves independent mutable lookup maps instead of sharing them across prepared results.

## Reproduce

```bash
# Use the same unchanged input snapshot for both checkouts.
PYTHONPATH=/path/to/baseline/python/src python/.venv/bin/python \
  tools/curation_docs/benchmark_validation.py /path/to/fixed/studies \
  --limit 8 --repeats 3 --fingerprints --no-profile --output /tmp/before

python/.venv/bin/python tools/curation_docs/benchmark_validation.py \
  /path/to/fixed/studies --limit 8 --repeats 3 --fingerprints --output /tmp/after
```

`output_sha256` hashes the complete serialized prepared result, including scientific values and provenance, or the complete error report if preparation fails. All runs for the same study should have identical hashes in both versions. The separate profiled pass excludes fingerprinting; its instrumented times must not be interpreted as normal validation latency.
