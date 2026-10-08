# Study format 2 cutover

The cutover converts every study folder of pkdb_data from study format 1 to study format 2 with `pkdb migrate`. Each study is converted from the entities that the format 1 parser resolved and is checked by an equivalence gate against that parser. Only studies whose data is identical, or differs only by intended changes, replace their format 1 folder. Run the cutover after the pkdb_data tooling (pre-commit, CI and the issue sync workflow) exists. The command needs Linux or macOS.

## Before the run

Fix the 20 invalid `study.json` files and the studies that are invalid in format 1 by normal pull requests. Merge or pause open curation pull requests, because they are written against format 1.

## Convert

Work on a branch of pkdb_data. Only one `pkdb migrate` runs per checkout, because it locks the repository root. Add `.pkdb-migrate/` to the `.gitignore` of pkdb_data.

```bash
pkdb migrate studies --approver <maintainer> --dry-run
```

Read `migration.md`, fix the format 1 studies or report converter bugs, and run again. When the dry run looks right, run the command without `--dry-run`. Repeat until `pkdb migrate` exits with 0, which means no study is `mismatch`, `invalid_v1` or `not_converted`. Each run converts only the studies that pass, so reruns are safe. A dry run writes only the report.

An interrupted run leaves `.pkdb-migrate/` at the repository root. The next real run finishes or undoes each interrupted swap, and a dry run refuses until that real run happened.

| Class | Result | What to do |
| --- | --- | --- |
| `identical` | Replaces the format 1 folder | Nothing. |
| `intended` | Replaces the format 1 folder | Check the listed changes and the manual decisions. |
| `mismatch` | Stays format 1 | Fix the format 1 study, see below, and rerun. |
| `invalid_v1` | Stays format 1 | The format 1 parser refuses the study. Fix it in format 1. |
| `not_converted` | Stays format 1 | Fix the reason in format 1, see below, and rerun. |

A `mismatch` mostly means that the converted study fails format 2 validation because of format 1 data defects that format 2 refuses: records without a central value (mean, gmean, median, min or max), concentrations or timecourse rows without time, repeated rows, choice rows without numeric statistics, and a group of one that is the parent of other subjects. The report lists the format 2 error codes and messages per study.

These `not_converted` reasons are fixed in format 1:

| Reason | Fix |
| --- | --- |
| `missing_image` | A table or figure source of outputs, timecourses or scatters needs `<study>_<source>.png`. |
| `image_conflict` | Two image files exist for one source. Keep one. |
| `sheet_name`, `image_name` | Rename to the source pattern `Tab...` or `Fig...`. |
| `subject_name` | Remove `,` `;` tabs and line breaks from names, and give a group and an individual different names. |
| `scatter_*` | For example `scatter_name`: two scatters with one subset name in different datasets, as in the caffeine studies Wood1979 and Roberts1976. Rename the subset. |
| `double_identifier` | Fix the identifier registry. |
| `no_subjects`, `metadata`, `reference` | Fix the study as named in the message. |
| `unreadable` | The format 1 parser refuses the folder, usually `invalid_v1`. |

A study without `reference.json` is resolved on a copy by the reference resolver, which needs the network. The original format 1 folder is not written. Check the section Manual decisions in `migration.md`: a replaced reference snapshot, unreleased public studies written as private, renamed timecourse labels, dropped output labels, converted JPG images, dropped data files (for example WebPlotDigitizer `.json` projects not named `.wpd.json`) and groups of one turned into individuals.

## Review and merge

Tag `v1-final` on `develop` before the merge. Review through `migration.md` (summary and manual decisions) and spot checks of converted studies. Merge one pull request with green CI.

## After the merge

Run `pkdb issues sync --adopt --dry-run`, review the result, then run it without `--dry-run`. Re-upload all studies with processing version 9 to staging and compare counts and API output with production. Delete the format 1 code once no format 1 branch is open.

## Papers

Folders without `study.json` move to `papers/<substance>/<name>/`. `pkdb new` takes the PDF and images from there.
