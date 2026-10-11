# Unreleased

- The client gives an idle connection to PK-DB up after two seconds instead of five (#905). uvicorn closes a connection after five idle seconds, so a write sent on a connection that it closed at that moment got no answer, ended as `unreachable` with an unknown outcome and stopped the batch; this happened once in an upload of all pkdb_data studies with eight jobs.

- `pkdb upload` of a parent folder uploads the other studies when some of them share a study identifier or a publication and source (#904). Before, one such pair, such as two pkdb_data folders whose `study.json` names the same PubMed ID, stopped the whole batch with `Multiple studies claim reference ...` before any upload; now each study of the pair fails with `identity_conflict` and names the others, because PK-DB keeps one study per publication and source and the order of the uploads would decide which one.

- `pkdb curate` without the built app names the folder where it looked and the source checkout that runs. Before, it only said `The curation app is not built. Run npm ci and npm run build:curation in frontend/.`, so a user with an installed release and an active virtual environment of a pkdb checkout could not tell that the checkout ran instead of the release. The guide of the local curation app no longer says that `pkdb curate` is missing from the releases; it is part of `pkdb` since 0.12.1.

- The Tables section of the local curation app hides the empty columns when it opens, because most tables leave many of their fixed columns empty. The switch **Hide empty columns** shows them again.

- The overview of the local curation app filters the studies by curator. **Curator** lists every curator of the workspace with the number of their studies, and **Me**, the PK-DB user of the app, first, so a curator sees their own studies. The filters and the sort order of the overview stay when a study is opened and the overview is shown again; before, every visit of a study reset them.

- The overview of the local curation app shows the names and pictures of the curators after a launch URL was pasted into an open overview without a session. Before, it kept their initials and the Curator filter their user names until the page was reloaded, because it loaded the curator roster only when it opened.

- The search and the selects of the overview stay in place when the counts of the status chips change. Before, the search field took the width that the chips left, so it grew or shrank by a few pixels with each filter, and a second line of chips moved every field down.
