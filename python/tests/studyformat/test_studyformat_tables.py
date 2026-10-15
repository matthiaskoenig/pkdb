import re

from pkdb.cache import bundled_vocabulary
from pkdb.studyformat.columns import ColumnType
from pkdb.studyformat.tables import (
    INFO_CLASSES,
    KIND_LABELS,
    KIND_ORDER,
    RAW_KIND,
    TABLES,
    column_class,
    column_classes,
    image_file,
    parse_table_file,
    table_file,
)
from pkdb.studyformat.terms import vocabulary_terms

STATS = (
    "count mean sd se cv gmean gsd gcv median min max unit error_bar error_type"
).split()
# Built from the code point so the source file itself holds no em dash.
EM_DASH = chr(0x2014)
HEAD = "measurement calculation substance tissue method choice".split()


def test_tables_in_folder_order():
    assert list(TABLES) == [
        "subjects",
        "interventions",
        "characteristica",
        "outputs",
        "timecourses",
        "scatters",
    ]


def test_kind_order_puts_the_characteristica_after_the_subjects():
    assert sorted(TABLES, key=KIND_ORDER.__getitem__) == [
        "subjects",
        "characteristica",
        "interventions",
        "outputs",
        "timecourses",
        "scatters",
    ]


def test_column_order_matches_spec():
    assert TABLES["subjects"].names == (
        "study",
        "name",
        "parent",
        "count",
        "source",
        "comment",
    )
    assert TABLES["characteristica"].names == (
        "study",
        "source",
        "subjects",
        *HEAD,
        "time",
        "time_unit",
        *STATS,
        "comment",
    )
    assert TABLES["interventions"].names == (
        "study",
        "source",
        "name",
        "subjects",
        *HEAD,
        "route",
        "form",
        "application",
        "time",
        "time_end",
        "interval",
        "doses",
        "time_unit",
        *STATS,
        "comment",
    )
    assert TABLES["outputs"].names == (
        "study",
        "source",
        "subjects",
        "interventions",
        *HEAD,
        "time",
        "time_unit",
        *STATS,
        "comment",
    )
    assert TABLES["timecourses"].names == (
        "study",
        "source",
        "label",
        "subjects",
        "interventions",
        *HEAD,
        "time",
        "time_unit",
        *STATS,
        "comment",
    )
    axis = "interventions measurement substance tissue method time time_unit mean unit"
    assert TABLES["scatters"].names == (
        "study",
        "source",
        "name",
        "subjects",
        *(f"x_{name}" for name in axis.split()),
        *(f"y_{name}" for name in axis.split()),
        "comment",
    )


def test_owned_columns():
    for spec in TABLES.values():
        assert spec.column("study").owned
    for kind in ("outputs", "timecourses", "scatters"):
        assert TABLES[kind].per_source
        assert TABLES[kind].column("source").owned
    for kind in ("subjects", "interventions", "characteristica"):
        assert not TABLES[kind].per_source
        assert not TABLES[kind].column("source").owned


def test_references_and_types():
    assert TABLES["outputs"].column("subjects").references == "subjects"
    assert TABLES["outputs"].column("interventions").references == "interventions"
    assert TABLES["outputs"].column("interventions").type is ColumnType.NAMES
    assert TABLES["subjects"].column("parent").references == "subjects"
    assert TABLES["scatters"].column("x_interventions").references == "interventions"
    assert TABLES["interventions"].column("time").type is ColumnType.TIMES
    assert TABLES["outputs"].column("time").type is ColumnType.TIME
    assert TABLES["outputs"].column("error_type").choices == ("sd", "se", "gsd")
    assert TABLES["outputs"].column("measurement").vocabulary == "measurements"
    assert TABLES["outputs"].column("calculation").vocabulary == "calculation_types"
    assert TABLES["interventions"].column("route").vocabulary == "routes"


def test_required_columns():
    assert TABLES["subjects"].required
    assert not TABLES["outputs"].required
    assert TABLES["timecourses"].required_columns == {
        "label",
        "subjects",
        "measurement",
        "time",
        "time_unit",
    }
    assert TABLES["scatters"].required_columns == {
        "name",
        "subjects",
        "x_measurement",
        "x_mean",
        "y_measurement",
        "y_mean",
    }


def test_every_column_is_documented():
    for spec in TABLES.values():
        for column in spec.columns:
            assert column.description.endswith(".")
            assert EM_DASH not in column.description


