# Unreleased

## Changes

- `tools/curation_testing/make_fixture.py` draws the scanned figure and the table images of the curation test fixture as charts of sbmlsim-core, drawn into PNG files by its renderer, and writes the placeholder PDFs with fpdf2, so matplotlib is needed nowhere: the script runs with `uv run --project python --with fpdf2`. The fixture is drawn again: the images, the pixels of its WebPlotDigitizer project and the PDFs change, its data and its problems stay, and the contract fixtures of the curation app follow (#1061).
- The caps of the error bars of the scanned figure of the curation test fixture are 8 points (11 pixels) wide with sbmlsim-core 0.37.0, as matplotlib drew them: `make_fixture.py` gives sbmlsim-core matplotlib's `capsize` of 4, which it reads as such from 0.37.0 on, and requires `sbmlsim-core>=0.37.0`. The fixture keeps its data, its digitization and its contract fixtures (#1062).
