"""Reviewed artifact pins. Updating these requires reviewing data and mapping changes."""

RELEASES = {
    "frdb": {
        "source_key": "ncats.frdb",
        "release": "2024-12-30",
        "revision": "frdb-v2024-12-30",
        "url": "https://drugs.ncats.io/downloads-public/frdb-v2024-12-30.zip",
        "sha256": "647b80d9cdac4a0517ce649570517dc1aff40545bdc84617ec9f1a56405f9c7a",
        "member": "frdb/frdb-pk.tsv",
        "terms": "No dataset-specific licence identified in the distribution; reuse terms unresolved.",
        "reference_scope": "source_document",
        "evidence_kind": "unknown",
    },
    "cvtdb": {
        "source_key": "epa.cvtdb",
        "release": "invivoPKfit-2.0.2",
        "revision": "CvTdb-2025-08-12",
        "url": "https://cran.r-project.org/src/contrib/invivoPKfit_2.0.2.tar.gz",
        "sha256": "5fcd5592e07578a0582b38be74abf6286eda7966226b01cf9adcc2c1a8a55148",
        "member": "invivoPKfit/data/cvtdb_original.rda",
        "terms": "Package licence GPL-3; no separate data-specific licence identified. Original publication rights remain distinct.",
        "reference_scope": "source_document",
        "evidence_kind": "observed",
    },
    "warfarin": {
        "source_key": "nlmixr2data.warfarin",
        "release": "nlmixr2data-2.0.10",
        "revision": "f2cfb01ade88d4d30e66f56b19efce2a2c6e26bd",
        "url": "https://raw.githubusercontent.com/nlmixr2/nlmixr2data/f2cfb01ade88d4d30e66f56b19efce2a2c6e26bd/data/warfarin.rda",
        "sha256": "331274f96ee87506c4360c7642f1d625735b6ebd14e5e1b2df5fece355438a51",
        "member": "warfarin",
        "terms": "Package licence GPL (>= 3); original publication rights and preparation history remain distinct.",
        "reference_scope": "compilation",
        "evidence_kind": "observed",
    },
}
