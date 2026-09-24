# Local curation validation benchmark — 2026-09-24

The optimizations are now implemented; see the [fixed-input before/after comparison](curation-validation-optimized-2026-09-24.md).

Eight alphabetically first apixaban studies from the local `pkdb_data` checkout, three sequential runs per study with bundled vocabulary and no network requests. Python 3.14.4 on Linux. Times below are unprofiled wall-clock medians in seconds; each stage median is computed independently, so stage medians need not sum to the total. Imports, workspace discovery, queue wait, vocabulary synchronization, server validation, and upload are excluded. Vocabulary loading took 0.094 s once. This is a small local sample, not a whole-corpus benchmark.

| Study | Result | Total | Read / snapshot | Parse | Scientific validation |
| --- | --- | ---: | ---: | ---: | ---: |
| Abdollahizad2025 | valid | 1.656 | 0.082 | 1.115 | 0.466 |
| Bashir2018 | valid | 3.031 | 0.108 | 2.212 | 0.775 |
| Chang2016 | valid | 2.863 | 0.170 | 1.835 | 0.909 |
| Cui2013 | valid | 2.151 | 0.081 | 1.604 | 0.560 |
| Frost2013 | valid | 4.005 | 0.191 | 2.390 | 1.490 |
| Frost2013a | invalid | 23.096 | 0.363 | 22.753 | 0.000 |
| Frost2014 | valid | 7.937 | 0.187 | 5.590 | 1.971 |
| Frost2014a | invalid | 5.253 | 0.136 | 4.442 | 0.675 |

Across all 24 unprofiled runs, parsing takes **83.3%**, scientific validation **14.0%**, and read/snapshot work **2.6%**. The final stage includes snapshot cleanup. Frost2013a fails during parsing, so its scientific validation time is zero; that is not a fast successful validation.

## Where optimization is most promising

A separate cProfile pass over the eight studies took 129.2 s. Profiler overhead is substantial; use it to locate hot paths, not as an estimate of user-facing latency. Cumulative times overlap and must not be added.

1. **Source-location construction:** `SourceLocation.for_header` ran 35,235 times (46.1 s cumulative in the profiled pass). Pydantic private-attribute initialization repeatedly inspects default-factory signatures (168,680 signature inspections, 41.3 s cumulative). Investigate creating header locations with a carefully controlled copy, or reducing repeated location creation per row/header. Preserve private field maps, immutability expectations, and exact diagnostic coordinates; compare serialized reports before accepting a change.
2. **Workbook processing:** 47 `read_table` calls took 43.7 s cumulative; workbook opening accounts for 15.3 s. Cache open workbooks within one preparation snapshot when multiple sheets refer to the same file. The reader also yielded about 2.1 million rows despite only about 6,000 parsed XML rows. Investigate sparse/formatting-only worksheet gaps while preserving physical row numbers and row limits; resetting dimensions alone does not eliminate every gap.
3. **Copying:** deep copies account for 17.5 s cumulative across parsing and scientific processing. Investigate sharing immutable source metadata or copying only transformed records. Do not introduce mutation of canonical inputs or shared provenance.
4. **Scientific work:** `prepare_study` totals 21.1 s cumulative, normalization 5.9 s, and PK derivation 3.4 s. These are secondary targets in this sample. Preserve numerical outputs and all validation diagnostics in any optimization.

Source hashing and snapshot creation are a small portion of these runs. Keep their change-detection guarantees. Network latency must be measured separately against an explicitly chosen endpoint before making claims about connected validation or uploads. No scientific processing changes were made as part of this frontend update.

## Reproduce

```bash
python/.venv/bin/python tools/curation_docs/benchmark_validation.py \
  /path/to/pkdb_data/studies/apixaban --limit 8 --repeats 3 \
  --output /tmp/pkdb-validation-benchmark
```

The tool saves stage timings in `results.json`, a cumulative profile in `profile.txt`, and full pstats data in `validation.prof`. It uses private snapshots and does not modify studies or upload anything. Committed evidence: [raw timings](curation-validation-2026-09-24.json) and [profile](curation-validation-2026-09-24-profile.txt).
