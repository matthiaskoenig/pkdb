"""Conservative folder construction and explicit field lineage for external data."""

import hashlib
import math
import re
from collections import Counter
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path
from platform import python_version

from pkdb.cache import atomic_json, bundled_vocabulary
from pkdb.domain.units import ureg
from pkdb.domain.vocabulary import MeasurementRule, SubstanceDefinition
from pkdb.importers.datasets.releases import RELEASES

SUMMARY = "unspecified summary"


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except ValueError, TypeError:
        return None


def text(value):
    return "" if value is None else str(value).strip()


def units(value):
    return (
        text(value)
        .replace("μ", "u")
        .replace("µ", "u")
        .replace("×", "*")
        .replace("²", "^2")
        .replace("%", "percent")
    )


@lru_cache(maxsize=4096)
def compatible(value, expected):
    try:
        return any(
            ureg(value).dimensionality == ureg(x).dimensionality for x in expected
        )
    except Exception:
        return False


def identifier(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:20]


def reference(value, fallback):
    from urllib.parse import unquote

    value = unquote(text(value))
    match = re.search(
        r"(?:pubmed\.ncbi\.nlm\.nih\.gov/|ncbi\.nlm\.nih\.gov/pubmed/)(\d+)", value
    )
    if match:
        pmid = str(int(match[1]))
        return "pmid:" + pmid, {"pmid": pmid}
    match = re.search(r"10\.\d{4,9}/[^\s?#]+", value, re.I)
    if match:
        doi = match[0].lower()
        return "doi:" + doi, {"doi": doi}
    if value.startswith(("http://", "https://")):
        return "url:" + value, {"url": value}
    return "source:" + str(fallback), {}


