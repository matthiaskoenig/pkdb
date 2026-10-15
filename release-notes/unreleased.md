# Unreleased

- The web interface guide describes the Studies page and the study page with what each reader sees, and the local curation guide notes that the website shows a study with the same views; all screenshots of both guides are rendered again, the website ones with the new `tools/website_docs/run.sh` on the disposable website of the browser tests.

- The website lists the study format 2 studies on a new Studies page, with the search and the Substance and Curator filters of the local curation app under the website's own heading, and shows a study at `/data/<substance>/<name>` with the views of the curation app, in its compact sizes: Metadata and Data for everyone, and for who may write the study also Problems, Review, the issue, the review status, the PDF and the figure images and raw tables. The page follows the session, keeps the data search that opened it in its address, and studies without a stored view, such as study format 1 studies and study format 2 studies uploaded before this release, keep the record page (#963).

- A browser that still holds the cookie of an ended session (expired, revoked or signed out elsewhere) no longer makes the website read again without end: the first read deletes the cookie and the reader continues as a visitor.

- The website now declares the order of Vuetify's style layers before any stylesheet loads, so buttons on every page show Vuetify's size and weight instead of the size of the text around them.
