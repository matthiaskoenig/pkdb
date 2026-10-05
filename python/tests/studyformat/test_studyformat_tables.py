from pkdb.studyformat.columns import ColumnType
from pkdb.studyformat.tables import (
    TABLES,
    image_file,
    parse_table_file,
    table_file,
)

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
