"""Decode verified distributions without executing upstream R scripts."""

import csv
import hashlib
import io
import tarfile
import zipfile
from importlib import import_module
from pathlib import Path

from pkdb.importers.datasets.common import Builder, number, reference, text
from pkdb.importers.datasets.releases import RELEASES


def rda_rows(payload, name):
    try:
        rdata = import_module("rdata")
    except ImportError as error:
        raise ValueError(
            "R datasets require the optional dependency: pip install 'pkdb[imports]'"
        ) from error
    import pandas as pd

    frame = rdata.read_rda(io.BytesIO(payload))[name]
    return [
        {
            str(k): None if pd.isna(v) else v.item() if hasattr(v, "item") else v
            for k, v in row.items()
        }
        for row in frame.to_dict("records")
    ]


def frdb(builder, rows):
    masses = {}
    for row in rows:
        key = (
            row.get("pk_analyte_unii")
            or row.get("pk_analyte_cid")
            or row.get("pk_analyte_pt")
        )
        mass = number(row.get("pk_analyte_mw"))
        if mass is not None and mass > 0:
            masses.setdefault(key, set()).add(mass)
    for index, row in enumerate(rows, 1):
        key, ref = reference(row.get("pk_source_uri"), row["id"])
        target = builder.target(key, ref)
        builder.row(target, index, row, row["id"])
        subject = builder.group(
            target,
            row["id"],
            index,
            row.get("pk_population_size"),
            fields=("id", "pk_population_size", "pk_species", "pk_sex"),
            species=text(row.get("pk_species")).lower(),
            sex={"FEMALE": "F", "MALE": "M", "FEMALE / MALE": "MF"}.get(
                row.get("pk_sex")
            ),
        )
        chemical = (
            row.get("pk_analyte_unii")
            or row.get("pk_analyte_cid")
            or row.get("pk_analyte_pt")
        )
        candidates = masses.get(chemical, set())
        if len(candidates) > 1:
            builder.warn(
                target,
                index,
                "pk_analyte_mw",
                "conflicting_molecular_mass_retained_in_source",
            )
        substance = builder.substance(
            chemical,
            row.get("pk_analyte_pt"),
            next(iter(candidates)) if len(candidates) == 1 else None,
        )
        for prefix, measurement in [
            ("cmax", "cmax"),
            ("thalf", "thalf"),
            ("auc", "auc_inf"),
        ]:
            field = f"pk_{prefix}_value"
            if not text(row.get(field)):
                continue
            time = time_unit = None
            if prefix == "auc":
                kind = text(row.get("pk_auc_type")).lower()
                if kind == "t":
                    measurement, time, time_unit = (
                        "auc_end",
                        row.get("pk_auc_hours"),
                        "hr",
                    )
                elif kind not in {"infinity", "∞"}:
                    builder.warn(target, index, field, "unknown_auc_interval")
                    continue
            builder.output(
                target,
                index,
                field,
                row[field],
                row.get(f"pk_{prefix}_units"),
                measurement,
                subject,
                substance,
                time=time,
                time_unit=time_unit,
                tissue=text(row.get("pk_analyte_tissue")).lower(),
                fields=(
                    f"pk_{prefix}_units",
                    "pk_analyte_unii",
                    "pk_analyte_cid",
                    "pk_analyte_pt",
                    "pk_analyte_mw",
                    "pk_analyte_tissue",
                    "pk_auc_type",
                    "pk_auc_hours",
                    "id",
                ),
            )
        builder.warn(
            target,
            index,
            "dose/subject context/fraction unbound",
            "context_retained_in_source",
        )


