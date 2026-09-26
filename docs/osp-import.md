# OSP observed-data import

The first importer supports [OSP observed-data v1.9](https://github.com/Open-Systems-Pharmacology/Database-for-observed-data/releases/tag/v1.9). It pins the upstream commit and workbook checksum in `python/src/pkdb/importers/osp/release.py` for reproducible imports.

## Import

```bash
pkdb import osp --creator osp-import --output /path/to/new-import
# For an existing workbook, add: --offline --workbook /path/to/ObsDataPK_OSP.xlsx
```

The output directory must be new or empty. It contains study folders, a portable vocabulary, original source rows, and `import-report.json` with mapping warnings. The initial local import produced **741 studies and 33,103 reported outputs** from 3,079 assessments; artifacts and database verification are under `.cache/osp/v1.9/`.

Studies are identified by **publication + source**. OSP records use source `osp.observed-data` and are labelled **Automatic import**. Manual curation, imports, and automatic curation share the scientific model but retain separate provenance and citation snapshots. Re-importing a release replaces the same source study without overwriting manual curation. See the [data model](data-model.md).

Ambiguous statistics, units, and dosing schedules remain in source attachments and are listed in the report. Unknown sample sizes stay null. Review the vocabulary additions and warnings before uploading; not every source cell has a native scientific representation.

To load a configured server, create the attribution account, apply migration `p004sources`, and reconcile the vocabulary additions first. Set `PKDB_API_TOKEN`, then run:

```bash
pkdb-server validate /path/to/new-import/studies --api-url "$PKDB_API_URL"
pkdb-server upload /path/to/new-import/studies --api-url "$PKDB_API_URL"
```

Imports default to private access and closed licence. The portable vocabulary is for validation, not a replacement for an existing server's vocabulary.

## Regular release check

The **OSP release check** GitHub Actions workflow checks the latest stable upstream release **every Monday at 07:23 UTC**, with a manual **Run workflow** option. It becomes scheduled once merged into the repository's default branch, as required by [GitHub scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

The job summary reports the pinned and latest versions. A newer release fails the check to flag an update for review; request failures are reported separately. No data is downloaded or imported by this check. Run it locally with:

```bash
python3 scripts/check_osp_release.py
```

Exit codes: `0` current, `2` newer release, `1` failed check or unexpected upstream metadata. When an update appears, review the release and workbook changes, update the commit/checksum/version pin, adjust mappings if needed, validate, then import through the normal pipeline.
