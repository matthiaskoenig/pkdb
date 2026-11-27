# Unreleased

## Changes

- `tools/curation_testing/make_fixture.py` draws the scanned figure and the table images of the curation test fixture as charts of sbmlsim-core, drawn into PNG files by its renderer, and writes the placeholder PDFs with fpdf2, so matplotlib is needed nowhere: the script runs with `uv run --project python --with fpdf2`. The fixture is drawn again: the images, the pixels of its WebPlotDigitizer project and the PDFs change, its data and its problems stay, and the contract fixtures of the curation app follow.