def cvtdb_references(rows):
    # Union aliases across extraction documents before generating stable studies.
    parents = {}

    def root(alias):
        parents.setdefault(alias, alias)
        if parents[alias] != alias:
            parents[alias] = root(parents[alias])
        return parents[alias]

    row_aliases = []
    values = {}
    for row in rows:
        aliases = []
        pmid = number(row.get("pmid"))
        if pmid and pmid > 0 and pmid.is_integer():
            key = "pmid:" + str(int(pmid))
            aliases.append(key)
            values[key] = {"pmid": str(int(pmid))}
        doi = text(row.get("doi"))
        if doi:
            key, ref = reference(doi, row["fk_extraction_document_id"])
            if "doi" in ref:
                aliases.append(key)
                values[key] = ref
        # The extraction document also bridges records with missing identifiers.
        key = "document:" + text(row["fk_extraction_document_id"])
        aliases.append(key)
        values[key] = {}
        root(aliases[0])
        for alias in aliases[1:]:
            parents[root(alias)] = root(aliases[0])
        row_aliases.append(aliases)
    components = {}
    for alias in parents:
        components.setdefault(root(alias), []).append(alias)
    references = {}
    for key, aliases in components.items():
        pmids = [a for a in aliases if a.startswith("pmid:")]
        dois = [a for a in aliases if a.startswith("doi:")]
        if len(pmids) > 1 or len(dois) > 1:
            raise ValueError(f"Conflicting publication aliases in CvTdb: {aliases}")
        selected = (sorted(pmids) or sorted(dois) or sorted(aliases))[0]
        refs = {}
        for alias in aliases:
            refs.update(values[alias])
        references[key] = selected, refs
    return [references[root(aliases[0])] for aliases in row_aliases]


def cvtdb(builder, rows):
    references = cvtdb_references(rows)
    for index, (row, (key, ref)) in enumerate(zip(rows, references, strict=True), 1):
        if not ref:
            ref = (
                {"url": row["url"]}
                if text(row.get("url")).startswith(("http://", "https://"))
                else {}
            )
        target = builder.target(key, ref)
        builder.row(target, index, row, row["conc_time_id"])
        # Count belongs to a series; keep it in the key to avoid conflicting group sizes.
        group_key = (
            row["fk_study_id"],
            row["fk_subject_id"],
            row.get("n_subjects_in_series"),
        )
        subject = builder.group(
            target,
            group_key,
            index,
            row.get("n_subjects_in_series"),
            fields=(
                "fk_study_id",
                "fk_subject_id",
                "n_subjects_in_series",
                "species",
                "sex",
            ),
            species={
                "rat": "rattus norvegicus",
                "mouse": "mus musculus",
                "human": "homo sapiens",
                "dog": "canis familiaris",
            }.get(text(row.get("species")).lower()),
            sex={"male": "M", "female": "F", "M": "M", "F": "F"}.get(row.get("sex")),
        )
        substance = builder.substance(
            row.get("analyzed_chem_dtxsid")
            or "chemical:" + text(row["fk_analyzed_chemical_id"]),
            row.get("analyzed_chem_name_original") or row.get("analyzed_chem_name"),
        )
        builder.output(
            target,
            index,
            "conc_original",
            row["conc_original"],
            row["conc_units_original"],
            "concentration",
            subject,
            substance,
            time=row["time_original"],
            time_unit=row["time_units_original"],
            tissue=text(row.get("conc_medium_original")).lower(),
            fields=(
                "conc_units_original",
                "time_original",
                "time_units_original",
                "analyzed_chem_dtxsid",
                "fk_analyzed_chemical_id",
                "analyzed_chem_name_original",
                "analyzed_chem_name",
                "conc_medium_original",
                "fk_study_id",
                "fk_subject_id",
                "n_subjects_in_series",
            ),
        )
        builder.warn(
            target, index, "dose/subject context/SD/LOQ", "context_retained_in_source"
        )


