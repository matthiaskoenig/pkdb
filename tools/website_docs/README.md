# Website screenshots

`render.mjs` renders the screenshots of [the web interface guide](../../docs/web-interface.md) into `docs/images/web/`, in the light theme, 1440 pixels wide, in a window 900 pixels high:

- as a visitor: `login.png`, `browse-studies.png` and `browse-measurements.png` (the data search on its Studies and Measurements tabs), `study-details.png` (the record page of a study without a study page) and `timecourse.png` (the plot of its timecourse), `studies.png` (the Studies page), `study-metadata.png` and `study-data.png` (a study page on Metadata and on Data);
- as the curator of that study: `studies-curator.png` (the Studies page), `study-curator-data.png` and `study-curator-review.png` (the study page on Data and on Review).

Each image shows the page from its top to the end of its content, without the footer, whose release and commit change with every build. The images of the data search and of the record page, which are longer, end at 1200 pixels, above the first line of text that this height would cut. It drives the real website in Chromium by roles and labels, against the disposable website of the browser tests ([tools/frontend_testing](../frontend_testing/README.md)): its production build behind Nginx, with the artificial fixture data of `serve.py` in a database on a tmpfs, so the images show no real publication or account. The study pages show `drug/Format2Public`, a public study format 2 study of the fixture that its account `curator` curates, and the record page shows the study format 1 study `FRONTEND_SCOPE`.

You need Docker, the frontend dependencies with Playwright Chromium, the built website, and [uv](https://docs.astral.sh/uv/). From the repository root:

```bash
(cd frontend && npm ci && npx playwright install chromium && npm run build)
tools/website_docs/run.sh
```

`run.sh` starts the Compose project `pkdb-frontend-test` of the browser tests from a fresh fixture, builds the backend from this checkout, runs `render.mjs` and removes the project again on exit, as `npm run test:e2e` does; it never touches another project or a deployment volume. To render against that website while it already runs, run `node tools/website_docs/render.mjs`; set `PKDB_WEBSITE_URL` for another address on a loopback interface. Before each image the renderer waits until the page shows the expected content, nothing loads, no menu is open and nothing moves, moves the pointer away and takes the focus from every control. It quantizes the images with [`optimize_png.py`](../curation_docs/README.md) of the curation app screenshots. Set `PKDB_WEBSITE_SCREENSHOTS` to a folder to write the images there instead. Look at every image before you commit it.
