# Edit tables in a workbook

A [study format 2](study-format.md) folder keeps its data in tab-separated tables, and these tables are the files you commit. To edit them in Excel or LibreOffice Calc, `pkdb tables` generates a workbook `<name>.xlsx` in the study folder and keeps it in step with the tables: a sync writes your workbook edits to the tables and updates the workbook with changes of the tables, for example after a `git pull`. The workbook is a generated editing aid that git ignores. The tables are the study.

## Workflow

```bash
pkdb tables open studies/caffeine/Harder1988
```

`open` syncs the study, creates `Harder1988/Harder1988.xlsx` when it does not exist, and opens it in the default application for `.xlsx` files. Use `--no-open` to only sync. Edit the sheets and save the workbook. The sync reads the saved file, so changes that you have not saved are not seen. Then write your edits to the tables, check them, and commit the tables:

```bash
pkdb tables sync studies/caffeine/Harder1988
pkdb validate studies/caffeine/Harder1988 --offline
git add studies/caffeine/Harder1988
git commit
```

The sync lists the tables it wrote or removed and what it did with the workbook. The tables are written in canonical form, as `pkdb format` does. Run the sync again whenever the tables may have changed, for example after `git pull`, and the workbook is updated. A folder that contains study folders syncs every study format 2 study below it and creates the missing workbooks; study format 1 folders are left unchanged.

```text
caffeine/Harder1988: synced
  wrote outputs_Tab2.tsv
  Harder1988.xlsx: unchanged
```

On a terminal the output is readable text. Elsewhere, or with `--format json`, it is one JSON line per study with `ok`, `workbook_action`, `changes`, `conflicts` and `issues`. The exit code is 0 when the sync succeeded and 1 when it found conflicts or errors. `pkdb tables sync --check` only reports what a sync would do, writes nothing, and exits with 1 when there is anything to do.

The dropdowns of the workbook list vocabulary terms. The tables commands never contact the server: they use the snapshot given with `--vocabulary`, otherwise the cached vocabulary of `--endpoint` (default `PKDB_ENDPOINT`), otherwise the vocabulary bundled with `pkdb`. The lists are written when the workbook is created or regenerated.

## Sheet layout

- One sheet per table, named like the file without `.tsv`: `subjects`, `interventions` and `characteristica`, followed by the `outputs_<source>`, `timecourses_<source>` and `scatters_<source>` sheets in natural order (`Tab2` before `Tab10`). A generated workbook always has the first three sheets, also without rows, and the `subjects` sheet cannot be removed. A table that has no rows is not a file, so deleting all rows of a sheet removes its TSV file.
- Row 1 holds the column headers, in bold, frozen, with filters. Each header has a comment with the description of the column, an example, and `Required` where the column is required. Do not change the headers.
- Columns that hold text are formatted as text, so that the spreadsheet application does not convert what you type, such as a date-like value, into a date. Number columns, such as `count`, `mean` and `sd`, keep the general format.
- Dropdowns suggest values. The reference columns (`subjects`, `interventions`, `parent` and the scatter `x_interventions` and `y_interventions`) list the live `name` column of the `subjects` and `interventions` sheets, so a new row shows up at once. The vocabulary columns (`measurement`, `calculation`, `substance`, `tissue`, `method`, `route`, `form`, `application` and their `x_` and `y_` variants) and `error_type` use lists on the hidden `_lists` sheet, and the list of measurements leaves out deprecated ones. Units have no dropdown. Dropdowns never block other input; `pkdb validate` checks the values.
- The hidden `_lists` sheet and the very hidden `_base` sheet belong to the workbook. `_base` stores the tables the workbook was generated from, which the sync needs to merge both sides. Do not edit them.
- A sheet whose name starts with `_` is a scratch sheet. It is never synced and is kept when the workbook is regenerated: values, formulas and basic formatting survive, charts and images may not. Any other sheet that is not a table is an error (`unknown_sheet`).

## Add a table

```bash
pkdb tables add studies/caffeine/Harder1988 outputs_Tab3
```

This syncs the study, then adds an empty sheet with the header of the table. The name is `<kind>_<source>` with the kind `outputs`, `timecourses` or `scatters` and a source that is `Text` or `Tab` or `Fig` followed by a label, such as `Tab3` or `Fig2A`, at most 31 characters, and not yet used by a file or a sheet, ignoring case. The TSV file appears when the sheet has a row and you sync. Validation needs an image `<study>_<source>.png` for every source except `Text`, and `add` warns when it is missing. It cannot add the sheet while the workbook is open; close it, or copy a sheet in the spreadsheet application and rename the copy to the table name. The sync checks the header of the new sheet, so keep the header row and replace the copied rows with your data.