def warfarin(builder, rows):
    url = "https://nlmixr2.github.io/nlmixr2data/reference/warfarin.html"
    target = builder.target(
        "url:" + url,
        {
            "name": "nlmixr2data warfarin PK/PD compilation",
            "url": url,
            "provenance": {
                "publication_attribution": "unresolved",
                "supporting_references": [
                    {"pmid": "14074349", "doi": "10.1172/JCI104839"},
                    {"pmid": "11712286", "doi": "10.1161/01.cir.38.1.169"},
                ],
                "preparation_history": "Distributed experimental example; transformations from original publications are undocumented.",
            },
        },
    )
    substance = builder.substance("warfarin", "warfarin")
    pca = builder.rule("prothrombin complex activity", "percent")
    subjects = {}
    doses = {}
    for index, row in enumerate(rows, 1):
        builder.row(target, index, row, index)
        key = text(row["id"])
        if key not in subjects:
            subjects[key] = "subject_" + key
            builder.append(
                target,
                "individual",
                {
                    "name": subjects[key],
                    "characteristica": [
                        {
                            "measurement_type": "weight",
                            "value": row["wt"],
                            "unit": "kg",
                        },
                        {"measurement_type": "age", "value": row["age"], "unit": "yr"},
                        {
                            "measurement_type": "sex",
                            "choice": {"male": "M", "female": "F"}[row["sex"]],
                        },
                    ],
                },
                index,
                ["id", "wt", "age", "sex"],
                [
                    "source individual identity",
                    "sex vocabulary mapping; age years and weight kg per upstream documentation",
                ],
            )
        if row["evid"] == 1:
            name = "dose_row_" + str(index)
            doses.setdefault(key, []).append(name)
            builder.append(
                target,
                "intervention",
                {
                    "name": name,
                    "measurement_type": "dosing",
                    "substance": substance,
                    "value": row["amt"],
                    "unit": "mg",
                    "time": row["time"],
                    "time_unit": "hr",
                    "route": "NR",
                    "form": "NR",
                    "application": "single dose",
                },
                index,
                ["amt", "time", "evid"],
                [
                    "evid=1 is dose; dv=0 is a placeholder and not an observation",
                    "mg and hours per upstream documentation; route/form absent in artifact",
                ],
            )
    for index, row in enumerate(rows, 1):
        if row["evid"] != 0:
            continue
        if row["dvid"] not in {"cp", "pca"}:
            raise ValueError("Unknown warfarin endpoint")
        key = text(row["id"])
        builder.output(
            target,
            index,
            "dv",
            row["dv"],
            "mg/l" if row["dvid"] == "cp" else "percent",
            "concentration" if row["dvid"] == "cp" else pca,
            subjects[key],
            substance,
            time=row["time"],
            time_unit="hr",
            individual=True,
            interventions=doses.get(key, ()),
            fields=("id", "time", "dvid", "evid"),
        )
    target["warnings"].append(
        {
            "row": None,
            "field": "publication/duplicate observations",
            "code": "collection_attribution_unresolved_duplicates_preserved",
        }
    )


def import_dataset(provider, path, output, *, creator):
    pin = RELEASES[provider]
    path = Path(path)
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != pin["sha256"]:
        raise ValueError(f"Artifact checksum does not match pinned {provider} release")
    if Path(output).exists() and any(Path(output).iterdir()):
        raise ValueError("Output directory must be new or empty")
    builder = Builder(provider, creator)
    if provider in {"cvtdb", "warfarin"}:
        from importlib.metadata import PackageNotFoundError, version

        try:
            builder.software.update(rdata=version("rdata"), pandas=version("pandas"))
        except PackageNotFoundError as error:
            raise ValueError(
                "R datasets require: pip install 'pkdb[imports]'"
            ) from error
    if provider == "frdb":
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            content = archive.read(pin["member"]).decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(content), delimiter="\t"))
    elif provider == "cvtdb":
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            member = archive.extractfile(pin["member"])
            if member is None:
                raise ValueError("CvTdb data member is missing")
            rows = rda_rows(member.read(), "cvtdb_original")
    else:
        rows = rda_rows(payload, "warfarin")
    {"frdb": frdb, "cvtdb": cvtdb, "warfarin": warfarin}[provider](builder, rows)
    report = builder.write(output)
    # Preserve the verified original distribution, including source notices and metadata.
    artifact = Path(output) / "artifacts" / pin["url"].rsplit("/", 1)[-1]
    artifact.parent.mkdir()
    artifact.write_bytes(payload)
    return report
