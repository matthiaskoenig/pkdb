"""The vocabulary of the study format tests, shared by fixtures and test helpers."""

from pkdb.domain.vocabulary import MeasurementRule, SubstanceDefinition, Vocabulary


def studyformat_vocabulary() -> Vocabulary:
    return Vocabulary(
        version="studyformat-test",
        measurements=(
            MeasurementRule(
                name="species", dtype="categorical", choices=("Homo sapiens",)
            ),
            MeasurementRule(name="healthy", dtype="boolean", choices=("Y", "N")),
            MeasurementRule(name="sex", dtype="categorical", choices=("M", "F", "NR")),
            MeasurementRule(name="age", units=("yr",)),
            # Numeric, but a row without a value states the abstinence.
            MeasurementRule(name="abstinence", units=("day", "NO_UNIT")),
            # A value, such as the years since diagnosis, or a choice.
            MeasurementRule(
                name="disease",
                dtype="numeric_categorical",
                units=("yr", "NO_UNIT"),
                choices=("t2dm", "cirrhosis"),
            ),
            MeasurementRule(name="concentration", units=("mg/l",), time_required=True),
            MeasurementRule(name="cmax", units=("mg/l",)),
            MeasurementRule(name="dosing", units=("mg",)),
            # Numeric in the bundled vocabulary, but used without a dose.
            MeasurementRule(name="qualitative dosing", units=("mg", "NO_UNIT")),
            MeasurementRule(name="fasting", dtype="boolean", choices=("Y", "N")),
            MeasurementRule(name="kinetics", dtype="abstract"),
            MeasurementRule(
                name="medication", dtype="boolean", choices=("Y", "N", "NR")
            ),
            MeasurementRule(name="change", units=("mg/l",), can_negative=True),
            MeasurementRule(name="old_measure", units=("mg/l",), deprecated=True),
            # Pharmacokinetic parameters that postprocessing derives from timecourses.
            MeasurementRule(name="auc_end", units=("g/l*hr", "mol/l*hr")),
            MeasurementRule(name="auc_inf", units=("g/l*hr", "mol/l*hr")),
            MeasurementRule(name="clearance", units=("l/hr", "l/hr/kg")),
            MeasurementRule(name="kel", units=("1/min",)),
            MeasurementRule(name="thalf", units=("hr",)),
            MeasurementRule(name="tmax", units=("hr",)),
            MeasurementRule(name="vd", units=("l", "l/kg")),
            MeasurementRule(name="vd_ss", units=("l", "l/kg")),
        ),
        substances=(SubstanceDefinition(name="drug", sid="drug", mass=500),),
        tissues=("plasma",),
        methods=("HPLC",),
        routes=("oral",),
        forms=("tablet",),
        applications=(
            "single dose",
            "multiple dose",
            "constant infusion",
            "variable infusion",
        ),
        calculation_types=("calculation", "geometric mean", "sample mean"),
    )
