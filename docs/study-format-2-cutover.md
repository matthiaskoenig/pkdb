# Study format 2 cutover

The cutover converts every study folder of pkdb_data from study format 1 to study format 2 with `pkdb migrate`. Each study is converted from the entities that the format 1 parser resolved and is checked by an equivalence gate against that parser. Only studies whose data is identical, or differs only by intended changes, replace their format 1 folder. Run the cutover after the pkdb_data tooling (pre-commit, CI and the issue sync workflow) exists. The command needs Linux or macOS.

## Before the run

Fix the 20 invalid `study.json` files and the studies that are invalid in format 1 by normal pull requests. Merge or pause open curation pull requests, because they are written against format 1.

## Convert

Work on a branch of pkdb_data. Only one `pkdb migrate` runs per checkout, because it locks the repository root. Add `.pkdb-migrate/` to the `.gitignore` of pkdb_data.

```bash
pkdb migrate studies --approver <maintainer> --dry-run
```

The command reads the identifier registry `studies/study_identifiers.json`, so it needs `--approver`, the maintainer who approves the released studies. It writes the report `migration.json` and `migration.md` to the current folder, or to the JSON file named by `--report` and the Markdown file next to it. Run every command from the same folder and keep `migration.json` between runs: each run reads the report of the earlier runs and keeps the studies they wrote, so `migration.md` covers the whole cutover. A run that stops early, by Ctrl-C or a failed swap, still writes the report, and `migration.md` then says "Interrupted." first. The report names the vocabulary of the run, because the conversion depends on it. Like `pkdb check`, the command uses the vocabulary of `--vocabulary`, else `vocabulary.lock.json` of the checkout, else the one bundled with pkdb, so pkdb_data CI checks the converted studies with the vocabulary that converted them. Use the same vocabulary for every run of the cutover, as the report warns as long as it holds studies written with another one.

Read `migration.md`, fix the format 1 studies or report converter bugs, and run again. The tables under Manual decisions say for each study whether it was written.

Before the first run without `--dry-run`, reconcile the registry with the dry-run report. A study whose `study.json` has a PKDB identifier as `sid` is only converted when the registry gives that identifier to its folder; the others are `not_converted` with `registry_sid` and are listed under "Identifiers that differ from the registry". Fix these, the studies with two PKDB identifiers (`double_identifier`) and the "Registry paths that do not exist" in the registry or in the studies, and run the dry run again.

When the dry run looks right, run the command without `--dry-run`. Repeat until `pkdb migrate` exits with 0, which means no study is `mismatch`, `invalid_v1` or `not_converted`. Each run converts only the studies that pass, so reruns are safe. A dry run writes only the report.

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

A `mismatch` mostly means that the converted study fails format 2 validation because of format 1 data defects that format 2 refuses: records with a statistic, such as an sd, but without a central value (mean, gmean, median, min or max), timecourse rows without time, repeated rows, choice rows without numeric statistics, and a group of one that is the parent of other subjects. The report lists the format 2 error codes and messages per study. Each message names the converted table and line with the identifying cells of that row, for example `validation characteristica.tsv:17 missing_value [subjects=S2 measurement=age]`; find the format 1 row by these cells. Other mismatches are differences between the format 1 data and the converted data, comments included, for example an `sd` or `se` cell `ABS(X - mean)` whose value saved in the workbook is stale: recalculate the workbook in a spreadsheet application and save it.

Two format 1 gaps need no fix, because the converter writes them as intended changes: a characteristic of a measurement that needs a time, such as a concentration, gets time `NR`, because format 1 characteristica have no time (`time_not_reported`), and a characteristic, output or timecourse point without any value, that is without a choice and without any statistic, is dropped (`valueless_row`). Rows with only a count or an error type, with a spread but no central value, and rows of `abstinence ...` and `fasting (duration)`, whose existence is the information, are not dropped and need a curator, and so does a repeated row with data. A timecourse that keeps only one point after the drop fails as `timecourse_points` (for example apixaban/Raghavan2009) and needs curation too. Text cells are written on one line, so runs of whitespace become one space and blank cells become empty (`whitespace`).

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
| `study_json` | A list of `study.json` is malformed, such as a curator that is not a name or a `[user, rating]` pair; the message names the field. |
| `no_subjects`, `metadata`, `reference` | Fix the study as named in the message. |
| `format` | Format 2 refuses the written folder for the reason in the message. Fix the format 1 study when the message names its data, otherwise report a converter bug. |
| `unreadable` | The format 1 parser refuses the folder, usually `invalid_v1`. |
| `papers_exists` | A folder without `study.json` moves to `papers/`, where a folder of that name exists. Merge the two folders by hand. |
| `swap` | The converted folder could not replace the format 1 folder, which is unchanged. Fix the file system problem named in the message and rerun. |
| `converter_error` | The converter failed or its worker process stopped. Rerun, and report a converter bug when it fails again. |