## How the sync works

The sync compares three versions of each table: the base (the tables the workbook was generated from), the workbook and the tables.

| Situation | What the sync does |
| --- | --- |
| There is no workbook | Creates it from the tables. |
| The workbook and the tables are equal | Nothing, they are in sync. |
| Only the workbook changed | Writes the workbook content to the tables. The workbook itself is not rewritten, so its formatting and the formulas in its data sheets stay. |
| Only the tables changed, for example by a pull | Regenerates the workbook from the tables. A workbook that is open is not replaced; close it and sync again. |
| Both changed | Merges the tables line by line, as git does. A clean merge is written to the tables and the workbook is regenerated. Changes to the same or neighbouring rows that differ are conflicts. |

All files are written atomically. An error or an unresolved conflict found by the sync stops it before it writes anything, so the tables and the workbook stay as they were, and a sync never overwrites a workbook that holds changes that are not in the tables yet. The sync needs every table to load, but not the JSON files: problems of `study.json`, `review.json` and `reference.json` do not stop it, and `pkdb validate` reports them.

A workbook can lose its `_base` sheet, for example when another application saves it, and an invalid one counts as lost. The sync then warns (`workbook_base_missing` or `workbook_base_invalid`): it cannot tell which side changed a table, so a table that differs between the workbook and the tables conflicts as a whole. When the workbook and the tables are equal after the sync, it regenerates the closed workbook, which restores the base and keeps the scratch sheets; while the workbook is open, it reports `workbook_open`, and closing the workbook and syncing again restores the base. If the tables and the workbook differ, choose a side with `--keep workbook` or `--keep tables`, and the same sync restores the base.

Next to the workbook, the sync keeps a hidden state file `.Harder1988.xlsx.pkdb-base`. It records the base of every table that was written from the workbook since the workbook was generated, so saving the workbook twice while it stays open never conflicts with the first sync. A regeneration starts afresh and removes the file. Do not edit it. If it is lost, the sync falls back to the `_base` sheet, and rows that you edited again after an earlier sync can conflict.

## Conflicts

A conflict is reported per table with its sheet, the rows of the sheet and the lines of the TSV file, each with the version of the workbook and the version of the tables:

```text
caffeine/Harder1988: cannot sync, resolve the conflicts below
  Harder1988.xlsx: unchanged
  conflict in sheet timecourses_Fig1
    workbook row 2: label=drug_plasma, subjects=all, interventions=D1, measurement=concentration, substance=drug, tissue=plasma, time=0, time_unit=h, mean=0.25, unit=mg/l
    timecourses_Fig1.tsv line 2: label=drug_plasma, subjects=all, interventions=D1, measurement=concentration, substance=drug, tissue=plasma, time=0, time_unit=h, mean=0.75, unit=mg/l
  Harder1988.xlsx, sheet timecourses_Fig1, row 2: The workbook and the tables changed the same rows of timecourses_Fig1 differently since the last sync: row 2 of the sheet, line 2 of timecourses_Fig1.tsv [sync_conflict]
    Keep one side with pkdb tables sync --keep workbook or --keep tables, or edit the workbook so that the conflicting rows equal the tables.
```

Terminal output lists the first ten rows of each side. `--format json` lists all of them, with the base lines. An issue found in the workbook, such as a conflict or a converted cell, names the workbook, the sheet and the row or cell, in JSON as `source.file`, `source.sheet`, `source.row` and `source.cell`; an issue of a TSV file names the file and its line. Resolve a conflict in one of two ways:

- `pkdb tables sync --keep workbook` or `--keep tables` resolves the conflicting parts of every conflicting table to that side, and still merges all other changes. The sync names the kept side. The other version is discarded, so copy anything you need from the listing first.
- Edit the workbook so that the conflicting rows equal the version in the tables, save, and sync again. To end with a third value, sync first, then edit the row again.

## Open workbooks and lock files

A workbook that is open in a spreadsheet application is never replaced. Excel marks an open workbook with the lock file `~$Harder1988.xlsx` and LibreOffice with `.~lock.Harder1988.xlsx#`. The sync still writes your saved workbook edits to the tables, and when the tables hold something the workbook lacks, it reports the warning `workbook_open` and leaves the workbook as it is. Close the workbook and sync again to update it. An application that crashed can leave a stale lock file behind; if the workbook is not open, delete the lock file that the message names.

