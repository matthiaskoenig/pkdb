# Study format 2 cutover

The cutover converts every study folder of pkdb_data from study format 1 to study format 2 with `pkdb migrate`. Each study is converted from the entities that the format 1 parser resolved and is checked by an equivalence gate against that parser. Only studies whose data is identical, or differs only by intended changes, replace their format 1 folder. Run the cutover after the pkdb_data tooling (pre-commit, CI and the issue sync workflow) exists. The command needs Linux or macOS.

## State on 2026-10-15

pkdb 0.12.7 on PyPI has every command of the cutover (`pkdb migrate`, `pkdb check`, `pkdb issues sync`, `pkdb new`, `pkdb move`, `pkdb release`, `pkdb registry`, `pkdb curate`, `pkdb review assign`), the fixes found during the cutover (#890 to #901), the curation app for the converted studies (#906 to #912, #920, #923 to #928, #943 to #953), the counts of the format 1 tables (#955), the vocabulary terms that the format 1 studies need (#969), the converter fixes for single-row array outputs and dose units with a factor (#968) and the refusal of migrations that would drop numbers that `study.json` does not map (`unmapped_value`, #983). pkdb_data pins it in `requirements/pkdb.txt` (pkdb_data#2644); `vocabulary.lock.json` is the vocabulary bundled with 0.12.6 and 0.12.7 (pkdb_data#2507). `main` of pkdb_data tracks its release [2.0.0](https://github.com/matthiaskoenig/pkdb_data/releases/tag/2.0.0) (pkdb_data#2493), the first release in study format 2. pkdb_data `develop` has the format 2 tooling (#2175: `pkdb check` in pre-commit and the required `studies` workflow, the `issues` and `vocabulary` workflows, `AGENTS.md`, the Claude skill, the pins), the format 1 fixes before the first run (#2176 to #2189) and the cutover with its follow-ups.

The first run is [pkdb_data#2190](https://github.com/matthiaskoenig/pkdb_data/pull/2190), with pkdb `develop` at 6b157fae; `v1-final` tags the last state of `develop` before it. Of 1576 studies, 303 `identical` and 546 `intended` went to format 2 (849), and 184 folders without `study.json` moved to `papers/`; two of them, the dulaglutide baseline analysis and the chlorzoxazone assays, are no papers and moved to pkdb_models ([pkdb_models#161](https://github.com/matthiaskoenig/pkdb_models/pull/161)). `docs/curation_guide.md` of pkdb_data is the format 2 guide since then, the format 1 guide is archived as `docs/curation-guide-format-1.md`, and `dulaglutide/Teraruchi2014` is renamed to `Terauchi2014` (pkdb_data#2191). Every format 2 study got its GitHub issue (pkdb_data#2485: 557 adopted existing issues, 292 are new); mkoenig is a reviewer (pkdb_data#2486) and a curator (pkdb_data#2488) of every format 2 study and an assignee of every study issue; every issue is labeled with the substance of its folder, every other substance that the study names, and the review status. The 349 issues that did not belong to a study were closed as not planned.

The second run on 2026-10-14 followed fixes of the format 1 studies by group, each a pull request of pkdb_data:

- The papers without curation data left `papers/` (#2498: 153 folders with only a PDF or a PDF and images).
- Stubs left `studies/` for `papers/`: 72 studies whose `study.json` defines no group or individual, with their digitized workbooks (#2500; `acetaminophen/Chiou1974` with an empty workbook was removed), and 14 studies whose `study.json` was copied from another study or an unadapted template (#2505); `glucose/Kerkshoffs1998` is renamed to `Kerckhoffs1998`.
- Metadata of `study.json` (#2501), images of the sources (#2502), the structure of study.json and workbooks (#2503) and duplicate rows and subjects (#2504).
- Abstinence and fasting rows without a value get the duration from the paper as `min` with a time unit, or are commented out when the paper gives none; repeated times of a series are fixed when the paper settles them; vocabulary gaps are mapped to existing terms or use the terms of pkdb#969 (#2506).
- The run itself (pkdb_data#2508, pkdb 0.12.6) wrote 367 studies (72 `identical`, 295 `intended`); 19 of them were first put back because they would have dropped numbers in columns that `study.json` did not map, and were converted again with the missing mappings. Their issues are adopted or created (pkdb_data#2641: 235 adopted, 132 new; seven issues with other titles were renamed first).

The same loss of unmapped numbers had happened in 68 studies of the first run and in 3 edoxaban studies of the second, which the check before its commit missed: they lacked tmax medians and ranges, CVs, geometric means or the values of a `value` column. pkdb_data#2642 and #2643 restored them in 68 studies (more than 500 rows or values, checked against the PDFs); `lisinopril/vanSchaik1988`, `omeprazole/Pounder1986` and `rapamycin/BasaDenes2019` need new digitizing instead. pkdb 0.12.7 refuses such migrations (`unmapped_value`).

Later fixes by group, each a pull request of pkdb_data that fixes the format 1 studies, runs `pkdb migrate` on them and gives the converted ones their issues with `pkdb issues sync --adopt`:

- 25 `mismatch` studies with mechanical fixes (pkdb_data#2649), and 8 studies that kept the diabetes duration in the numbers of their `disease` choice row, which now go to the measurement `disease duration` of pkdb 0.12.8 (pkdb_data#2653, pin #2650). The points that need a curator are open review items (pkdb_data#2654).
- pkdb 0.12.9 (pin pkdb_data#2657) adds the vocabulary terms that more studies need (#990) and refuses to drop a row when any unmapped column holds a number (#991). Its audit found values that earlier runs had lost in 15 converted studies; pkdb_data#2655 restored them, and pkdb_data#2656 put confidence limits, quartiles and ratios that format 2 has no column for into the row comments.
- 61 studies fixed, 47 of them converted (pkdb_data#2658, issues #2677: 29 adopted, 18 new): names with commas or repeated names, schema errors of `study.json`, groups of one with subgroups, unmapped columns, reversed ranges, digitizing noise below zero and scatter dimensions that the format 1 reader did not split.
- 45 studies fixed, 40 of them converted (pkdb_data#2678, issues #2687: 32 adopted, 8 new): choice rows with numeric statistics, single subjects with their value outside `mean`, missing units and broken formulas, and single defects of structure. Geometric means and CVs are mapped to `gmean`, `gcv` and `cv`: format 1 reads `cv` and `gcv` as fractions and the converter writes percent, so a curated percent converts 100 times too large. Converted studies with a mapped `cv` or `gcv` in percent are worth an audit. Sheets that `study.json` never references (`unreferenced_sheet`) are not carried into format 2; they stay in the history.

`pkdb check` of pkdb_data `develop` with the pinned 0.12.9: 1338 format 2 studies, 0 errors, 4666 warnings; 151 studies stay format 1. A dry run of these by their largest groups, all format 1 data defects for curators:

| Class | Largest groups (studies) |
| --- | --- |
| `mismatch` (64) | `duplicate_row` 36 (arms, days or scatter points that the mapping does not tell apart), `missing_value` 24, `unmapped_value` 5 (map the columns in `study.json`), `choice_statistics` 4 (a choice row with numeric statistics, some need vocabulary such as a smoking amount in g/day) |
| `invalid_v1` (68) | `timecourse_points` 36 (repeated times that the paper does not settle: digitize again), `missing_time` 6, `unknown_column` 6, `missing_time_unit` 5, `negative_value` 4 (values that can be negative, such as a decremental AUC or an arterio-venous difference, need vocabulary), `pk_zero_curve` 3 (curves that are all zero in the paper) |
| `not_converted` (18) | `missing_image` 8 (data from a supplement or text that the folder lacks), `scatter_pairs` 6, `scatter_statistics` 2 |

`glucose/LicinioPaixao1986` would convert as `identical` but stays format 1: it has no interventions and no outputset, so its digitized Fig1 would be lost. The report of the second run, `migration.json` and `migration.md`, lies uncommitted in the root of the pkdb_data checkout of mkoenig; later runs wrote their reports elsewhere.

Known open items: the models of pkdb_models that read the hidden format 1 tables from a pkdb_data checkout (`DATA_PATH_BASE` pointing to `pkdb_data/studies`) no longer find them for the converted studies; the models on `develop` of pkdb_models read their own copies in `data/`. The curator roster names a GitHub login for every curator except `dimitra`, `Ahmed-fub` and `lisapolzer`; former curators of student groups are no collaborators of pkdb_data, so their studies' issues lack them as assignees.

Open settings of pkdb_data, for a maintainer: apply the rulesets with `.github/rulesets/apply.sh` (makes `studies` a required check), set the secret `PKDB_API_KEY` and the variable `PKDB_ENDPOINT` (until then the `issues` and `vocabulary` workflows are skipped), and allow GitHub Actions to create pull requests. `vocabulary.lock.json` is still the vocabulary bundled with pkdb; the `vocabulary` workflow refreshes it from `PKDB_ENDPOINT`. Dependabot cannot update pkdb_data (`Dependabot::OutOfDisk`: it clones the whole repository), so bump `requirements/pkdb.txt` by hand as `docs/development.md` of pkdb_data describes.

The cutover can be partial: merge the studies that convert, curate them in study format 2 at once, and convert the others later. The tooling handles a repository with both formats (`pkdb check` and the curation app skip format 1 folders), a later `pkdb migrate` converts only the folders still in format 1, and the identifier registry stays until every identifier belongs to a format 2 study. Curation of format 1 studies then continues only to make them convert.

## Prepare a machine

1. Clone pkdb and pkdb_data. In pkdb, on `develop`, start the local server and create the administrator as [Local setup and development](installation.md) describes (`docker compose --profile dev up --build --wait`); an existing database volume is kept and migrated at startup. Sign in at <http://localhost:8080> and create a personal API key.
2. Install pkdb: the release pinned by pkdb_data with `uv tool install --python 3.14 --force pkdb --with-requirements requirements/pkdb.txt` from the pkdb_data checkout, or the newer `develop` from the pkdb checkout with `uv tool install --python 3.14 --force --editable ./python`.
3. Set the environment: `PKDB_ENDPOINT=http://localhost:18083`, `PKDB_USER` and `PKDB_API_KEY` of your local account, `PKDB_NO_UPDATE=1`, and `GH_TOKEN` (for example `gh auth token`) for `pkdb new`, `pkdb move` and `pkdb issues sync`.
4. In pkdb_data, install the hooks with `uvx pre-commit install` and work on branches of `develop`.

## Next steps

1. Curate the converted studies with `pkdb curate` ([Local curation app](local-curation.md)), one branch and pull request per study.
2. Fix the format 1 studies by the groups above and rerun `pkdb migrate` until it exits with 0; then give the newly converted studies their issues with `pkdb issues sync --adopt`. Before a run is committed, read the Manual decisions of `migration.md`, in particular the dropped rows without any value.
3. When beta.pk-db.com is deployed again, set `PKDB_API_KEY` and `PKDB_ENDPOINT` of pkdb_data (see the open settings above), so that the `issues` workflow keeps the issues in step every night, re-upload the studies to staging and compare them with production (see [After the merge](#after-the-merge)).

## Before the run

Fix unreadable `study.json` files and the studies that are invalid in format 1 by normal pull requests. Merge or pause open curation pull requests, because they are written against format 1.

## Convert

Work on a branch of pkdb_data. Only one `pkdb migrate` runs per checkout, because it locks the repository root. Add `.pkdb-migrate/` to the `.gitignore` of pkdb_data.

```bash
pkdb migrate studies --approver <maintainer> --dry-run
```

The command reads the identifier registry `studies/study_identifiers.json`, so it needs `--approver`, the maintainer who approves the released studies. It writes the report `migration.json` and `migration.md` to the current folder, or to the JSON file named by `--report` and the Markdown file next to it. Run every command from the same folder and keep `migration.json` between runs: each run reads the report of the earlier runs and keeps the studies they wrote, so `migration.md` covers the whole cutover. A run that stops early, by Ctrl-C or a failed swap, still writes the report, and `migration.md` then says "Interrupted." first. The report names the vocabulary of the run, because the conversion depends on it. Like `pkdb check`, the command uses the vocabulary of `--vocabulary`, else `vocabulary.lock.json` of the checkout, else the one bundled with pkdb, so pkdb_data CI checks the converted studies with the vocabulary that converted them. Use the same vocabulary for every run of the cutover, as the report warns as long as it holds studies written with another one.

Read `migration.md`, fix the format 1 studies or report converter bugs, and run again. The tables under Manual decisions say for each study whether it was written.

Before the first run without `--dry-run`, reconcile the registry with the dry-run report. A study whose `study.json` has a PKDB identifier as `sid` is only converted when the registry gives that identifier to its folder; the others are `not_converted` with `registry_sid` and are listed under "Identifiers that differ from the registry". Fix these, the studies with two PKDB identifiers (`double_identifier`) and the "Registry paths that do not exist" in the registry or in the studies, and run the dry run again.

When the dry run looks right, run the command without `--dry-run`. Stage the whole result before you commit it (`git add -A studies papers .gitignore`): pre-commit stashes unstaged changes as one patch and cannot apply a patch of more than 1 GB again, so a commit with unstaged changes of the migration fails and leaves the checkout half restored; then reset the checkout to the last commit, remove the untracked files of the run and run the migration again. Repeat until `pkdb migrate` exits with 0, which means no study is `mismatch`, `invalid_v1` or `not_converted`. Each run converts only the studies that pass, so reruns are safe. A dry run writes only the report.

The run after which every identifier of the registry belongs to a format 2 study deletes `studies/study_identifiers.json`, and its `migration.md` says "Registry file deleted." under Manual decisions. Commit the deletion with the converted studies.

An interrupted run leaves `.pkdb-migrate/` at the repository root. The next real run finishes or undoes each interrupted swap, and a dry run refuses until that real run happened.

| Class | Result | What to do |
| --- | --- | --- |
| `identical` | Replaces the format 1 folder | Nothing. |
| `intended` | Replaces the format 1 folder | Check the listed changes and the manual decisions. |
| `mismatch` | Stays format 1 | Fix the format 1 study, see below, and rerun. |
| `invalid_v1` | Stays format 1 | The format 1 parser refuses the study. Fix it in format 1, see below. |
| `not_converted` | Stays format 1 | Fix the reason, see below, and rerun. |

The report lists the issue codes of an `invalid_v1` study. `pkdb validate --offline studies/<substance>/<name>` shows each error with its place in `study.json` or the workbook; like other format 1 tools, it may rewrite the hidden `.tsv` files of the workbook.

A `mismatch` mostly means that the converted study fails format 2 validation because of format 1 data defects that format 2 refuses: records with a statistic, such as an sd, but without a central value (mean, gmean, median, min or max), timecourse rows without time, repeated rows, choice rows without numeric statistics, and a group of one that is the parent of other subjects. The report lists the format 2 error codes and messages per study. Each message names the converted table and line with the identifying cells of that row, for example `validation characteristica.tsv:16 missing_value [subjects=S2 measurement=age]`; find the format 1 row by these cells. Other mismatches are differences between the format 1 data and the converted data, comments included, for example an `sd` or `se` cell `ABS(X - mean)` whose value saved in the workbook is stale: recalculate the workbook in a spreadsheet application and save it.

A row without any value whose format 1 row holds a number in a column that `study.json` does not map is a `mismatch` with the issue code `unmapped_value`, so that the converter never drops numbers unseen: typically the `median`, `min` and `max` of a tmax row in a table whose template maps only `mean` and `sd`, a `cv` or `geomean` column, confidence limits or quartiles, or a `value` column where the template maps `mean`. Every column can hold a value of the row, in any case, except `count`, `n`, `group_count`, `groupcount`, `time`, `time_end`, `time_raw`, `timeraw`, `study`, `group`, `individual`, `subject`, `name`, `id`, `label` and the columns whose name contains `comment` or `note`; a column that the template of another record of the same row maps, text such as `NR` and anything after a `#` in the row are no values of the row either. Until pkdb 0.12.8 the check knew only the statistic columns `value`, `mean`, `median`, `min`, `max`, `sd`, `se`, `cv`, `gmean`, `gsd`, `gcv` and `mean_pm`, and dropped rows whose numbers were in columns such as `geomean`, `geometric_mean`, `ci_low` or `q25`. Each difference names the table that the row would be in, the format 1 file, sheet and row, the subject and measurement, and the columns with their numbers, for example `unmapped_value outputs_Tab2.tsv: Bashir2018.xlsx Tab2 row 3, subject all, cmax, substance apixaban, tissue plasma` with `min 147, max 219`. Map the columns in `study.json`, or remove a number that is no value of the row, and rerun. The check reads each characteristic from its own row of the sheet: the format 1 parser located every characteristic of a group that spans several rows at the first of them.

Three format 1 gaps need no fix, because the converter writes them as intended changes: a characteristic of a measurement that needs a time, such as a concentration, gets time `NR`, because format 1 characteristica have no time (`time_not_reported`), a characteristic, output or timecourse point without any value, that is without a choice and without any statistic, is dropped (`valueless_row`) unless its format 1 row holds a number that `study.json` does not map (`unmapped_value`, see above), and an output or timecourse point of a group takes the count of the `count` column of its format 1 table when that count differs from the count of the group (`table_count`). No format 1 template maps `count`, because the format 1 server counted every output with its group, but curators kept the number of subjects of a row in that column and the formulas of their workbooks derive an sd or se from it. A count above the count of the group, such as the count of `all` copied into the rows of a subgroup, is not written and is listed under Manual decisions, and so is a count that is no whole number; the rows of an individual keep the count 1, and a scatter point has no count in format 2. Rows with only a count or an error type, with a spread but no central value, and rows of `abstinence ...` and `fasting (duration)`, whose existence is the information, are not dropped and need a curator, and so does a repeated row with data. A timecourse that keeps only one point after the drop fails as `timecourse_points` (for example apixaban/Raghavan2009) and needs curation too. Text cells are written on one line, so runs of whitespace become one space and blank cells become empty (`whitespace`).

What to do for each `not_converted` reason:

| Reason | Fix |
| --- | --- |
| `missing_image` | A table or figure source of outputs, timecourses or scatters needs `<study>_<source>.png`. |
| `image_type` | The image of a source is neither PNG nor JPG. Convert it to `<study>_<source>.png`. |
| `image_unreadable` | A PNG or JPG image cannot be read or is corrupt; every image is decoded completely before it is copied. Replace it with a readable PNG or JPG. |
| `image_write` | An image could not be written to the work folder, such as on a full disk. The source image is fine; fix the disk and run again. |
| `image_conflict` | Two image files exist for one source, such as a PNG and a JPG. Keep one. |
| `sheet_name`, `image_name` | Rename to the source pattern `Tab...` or `Fig...`. |
| `subject_name` | Remove `,` `;` tabs and line breaks from names, and give a group and an individual different names. |
| `label_name` | A timecourse label whose `,` `;` tabs and line breaks become `_` would equal another label. Rename one of them. |
| `scatter_*` | For example `scatter_name`: two scatters with one subset name in different datasets, as in the caffeine studies Wood1979 and Roberts1976. Rename the subset. |
| `registry_sid` | The `sid` of `study.json` is a PKDB identifier that the registry does not give to this folder. Fix the registry or the `sid`, see above. |
| `double_identifier` | Fix the identifier registry. |
| `no_subjects`, `metadata`, `reference` | Fix the study as named in the message. |
| `format` | Format 2 refuses the written folder for the reason in the message. Fix the format 1 study when the message names its data, otherwise report a converter bug. |
| `unreadable` | The format 1 parser refuses the folder, usually `invalid_v1`. |
| `papers_exists` | A folder without `study.json` moves to `papers/`, where a folder of that name exists. Merge the two folders by hand. |
| `swap` | The converted folder could not replace the format 1 folder, which is unchanged. Fix the file system problem named in the message and rerun. |
| `converter_error` | The converter failed or its worker process stopped. Rerun, and report a converter bug when it fails again. |

A study without `reference.json` is resolved on a copy by the reference resolver, which needs the network. The original format 1 folder is not written. Check the section Manual decisions in `migration.md`: dropped rows without any value, one line per study, table and format 1 file with the row ranges, for the studies that are written (a dropped row can be the symptom of another defect, such as `||` lists of different order in `study.json`; `migration.json` lists every dropped row with its comment), replaced reference snapshots (the PubMed ID of `study.json` wins over a `reference.json` of another publication), unreleased public studies written as private, studies without a creator (the approver, or `pkdb` without one, becomes the creator), renamed timecourse labels, dropped output labels (also of array outputs that form no timecourse series, such as correlation data of many subjects or a label with a single row, as in tirzepatide/Urva2021), converted JPG images (turned upright by their EXIF orientation, with their ICC profile kept in the PNG; an image of another format named `.png` is converted the same way), dropped data files (for example WebPlotDigitizer `.json` projects not named `.wpd.json`), groups of one turned into individuals, and counts of the format 1 tables that were not written because they exceed the count of the group or are no whole number.

## Review and merge

Tag `v1-final` on `develop` before the merge. In the migration pull request (pkdb_data#2190 has these changes), add `studies/**/*.xlsx` to `.gitignore` (format 2 workbooks are generated), archive the format 1 guide as `docs/curation-guide-format-1.md` first, then rename `docs/curation-v2.md` to `docs/curation_guide.md`, update the navigation in `zensical.toml`, update every link to `curation-v2.md` (today in `AGENTS.md`, `CLAUDE.md`, `docs/development.md`, `docs/installation.md`; find them with `git grep -n curation-v2`), remove the "applies after the cutover" note at the top of the guide, and revisit the install and update instructions in `docs/installation.md` of pkdb_data (they still say `uv tool upgrade pkdb`): after the cutover they must install the pinned pkdb with `uv tool install --python 3.14 --force pkdb --with-requirements requirements/pkdb.txt`, like the format 2 guide. Review through `migration.md` (summary and manual decisions) and spot checks of converted studies. Merge one pull request with green CI.

## After the merge

Give every study its GitHub issue on a branch of pkdb_data while curation is still paused. `pkdb issues sync` reads the GitHub logins from the PK-DB roster, so set `PKDB_ENDPOINT` and `PKDB_API_KEY`; set `GH_TOKEN` to a token that may write the issues of pkdb_data, which is private, so the dry run needs it too; and name the PK-DB user of the adoption with `--user` or `PKDB_USER`.

```bash
export PKDB_ENDPOINT=https://beta.pk-db.com PKDB_API_KEY=<key> GH_TOKEN=<token>
pkdb issues sync --adopt --user <maintainer> --dry-run
```

The local server of [Local setup and development](installation.md) serves the roster too: set `PKDB_ENDPOINT=http://localhost:18083` (the API; the frontend runs on <http://localhost:8080>) and the API key of a local administrator, after the user roster with the GitHub logins was imported. Its roster must name every curator and reviewer of the studies with their GitHub login, otherwise the dry run reports `User ... is not in the PK-DB roster` or `has no GitHub login`.

Compare the number of new issues in the dry run (`create N issues` in the summary, the adoptions with `created` in `--format json`) with the number of studies: a large count means that the titles of the existing issues do not follow `<substance>/<name>`. Rename the issues named in the warnings about similar titles. Then run the command without `--dry-run`; it prints each adoption and change as it goes, and a rerun finishes a stopped run. A study that names the same issue as a study that cannot be read gets an error and no change: fix the unreadable study and run the command again. A warning `created #N although issue #M has a similar title` names an issue that the run did not adopt; close it if it duplicates the new issue. Commit the changed `study.json` and `review.json` files and merge them through a pull request.

Re-upload all studies with processing version 9 to staging and compare counts and API output with production. Delete the format 1 code once no format 1 branch is open.

## Papers

Folders without `study.json` move to `papers/<substance>/<name>/`. `pkdb new <substance>/<name>` takes the PDF `<name>.pdf` and the images `<name>_<source>.png`, with a source such as `Tab1`, `Fig2A` or `Text`, from there into the new study. Other files, such as a study format 1 workbook `<name>.xlsx`, stay in the paper folder and are listed in the output; a file whose name differs from these names only in case, such as `<name>.PDF`, also stays and is named with the expected name. An emptied paper folder and an emptied substance folder below `papers/` are removed.