class Builder:
    def __init__(self, provider, creator):
        self.provider = provider
        self.pin = RELEASES[provider]
        self.creator = creator
        self.vocabulary = bundled_vocabulary()
        self.rules = self.vocabulary.measurement_map()
        self.substances = {}
        self.targets = {}
        self.extra_rules = {}
        self.software = {"python": python_version(), "pkdb": version("pkdb")}

    def rule(self, name, unit):
        if name not in self.rules:
            rule = MeasurementRule(
                name=name, sid="external-" + identifier(name), units=(unit,)
            )
            self.rules[name] = self.extra_rules[name] = rule
        return name

    def substance(self, source_id, name, mass=None):
        if not text(source_id) or not text(name):
            return None
        key = text(source_id)
        if key not in self.substances:
            molecular_mass = number(mass)
            self.substances[key] = SubstanceDefinition(
                sid=self.provider + "-" + identifier(key),
                name=f"{self.provider}: {name} [{key}]",
                mass=molecular_mass if molecular_mass and molecular_mass > 0 else None,
            )
        return self.substances[key].name

    def target(self, key, ref):
        if key not in self.targets:
            sid = self.provider.upper() + "_" + identifier(key)
            provenance = {
                "kind": "data_import",
                "source_key": self.pin["source_key"],
                "release": self.pin["release"],
                "revision": self.pin["revision"],
                "importer": "pkdb.datasets." + self.provider,
                "importer_version": "1",
                "assets": [{"url": self.pin["url"], "sha256": self.pin["sha256"]}],
                "dataset_ids": [],
                "report_file": "source-records.json",
                "evidence_kind": self.pin["evidence_kind"],
                "reference_scope": self.pin["reference_scope"],
                "source_terms": self.pin["terms"],
            }
            self.targets[key] = {
                "reference": {"sid": sid + ":reference", "name": key, **ref},
                "study": {
                    "sid": sid,
                    "name": sid,
                    "reference": sid + ":reference",
                    "creator": self.creator,
                    "access": "private",
                    "licence": "closed",
                    "provenance": provenance,
                    "groupset": {"groups": []},
                    "individualset": {"individuals": []},
                    "interventionset": {"interventions": []},
                    "outputset": {"outputs": []},
                },
                "records": [],
                "lineage": [],
                "warnings": [],
                "subjects": {},
            }
        return self.targets[key]

    def row(self, target, index, row, source_id):
        target["records"].append(
            {"row": index, "source_id": text(source_id), "values": row}
        )
        # Row identity, not just a publication identifier, survives every import.
        target["study"]["provenance"]["dataset_ids"].append(text(source_id))

    def warn(self, target, row, field, reason):
        target["warnings"].append({"row": row, "field": field, "code": reason})

    def append(self, target, collection, record, row, fields, operations):
        records = target["study"][collection + "set"][collection + "s"]
        index = len(records)
        records.append(record)
        target["lineage"].append(
            {
                "target": f"/{collection}set/{collection}s/{index}",
                "source_row": row,
                "source_fields": fields,
                "operations": operations,
            }
        )

    def group(self, target, key, row, count=None, *, fields=(), species=None, sex=None):
        if key not in target["subjects"]:
            n = number(count)
            name = "group_" + identifier(key)
            characteristics = []
            for measurement, choice in (("species", species), ("sex", sex)):
                if choice in self.rules[measurement].choices:
                    characteristics.append(
                        {"measurement_type": measurement, "choice": choice}
                    )
            self.append(
                target,
                "group",
                {
                    "name": name,
                    "characteristica": characteristics,
                    "count": int(n)
                    if n is not None and n >= 1 and n.is_integer()
                    else None,
                },
                row,
                list(fields),
                [
                    "source group identity; ambiguous count remains null",
                    "species and sex mapped only to known vocabulary choices",
                ],
            )
            target["subjects"][key] = name
        return target["subjects"][key]

    def output(
        self,
        target,
        row,
        field,
        value,
        unit,
        measurement,
        subject,
        substance,
        *,
        time=None,
        time_unit=None,
        tissue=None,
        individual=False,
        interventions=(),
        fields=(),
    ):
        parsed = number(value)
        if parsed is None or parsed < 0:
            self.warn(
                target,
                row,
                field,
                "missing_censored_or_non_numeric"
                if parsed is None
                else "negative_value",
            )
            return
        rule = self.rules[measurement]
        unit = units(unit)
        if not unit or not compatible(unit, rule.units) or not substance:
            self.warn(target, row, field, "unsupported_unit_or_analyte")
            return
        record = {
            "measurement_type": measurement,
            "substance": substance,
            "value": parsed,
            "unit": unit,
            "individual" if individual else "group": subject,
            "interventions": list(interventions),
            "descriptions": [
                f"Source row {row}, field {field}; see source-records.json."
            ],
        }
        if not individual:
            record["calculation_type"] = SUMMARY
        if tissue in self.vocabulary.tissues:
            record["tissue"] = tissue
        elif tissue:
            self.warn(target, row, "tissue", "unmapped_tissue")
        if number(time) is not None and compatible(units(time_unit), ("hr",)):
            record.update(time=number(time), time_unit=units(time_unit))
        elif rule.time_required:
            record.update(time="NR", time_unit="NR")
            self.warn(target, row, "time", "missing_or_unsupported_time")
        self.append(
            target,
            "output",
            record,
            row,
            list(dict.fromkeys([field, *fields])),
            [
                "strict finite numeric parsing",
                "unit spelling normalized; magnitude unchanged",
                "individual value"
                if individual
                else "summary statistic unspecified; no arithmetic-mean inference",
                "unmapped context retained in original row",
            ],
        )

    def write(self, output):
        output = Path(output)
        if output.exists() and any(output.iterdir()):
            raise ValueError("Output directory must be new or empty")
        output.mkdir(parents=True, exist_ok=True)
        vocabulary = self.vocabulary.model_copy(
            update={
                "substances": (*self.vocabulary.substances, *self.substances.values()),
                "measurements": (
                    *self.vocabulary.measurements,
                    *self.extra_rules.values(),
                ),
                "calculation_types": tuple(
                    dict.fromkeys((*self.vocabulary.calculation_types, SUMMARY))
                ),
                "version": self.vocabulary.version
                + "+"
                + self.provider
                + "-"
                + self.pin["release"],
            }
        )
        vocabulary.save(output / "vocabulary.json")
        entries = []
        warnings = Counter()
        for key, target in sorted(self.targets.items()):
            study = target["study"]
            study["provenance"]["dataset_ids"] = sorted(
                set(study["provenance"]["dataset_ids"])
            )
            folder = output / "studies" / study["name"]
            folder.mkdir(parents=True)
            atomic_json(folder / "study.json", study)
            atomic_json(folder / "reference.json", target["reference"])
            atomic_json(
                folder / "source-records.json",
                {
                    "artifact": self.pin,
                    "software": self.software,
                    "row_numbering": "one-based data row; excludes header",
                    "records": target["records"],
                    "lineage": target["lineage"],
                    "warnings": target["warnings"],
                    "coverage": "Only explicitly mapped fields are native records. All remaining source fields, including dose context, uncertainty and curation tags, are retained verbatim here. No source preprocessing, censor imputation, averaging or literature enrichment is performed.",
                },
            )
            warnings.update(w["code"] for w in target["warnings"])
            entries.append(
                {
                    "sid": study["sid"],
                    "publication_key": key,
                    "source_rows": len(target["records"]),
                    "mapped_measurements": len(study["outputset"]["outputs"]),
                }
            )
        report = {
            "provider": self.provider,
            **self.pin,
            "study_count": len(entries),
            "source_rows": sum(x["source_rows"] for x in entries),
            "mapped_measurements": sum(x["mapped_measurements"] for x in entries),
            "warning_counts": dict(warnings),
            "studies": entries,
        }
        atomic_json(output / "import-report.json", report)
        return report