A study without `reference.json` is resolved on a copy by the reference resolver, which needs the network. The original format 1 folder is not written. Check the section Manual decisions in `migration.md`: dropped rows without any value, one line per study, table and format 1 file with the row ranges, for the studies that are written (a dropped row can be the symptom of another defect, such as `||` lists of different order in `study.json`; `migration.json` lists every dropped row with its comment), replaced reference snapshots (the PubMed ID of `study.json` wins over a `reference.json` of another publication), unreleased public studies written as private, studies without a creator (the approver, or `pkdb` without one, becomes the creator), renamed timecourse labels, dropped output labels (also of array outputs that form no timecourse series, such as correlation data of many subjects), converted JPG images (turned upright by their EXIF orientation, with their ICC profile kept in the PNG), dropped data files (for example WebPlotDigitizer `.json` projects not named `.wpd.json`) and groups of one turned into individuals.

## Review and merge

Tag `v1-final` on `develop` before the merge. In the migration pull request, add `studies/**/*.xlsx` to `.gitignore` (format 2 workbooks are generated), archive the format 1 guide as `docs/curation-guide-format-1.md` first, then rename `docs/curation-v2.md` to `docs/curation_guide.md`, update the navigation in `zensical.toml`, update every link to `curation-v2.md` (today in `AGENTS.md`, `CLAUDE.md`, `docs/development.md`, `docs/installation.md`; find them with `git grep -n curation-v2`), remove the "applies after the cutover" note at the top of the guide, and revisit the install and update instructions in `docs/installation.md` of pkdb_data (they still say `uv tool upgrade pkdb`): after the cutover they must install the pinned pkdb with `uv tool install --python 3.14 --force pkdb --with-requirements requirements/pkdb.txt`, like the format 2 guide. Review through `migration.md` (summary and manual decisions) and spot checks of converted studies. Merge one pull request with green CI.

## After the merge

Give every study its GitHub issue on a branch of pkdb_data while curation is still paused. `pkdb issues sync` reads the GitHub logins from the PK-DB roster, so set `PKDB_ENDPOINT` and `PKDB_API_KEY`; set `GH_TOKEN` to a token that may write the issues of pkdb_data, which is private, so the dry run needs it too; and name the PK-DB user of the adoption with `--user` or `PKDB_USER`.

```bash
export PKDB_ENDPOINT=https://beta.pk-db.com PKDB_API_KEY=<key> GH_TOKEN=<token>
pkdb issues sync --adopt --user <maintainer> --dry-run
```

Compare the number of new issues in the dry run (`create N issues` in the summary, the adoptions with `created` in `--format json`) with the number of studies: a large count means that the titles of the existing issues do not follow `<substance>/<name>`. Rename the issues named in the warnings about similar titles. Then run the command without `--dry-run`; it prints each adoption and change as it goes, and a rerun finishes a stopped run. Commit the changed `study.json` and `review.json` files and merge them through a pull request.

Re-upload all studies with processing version 9 to staging and compare counts and API output with production. Delete the format 1 code once no format 1 branch is open.

## Papers

Folders without `study.json` move to `papers/<substance>/<name>/`. `pkdb new <substance>/<name>` takes the PDF `<name>.pdf` and the images `<name>_<source>.png`, with a source such as `Tab1`, `Fig2A` or `Text`, from there into the new study. Other files, such as a study format 1 workbook `<name>.xlsx`, stay in the paper folder and are listed in the output; a file whose name differs from these names only in case, such as `<name>.PDF`, also stays and is named with the expected name. An emptied paper folder and an emptied substance folder below `papers/` are removed.