A sync never creates a workbook while its lock file exists, because Excel on Windows renames the workbook while it saves it, so that it is missing for a moment; it reports `workbook_open` instead.

A workbook that you save while a sync runs is not replaced either. The sync reports `workbook_changed` and the next sync merges that save.

## Formulas

A formula cell is stored as the value that the spreadsheet application saved with it, and every sync lists such cells as the warning `formula_value`. A formula that has no saved value is an error (`formula_without_value`), because the workbook was not saved by a spreadsheet application; open it in Excel or LibreOffice and save it. Tables hold the values of the publication, and derived statistics are calculated when the study is prepared, see [study format](study-format.md#statistics-and-schedules).

Formulas in data sheets stay while the workbook is only synced to the tables, but a regeneration builds the data sheets from the tables, so it replaces their formulas with their values. Put scratch calculations in a sheet whose name starts with `_`, which regeneration keeps with its formulas.

## Converted cells and numbers

When the spreadsheet application converted what you typed, the sync reports an error at the cell, with sheet, row and column, and writes nothing until you fix it.

| In the workbook | Error | Fix |
| --- | --- | --- |
| A date or a time | `cell_date` | Format the column as text and enter the value again. |
| A percentage; `20%` is stored as `0.2` | `cell_percent` | Enter `20`. |
| An error value such as `#DIV/0!`, also as the saved value of a formula | `cell_error` | Correct the formula or enter the value. |
| A line break or a tab inside a cell | `cell_line_break` | Remove it. |
| A value to the right of the last header column | `value_outside_table` | Move it into the table, or into a `_` sheet. |

Text that looks like an error value, such as `#N/A` in a text column, is text and is written to the tables as it is.

Numbers with more than 15 significant digits appear as text cells, because LibreOffice saves at most 15 significant digits. They are written back to the tables unchanged. Every other number is a number cell, so the tables come back unchanged from a round trip through the workbook.

The workbook file format stores some characters as escapes such as `_x0041_`, so a text that looks like one, such as `_x0041_` itself, is stored escaped and reads back unchanged. LibreOffice saves text in which two such escapes share an underscore, such as `_x005F_x0041_`, wrongly, and it reads back as `_x0041_`. The workbook generation warns about such a cell (`cell_escape_text`); edit it in the TSV file or in Excel. A control character in a cell, which Excel stores as such an escape, is an error (`illegal_character`).

## Git

Commit the tables, not the workbook. Add these lines to the `.gitignore` of the repository:

```text
*.xlsx
.*.pkdb-base
```

`pkdb tables sync` and `open` warn (`workbook_not_ignored`) and print the missing lines when the study is in a git repository that does not ignore the workbook or its state file. Git never ignores a file that it already tracks, such as a workbook of study format 1, so for a tracked workbook or state file they warn with `workbook_tracked` instead and print the command `git rm --cached Harder1988.xlsx`, which stops tracking the file and keeps it.

## Upload, validate and prepare

`pkdb upload` syncs a study format 2 folder that has a workbook before it uploads: your saved workbook edits are written to the tables, then the tables are formatted, then the study is prepared and uploaded. A workbook that was saved during the sync is synced once more, and one that is saved again during that second sync stops the upload, so upload again. Upload also stops and uploads nothing when the sync finds conflicts or errors, or when the tables cannot be formatted; the message names the command to run, `pkdb tables sync` or `pkdb format`. A workbook that is open does not stop it, the upload reports the warning and the workbook stays as it is. A folder without a workbook is only formatted, and no workbook is created. The workbook itself is never uploaded.

`pkdb validate` and `pkdb prepare` never write to the study folder. They check the tables, and when a workbook has changes that are not in the tables yet or cannot be synced, they say so and name `pkdb tables sync`; the JSON result has a `workbook` entry with the planned `changes` and the number of `conflicts`.

## Compatibility

The workbook is generated for Excel and LibreOffice Calc, and its round trip is tested with LibreOffice. Excel limits sheet names to 31 characters and compares them ignoring case, so layout validation rejects table files whose name before `.tsv` is longer than 31 characters (`table_name_too_long`) and names that differ only in case (`duplicate_table_name`). LibreOffice may shorten the range of rows that a dropdown covers when it saves a workbook; this is harmless, because dropdowns only suggest values, and a regeneration restores them.