def test_examples_are_vocabulary_terms():
    # The descriptions are the contract for AI agents: every term they name exists.
    vocabulary = bundled_vocabulary()
    rules = vocabulary.measurement_map()
    terms = vocabulary_terms(vocabulary)
    for spec in TABLES.values():
        for column in spec.columns:
            where = (spec.kind, column.name)
            if column.vocabulary:
                assert column.example in terms[column.vocabulary], where
            if column.vocabulary == "measurements":
                named = re.findall(r"`([^`]+)`", column.description)
                assert named and set(named) <= terms["measurements"], where
                if spec.kind == "scatters":
                    # A scatter axis has a numeric value and no choice.
                    assert {rules[term].dtype for term in named} == {"numeric"}, where
            if column.name == "choice":
                match = re.search(r"`([^`]+)` for `([^`]+)`", column.description)
                assert match is not None, where
                choice, measurement = match.groups()
                assert choice == column.example, where
                assert choice in rules[measurement].choices, where


def test_intervention_examples_are_interventions():
    choice = TABLES["interventions"].column("choice")
    assert "`fasting`" in choice.description
    measurement = TABLES["interventions"].column("measurement")
    assert "`fasting`" in measurement.description


def test_file_names():
    assert table_file("subjects") == "subjects.tsv"
    assert table_file("outputs", "Tab2") == "outputs_Tab2.tsv"
    assert parse_table_file("subjects.tsv") == (TABLES["subjects"], None)
    assert parse_table_file("timecourses_Fig3A.tsv") == (TABLES["timecourses"], "Fig3A")
    assert parse_table_file("outputs_Text.tsv") == (TABLES["outputs"], "Text")
    assert parse_table_file("scatters_Fig1_group.tsv") == (
        TABLES["scatters"],
        "Fig1_group",
    )
    assert parse_table_file("outputs.tsv") is None
    assert parse_table_file("subjects_Tab1.tsv") is None
    assert parse_table_file("outputs_Tab2.csv") is None
    assert parse_table_file("groups.tsv") is None
    assert image_file("Guo2016", "Fig2") == "Guo2016_Fig2.png"


def test_every_table_kind_and_the_raw_table_have_a_class_of_information_and_a_label():
    kinds = [*KIND_ORDER, RAW_KIND]
    assert [INFO_CLASSES[kind] for kind in kinds] == [
        "subjects",
        "subjects",
        "interventions",
        "data",
        "data",
        "data",
        "raw",
    ]
    assert [KIND_LABELS[kind] for kind in kinds] == [
        "Subjects",
        "Characteristica",
        "Interventions",
        "Outputs",
        "Timecourses",
        "Scatters",
        "Raw table",
    ]
    assert set(INFO_CLASSES) == set(KIND_LABELS) == set(kinds)


def _classes(kind: str) -> dict[str, str]:
    spec = TABLES[kind]
    return dict(zip(spec.names, column_classes(spec), strict=True))


def test_the_columns_of_a_data_table_are_classed_by_what_they_name():
    timecourses = _classes("timecourses")
    assert (timecourses["study"], timecourses["source"]) == ("meta", "meta")
    assert timecourses["subjects"] == "subjects"
    assert timecourses["interventions"] == "interventions"
    data = ("label", "measurement", "time", "mean", "sd", "error_type", "comment")
    assert {timecourses[name] for name in data} == {"data"}
    scatters = _classes("scatters")
    assert scatters["subjects"] == "subjects"
    assert (scatters["x_interventions"], scatters["y_interventions"]) == (
        "interventions",
        "interventions",
    )
    assert scatters["x_measurement"] == scatters["name"] == "data"
    assert set(_classes("outputs").values()) == {
        "meta",
        "subjects",
        "interventions",
        "data",
    }


def test_the_tables_of_subjects_and_interventions_are_wholly_of_their_class():
    for kind, info in (
        ("subjects", "subjects"),
        ("characteristica", "subjects"),
        ("interventions", "interventions"),
    ):
        classes = _classes(kind)
        assert (classes.pop("study"), classes.pop("source")) == ("meta", "meta")
        assert set(classes.values()) == {info}, kind


def test_a_column_of_a_data_table_is_classed_by_its_name():
    assert column_class("outputs", "parent") == "subjects"
    assert column_class("outputs", "donor_subjects") == "subjects"
    assert column_class("scatters", "z_interventions") == "interventions"
    # Only the ending counts, and only in the tables of the data.
    assert column_class("outputs", "subjects_count") == "data"
    assert column_class("interventions", "subjects") == "interventions"
    assert column_class("characteristica", "interventions") == "subjects"
    assert column_class("subjects", "source") == "meta"
