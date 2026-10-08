# Curation app screenshots and benchmarks

`render.mjs` renders the screenshots of [the local curation app guide](../../docs/local-curation.md) into `docs/images/curation/`: `overview.png`, `review.png`, `sources.png`, `metadata.png` and `tables-conflict.png`, in the light theme, 1440 pixels wide. Most are 900 pixels high; `review.png` is 1010 and `sources.png` 1100 pixels high, so that they show the study header together with the whole review target or the whole figure. It drives the real app of a running `pkdb curate` in Chromium by roles and labels. The app runs on a copy of the synthetic fixture workspace of the browser tests (`tools/curation_testing/fixture`), so the images show no real publication or account.

The renderer changes the workspace: for `tables-conflict.png` it edits the same cell of `caffeine/Demo2020` in the workbook and in `timecourses_Fig1.tsv`. Start every run from a fresh copy.

You need the frontend dependencies with Playwright Chromium, the built app, and [uv](https://docs.astral.sh/uv/). From the repository root:

```bash
(cd frontend && npm ci && npx playwright install chromium && npm run build:curation)

# A fresh copy of the fixture workspace, with the workbook of Demo2020, in a folder named
# demo_studies, which the header of every image shows:
SCRATCH=$(mktemp -d)
uv run --project python python tools/curation_testing/workspace.py "$SCRATCH/demo_studies"

# pkdb curate on it: offline, as the user curator, without your API key, settings or cache.
env -u PKDB_API_KEY -u PKDB_ENDPOINT PKDB_USER=curator PKDB_NO_UPDATE=1 PKDB_CACHE_DIR="$SCRATCH/cache" \
  uv run --project python pkdb curate "$SCRATCH/demo_studies" --offline --no-browser --state-dir "$SCRATCH/state"
```

In a second terminal, pass the launch URL that `pkdb curate` printed, before anything else opens it:

```bash
PKDB_CURATION_URL='http://127.0.0.1:PORT/#token=LAUNCH_TOKEN' node tools/curation_docs/render.mjs
```

The renderer imports the column letters from `frontend/src/curation-app/columns.ts`, which Node.js runs without a build step since version 22.18. It accepts only a launch URL on a loopback address, and refuses a workspace folder with another name than `demo_studies`. It never prints the launch token: an error message shows `<launch token>` in its place. Before each image it waits until the app shows the expected content, no menu is open and nothing moves. It writes the five images and quantizes them to 256 colors with `optimize_png.py`, which keeps them small without a visible change. Set `PKDB_CURATION_SCREENSHOTS` to a folder to write the images there instead. Stop `pkdb curate` with Ctrl+C afterwards, and look at every image before you commit it.

Validation performance can be measured offline with `python/.venv/bin/python tools/curation_docs/benchmark_validation.py /path/to/studies`. See [measured timings and optimization opportunities](../../docs/benchmarks/curation-validation-2026-09-24.md).

Implemented optimizations and a fixed-input comparison are documented in [validation optimization results](../../docs/benchmarks/curation-validation-optimized-2026-09-24.md). Pass `--fingerprints` to record output equivalence hashes and `--no-profile` to skip the separate instrumented pass.
