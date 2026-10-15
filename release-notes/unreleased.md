# Unreleased

- The web interface guide describes the Studies page and the study page with what each reader sees, and the local curation guide notes that the website shows a study with the same views; all screenshots of both guides are rendered again, the website ones with the new `tools/website_docs/run.sh` on the disposable website of the browser tests.
- A concentration timecourse that is all zero, such as the concentrations of a placebo or below the limit of quantification, has no PK parameters, where before its study failed with `pk_zero_curve`. Three format 1 studies of pkdb_data that the conversion refused for it now convert.
