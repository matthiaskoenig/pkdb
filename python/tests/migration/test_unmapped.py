from migration_fixtures import IMAGES, SHEETS, STUDY, v1_study

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.unmapped import unmapped_values

GROUP = {
    "source": "Tab1",
    "image": "Tab1",
    "name": "col==group",
    "count": "col==count",
    "characteristica": [
        {"measurement_type": "col==measurement", "mean": "col==mean", "unit": "yr"}
    ],
}
TAB1 = [
    ["group", "count", "measurement", "mean", "Median", "comments"],
    ["all", 2, "age", 35, "NA", "NA"],
    ["all", 2, "age", "NA", 40, 7],
]


def test_each_characteristic_of_a_subject_keeps_its_row(tmp_path):
    study = {**STUDY, "groupset": {"groups": [GROUP]}}
    v1 = v1_study(tmp_path, study, {**SHEETS, "Tab1": TAB1}, IMAGES)
    [group] = parse_bundle(load_folder(v1)).groups
    sources = [record.source for record in group.characteristica]
    assert group.source is not None and None not in sources
    assert [(s.sheet, s.row) for s in sources if s] == [("Tab1", 3), ("Tab1", 4)]
    # The headers that the template maps, those of characteristica included.
    assert group.source._mapped == {"group", "count", "measurement", "mean"}
    assert all(s and s._mapped == group.source._mapped for s in sources)


def test_numbers_of_unmapped_statistic_columns_are_found_in_hidden_tables(tmp_path):
    # A hidden table holds text: `40` is a number, and so the column of any
    # case named like a statistic; comments are no statistic.
    study = {**STUDY, "groupset": {"groups": [GROUP]}}
    v1 = v1_study(tmp_path, study, {**SHEETS, "Tab1": TAB1}, IMAGES, workbook=False)
    parsed = parse_bundle(load_folder(v1))
    keys = [record.key for record in parsed.groups[0].characteristica]
    assert unmapped_values(load_folder(v1), parsed, keys) == {
        keys[1]: [("Median", "40")]
    }
