import pytest

from pkdb.domain.validation import prepare_study
from pkdb.importers.folder import parse_bundle
from pkdb.schemas.study import DataRecord, Dimension, Subset
from pkdb.schemas.validation import StudyValidationError


def scatter_study(valid_study):
    study = valid_study.model_copy(deep=True)
    base = study.measurements[0]
    study.measurements = [
        base.model_copy(
            deep=True,
            update={
                "key": f"{label}-{time}",
                "label": label,
                "time": float(time),
                "output_type": "array",
            },
        )
        for time in (0, 1)
        for label in ("x", "y")
    ]
    study.scatters = [
        DataRecord(
            key="scatter",
            name="correlation",
            data_type="scatter",
            subsets=[
                Subset(
                    name="pairs",
                    shared=["time"],
                    dimensions=[
                        Dimension(dimension="0", output="x"),
                        Dimension(dimension="1", output="y"),
                    ],
                )
            ],
        )
    ]
    return study


def test_scatter_labels_expand_to_paired_normalized_measurements(
    valid_study, vocabulary
):
    prepared = prepare_study(scatter_study(valid_study), vocabulary)
    subset = prepared.study.scatters[0].subsets[0]
    assert len(subset.points) == 2
    records = {r.key: r for r in prepared.study.measurements}
    for x_key, y_key in subset.points:
        x, y = records[x_key], records[y_key]
        assert x.label == "x" and y.label == "y"
        assert x.time == y.time
        assert x.origin == y.origin == "normalized"


@pytest.mark.parametrize("mode", ["ambiguous", "missing", "unknown_shared"])
def test_scatter_rejects_ambiguous_or_missing_pairings(valid_study, vocabulary, mode):
    study = scatter_study(valid_study)
    if mode == "ambiguous":
        study.measurements.append(
            study.measurements[0].model_copy(update={"key": "duplicate"})
        )
    elif mode == "missing":
        study.measurements.pop()
    else:
        study.scatters[0].subsets[0].shared = ["unknown"]
    with pytest.raises(StudyValidationError):
        prepare_study(study, vocabulary)


def test_importer_accepts_legacy_dimension_labels(valid_bundle):
    valid_bundle.study["dataset"] = {
        "data": [
            {
                "name": "correlation",
                "data_type": "scatter",
                "subsets": [
                    {
                        "name": "pairs",
                        "shared": ["individual"],
                        "dimensions": ["x", "y"],
                    }
                ],
            }
        ]
    }
    study = parse_bundle(valid_bundle)
    assert [
        dimension.output for dimension in study.scatters[0].subsets[0].dimensions
    ] == ["x", "y"]


def test_explicit_timecourse_resolves_original_records(valid_study, vocabulary):
    study = scatter_study(valid_study)
    study.scatters[0].data_type = "timecourse"
    study.scatters[0].subsets[0].dimensions = [Dimension(dimension="0", output="x")]
    study.scatters[0].subsets[0].shared = []
    from pkdb.domain.datasets import compile_datasets

    prepared = prepare_study(scatter_study(valid_study), vocabulary).study
    prepared.scatters = study.scatters
    compile_datasets(prepared)
    assert len(prepared.timecourses) == 1
    points = prepared.scatters[0].subsets[0].points
    assert points == [[point.key] for point in prepared.timecourses[0].points]
    assert {key for point in points for key in point} <= {
        row.key for row in prepared.measurements
    }


def test_nested_characteristics_expand_parallel_values(valid_bundle):
    group = valid_bundle.study["groupset"]["groups"][0]
    group["characteristica"] = [
        {"measurement_type": "sex", "choice": "F || M", "count": "1 || 3"}
    ]
    study = parse_bundle(valid_bundle)
    assert [
        (c.choice, c.statistics.count) for c in study.groups[0].characteristica
    ] == [("F", 1), ("M", 3)]


def test_legacy_comment_pair_preserves_author(valid_bundle):
    valid_bundle.study["groupset"]["groups"][0]["comments"] = [
        ["curator", "Source clarification"]
    ]
    study = parse_bundle(valid_bundle)
    assert study.groups[0].comments[0].user == "curator"
    assert study.groups[0].comments[0].text == "Source clarification"


def test_empty_mapped_intervention_cell_is_an_empty_list():
    from pkdb.importers.expressions import bind_columns

    assert bind_columns({"interventions": ["col==dose"]}, {"dose": None}) == {
        "interventions": []
    }


def test_equivalent_dimension_order_does_not_change_normalization():
    from pkdb.domain.normalization import conversion

    factor, _ = conversion("hr * µg / ml", ("g / l * hr",), None)
    assert factor == pytest.approx(0.001)


def test_workbook_dataset_rows_group_subsets_by_data_name(valid_bundle, tmp_path):
    source = tmp_path / ".Example_Data.tsv"
    source.write_text(
        "data_name\tsubset_name\tdimensions\tshared\nFig1\ta\tx,y\ttime\nFig1\tb\tx,z\ttime\n"
    )
    valid_bundle.files[source.name] = source
    valid_bundle.study["dataset"] = {
        "data": [
            {
                "name": "col==data_name",
                "source": "Data",
                "data_type": "scatter",
                "subsets": [
                    {
                        "name": "col==subset_name",
                        "dimensions": "col==dimensions",
                        "shared": "col==shared",
                    }
                ],
            }
        ]
    }
    parsed = parse_bundle(valid_bundle)
    assert len(parsed.scatters) == 1
    assert [subset.name for subset in parsed.scatters[0].subsets] == ["a", "b"]


@pytest.mark.parametrize("axis", ["x", "1", "2"])
def test_scatter_rejects_noncanonical_axis_order(valid_study, vocabulary, axis):
    study = scatter_study(valid_study)
    study.scatters[0].subsets[0].dimensions[0].dimension = axis
    with pytest.raises(StudyValidationError, match="dimension"):
        prepare_study(study, vocabulary)
