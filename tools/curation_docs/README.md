# Curation browser checks and screenshots

Install the frontend development dependencies and Playwright Chromium to run developer browser tooling. These tools are not required by curators; the Python package bundles the local app.

To regenerate screenshots, launch the current package against a local workspace using `--no-browser`. Let the renderer consume the fresh launch URL; it validates the selected studies itself. The committed images show real offline validation of the apixaban workspace on 2026-09-24. They are examples of that source revision, not fixed scientific acceptance counts.

```bash
pkdb curate /path/to/pkdb_data/studies/apixaban --offline --no-browser
# Pass the fresh printed launch URL to the renderer before opening it elsewhere.
PKDB_CURATION_URL='http://127.0.0.1:PORT/#token=LAUNCH_TOKEN' node tools/curation_docs/render.mjs
```

The renderer captures the actual app into `docs/images/curation/workspace.png` and `problems.png`, filtering to Frost2013 studies by default. Override the filter with `PKDB_CURATION_SCREENSHOT_FILTER`. The launch URL is never printed by the renderer. Use an offline workspace or a non-sensitive test account for documentation screenshots; do not expose private source records or credentials.

Validation performance can be measured offline with `python/.venv/bin/python tools/curation_docs/benchmark_validation.py /path/to/studies`. See [measured timings and optimization opportunities](../../docs/benchmarks/curation-validation-2026-09-24.md).

Implemented optimizations and a fixed-input comparison are documented in [validation optimization results](../../docs/benchmarks/curation-validation-optimized-2026-09-24.md). Pass `--fingerprints` to record output equivalence hashes and `--no-profile` to skip the separate instrumented pass.
