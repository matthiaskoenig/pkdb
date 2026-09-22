"""Batched in-memory scientific validation, independent of transport and storage."""

import re
from collections import Counter

import pint

from pkdb.domain.datasets import add_generated_timecourses, compile_datasets
from pkdb.domain.normalization import normalize_record
from pkdb.domain.pharmacokinetics import build_timecourses, derive_pk
from pkdb.domain.statistics import complete_statistics
from pkdb.domain.units import ureg
from pkdb.domain.vocabulary import Vocabulary
from pkdb.schemas.prepared import PreparedStudy
from pkdb.schemas.study import (
    CanonicalStudy,
    Intervention,
    Measurement,
    ScientificRecord,
)
from pkdb.schemas.validation import (
    StudyValidationError,
    ValidationIssue,
    ValidationReport,
)

PROCESSING_VERSION = "2"
NUMERIC_FIELDS = ("value", "mean", "median", "min", "max", "sd", "se", "cv")


def prepare_study(
    study: CanonicalStudy, vocabulary: Vocabulary, *, max_issues: int = 100
) -> PreparedStudy:
    if max_issues < 1:
        raise ValueError("max_issues must be positive")
    study = study.model_copy(deep=True)
    group_counts = {group.name: group.count for group in study.groups}
    for group in study.groups:
        for record in group.characteristica:
            if record.statistics.count is None:
                record.statistics.count = group.count
            if (
                record.calculation_type is None
                and "sample mean" in vocabulary.calculation_types
            ):
                record.calculation_type = "sample mean"
    for individual in study.individuals:
        for record in individual.characteristica:
            if record.statistics.count is None:
                record.statistics.count = 1
    for record in study.measurements:
        if record.group:
            if (
                record.calculation_type is None
                and "sample mean" in vocabulary.calculation_types
            ):
                record.calculation_type = "sample mean"
    report = ValidationReport()

    def issue(code, message, record=None, severity="error"):
        if severity == "error":
            report.error_count += 1
        if len(report.issues) >= max_issues:
            report.truncated = True
            return
        report.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                severity=severity,
                source=getattr(record, "source", None),
            )
        )

    def unique(values, kind):
        for value, count in Counter(values).items():
            if count > 1:
                issue("duplicate_identifier", f"Duplicate {kind}: {value}")

    unique([g.name for g in study.groups], "group")
    unique([i.name for i in study.individuals], "individual")
    unique([i.name for i in study.interventions], "intervention")
    unique([m.key for m in study.measurements], "measurement")
    unique([c.user for c in study.metadata.curators], "curator")
    unique(study.metadata.collaborators, "collaborator")
    groups = {g.name: g for g in study.groups}
    individuals = {i.name: i for i in study.individuals}
    interventions = {i.name: i for i in study.interventions}
    rules = vocabulary.measurement_map()
    substances = vocabulary.substance_map()
    normalized: dict[str, ScientificRecord] = {}
    for group in study.groups:
        if group.parent and group.parent not in groups:
            issue("unknown_parent", f"Unknown group parent: {group.parent}", group)
        seen = set()
        node = group
        while node:
            if node.name in seen:
                issue(
                    "group_cycle",
                    f"Group hierarchy contains a cycle at {node.name}",
                    group,
                )
                break
            seen.add(node.name)
            node = groups.get(node.parent)
        if group.name == "all":
            missing = {"species", "healthy", "sex"} - {
                c.measurement_type for c in group.characteristica
            }
            if missing:
                issue(
                    "missing_characteristics",
                    f"Group all lacks {sorted(missing)}",
                    group,
                )
        for characteristic in group.characteristica:
            if (
                characteristic.statistics.count is not None
                and characteristic.statistics.count > group.count
            ):
                issue(
                    "characteristic_count",
                    "Characteristic count exceeds group count",
                    characteristic,
                )
            if characteristic.statistics.value is not None:
                issue(
                    "group_value",
                    "Group characteristics use mean/median, not individual value",
                    characteristic,
                )
    for individual in study.individuals:
        if individual.group and individual.group not in groups:
            issue(
                "unknown_group",
                f"Unknown individual group: {individual.group}",
                individual,
            )

    def validate_individual(record):
        prohibited = [
            field
            for field in ("mean", "median", "min", "sd", "se", "cv")
            if getattr(record.statistics, field) is not None
        ]
        if prohibited or record.calculation_type is not None:
            issue(
                "individual_statistics",
                "Individual records cannot contain population statistics or calculation_type",
                record,
            )

    for individual in study.individuals:
        for characteristic in individual.characteristica:
            validate_individual(characteristic)
    for measurement in study.measurements:
        if measurement.individual:
            validate_individual(measurement)
        if measurement.group and measurement.statistics.value is not None:
            issue(
                "group_value",
                "Group outputs cannot contain individual value",
                measurement,
            )
        if bool(measurement.group) == bool(measurement.individual):
            issue(
                "subject_reference",
                "Output must refer to exactly one group or individual",
                measurement,
            )
        if measurement.group and measurement.group not in groups:
            issue("unknown_group", f"Unknown group: {measurement.group}", measurement)
        if measurement.individual and measurement.individual not in individuals:
            issue(
                "unknown_individual",
                f"Unknown individual: {measurement.individual}",
                measurement,
            )
        for name in measurement.interventions:
            if name not in interventions:
                issue(
                    "unknown_intervention", f"Unknown intervention: {name}", measurement
                )
        if measurement.output_type == "timecourse" and not measurement.label:
            issue("missing_label", "Timecourse points require a label", measurement)
    records: list[ScientificRecord] = [*study.interventions, *study.measurements]
    records.extend(
        c
        for subject in [*study.groups, *study.individuals]
        for c in subject.characteristica
    )
    for record in records:
        rule = rules.get(record.measurement_type)
        if rule is None:
            issue(
                "unknown_measurement",
                f"Unknown measurement: {record.measurement_type}",
                record,
            )
            continue
        if record.substance and record.substance not in substances:
            issue("unknown_substance", f"Unknown substance: {record.substance}", record)
        for field, allowed in [
            ("tissue", vocabulary.tissues),
            ("method", vocabulary.methods),
            ("route", vocabulary.routes),
            ("form", vocabulary.forms),
            ("application", vocabulary.applications),
            ("calculation_type", vocabulary.calculation_types),
        ]:
            value = getattr(record, field, None)
            if value and value not in allowed:
                issue("unknown_" + field, f"Unknown {field}: {value}", record)
        if record.choice:
            if (
                rule.dtype not in {"categorical", "boolean", "numeric_categorical"}
                or record.choice not in rule.choices
            ):
                issue(
                    "invalid_choice",
                    f"Invalid choice {record.choice} for {rule.name}",
                    record,
                )
        elif rule.choices:
            issue("missing_choice", f"A choice is required for {rule.name}", record)
        for field in NUMERIC_FIELDS:
            value = getattr(record.statistics, field)
            if value is not None and value < 0 and not rule.can_negative:
                issue(
                    "negative_value",
                    f"{field} must be nonnegative for {rule.name}",
                    record,
                )
        if (
            record.statistics.min is not None
            and record.statistics.max is not None
            and record.statistics.min > record.statistics.max
        ):
            issue(
                "reversed_range", "Minimum exceeds maximum", record, severity="warning"
            )
        if rule.deprecated:
            issue(
                "deprecated_measurement",
                f"{rule.name} is deprecated",
                record,
                severity="warning",
            )
        if isinstance(record, Measurement):
            if (
                rule.time_required
                and record.time is None
                and not record.time_not_reported
            ):
                issue("missing_time", f"Time is required for {rule.name}", record)
            if (
                rule.time_required
                and not record.time_unit
                and not (record.time_not_reported or record.time_unit_not_reported)
            ):
                issue(
                    "missing_time_unit",
                    f"Time unit is required for {rule.name}",
                    record,
                )
        time_unit = getattr(record, "time_unit", None)
        if time_unit:
            try:
                if not ureg(time_unit).check("[time]"):
                    issue(
                        "time_dimension",
                        "Time unit must have time dimensionality",
                        record,
                    )
            except (pint.PintError, ValueError, TypeError):
                issue("invalid_time_unit", f"Invalid time unit: {time_unit}", record)
        if record.unit and not re.fullmatch(
            r"[\/^_*.() µα-ωΑ-Ωa-zA-Z0-9]*", record.unit
        ):
            issue("invalid_unit", "Unit contains unsupported characters", record)
            continue
        if not record.unit:
            if rule.units and "NO_UNIT" not in rule.units:
                issue("missing_unit", f"Unit is required for {rule.name}", record)
            else:
                normalized[record.key] = normalize_record(record, rule)
            continue
        try:
            substance = substances.get(record.substance)
            candidate = normalize_record(
                record, rule, molar_mass=substance.mass if substance else None
            )
            normalized[record.key] = candidate
            if rule.name == "recovery":
                for field in ("value", "mean", "median"):
                    value = getattr(record.statistics, field)
                    if (
                        value is not None
                        and ureg.Quantity(value, record.unit)
                        .to("dimensionless")
                        .magnitude
                        > 2
                    ):
                        issue("recovery_range", "Recovery cannot exceed 200%", record)
        except StudyValidationError as error:
            for detail in error.report.issues:
                issue(detail.code, detail.message, record)
    for intervention in study.interventions:
        if intervention.measurement_type in {"dosing", "medication"}:
            for field in ("substance", "route", "unit"):
                if not getattr(intervention, field):
                    issue(
                        "missing_dosing_field",
                        f"{field} required for dosing",
                        intervention,
                    )
            if intervention.statistics.value is None:
                issue("missing_dose", "Dose value is required", intervention)
        if intervention.measurement_type == "dosing":
            for field in ("form", "application", "time", "time_unit"):
                if getattr(intervention, field) is None:
                    issue(
                        "missing_dosing_field",
                        f"{field} required for dosing",
                        intervention,
                    )
            if intervention.application not in {
                "single dose",
                "multiple dose",
                "constant infusion",
            }:
                issue(
                    "invalid_application",
                    "Unsupported dosing application",
                    intervention,
                )
    if not report.valid:
        raise StudyValidationError(report)
    for candidate in normalized.values():
        if isinstance(candidate, Measurement) and candidate.group:
            candidate.statistics = complete_statistics(
                candidate.statistics, group_counts.get(candidate.group)
            )
    prepared = study.model_copy(deep=True)
    prepared.measurements.extend(
        item
        for m in study.measurements
        if isinstance(item := normalized.get(m.key), Measurement)
    )
    prepared.interventions.extend(
        item
        for intervention in study.interventions
        if isinstance(item := normalized.get(intervention.key), Intervention)
    )
    for subject in [*prepared.groups, *prepared.individuals]:
        originals = list(subject.characteristica)
        subject.characteristica.extend(
            normalized[record.key] for record in originals if record.key in normalized
        )
    prepared.timecourses = build_timecourses(prepared.measurements)
    add_generated_timecourses(prepared)
    compile_datasets(prepared)
    for course in prepared.timecourses:
        if not course.points or course.points[0].origin != "normalized":
            continue
        candidates = [
            interventions[name]
            for name in course.points[0].interventions
            if name in interventions
            and interventions[name].substance == course.points[0].substance
        ]
        dose = candidates[0] if len(candidates) == 1 else None
        for generated in derive_pk(course, dose):
            rule = rules.get(generated.measurement_type)
            if rule is None:
                issue(
                    "unknown_generated_measurement",
                    f"Missing PK vocabulary: {generated.measurement_type}",
                    generated,
                )
                continue
            try:
                checked = normalize_record(generated, rule)
                prepared.measurements.extend(
                    [
                        Measurement.model_validate(generated.model_dump()),
                        Measurement.model_validate(checked.model_dump()),
                    ]
                )
            except StudyValidationError as error:
                for detail in error.report.issues:
                    issue(detail.code, detail.message, generated)
    if not report.valid:
        raise StudyValidationError(report)
    return PreparedStudy(
        study=prepared,
        report=report,
        vocabulary_version=vocabulary.version,
        processing_version=PROCESSING_VERSION,
    )
