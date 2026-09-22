"""Graph behavior and authoring validation without remote enrichment."""

import pytest


def test_audit_reports_curation_and_unknown_policy(monkeypatch):
    from info_nodes import audit
    from info_nodes.graph import NodeIndex
    from info_nodes.node import InfoNode

    nodes = NodeIndex([InfoNode("review-example", "A curated example.", [])])
    monkeypatch.setattr(audit, "CURATION_REVIEW", {"review-example": "Check identity."})
    issues = audit.audit_nodes(
        nodes, policies={"can_negative": ["missing-measurement"]}
    )
    assert issues == [
        {
            "sid": "missing-measurement",
            "code": "unknown_policy_measurement",
            "message": "can_negative references an unknown measurement name.",
        },
        {
            "sid": "review-example",
            "code": "curation_review",
            "message": "Check identity.",
        },
    ]


def test_index_preserves_children_and_deduplicates_diamond_choices():
    from info_nodes.graph import NodeIndex
    from info_nodes.node import Choice, DType, InfoNode, MeasurementType

    root = MeasurementType("category", "Category.", [], dtype=DType.CATEGORICAL)
    left = InfoNode("left", "Left.", [root.sid])
    right = InfoNode("right", "Right.", [root.sid])
    choice = Choice(
        "answer", description="Answer.", parents=[left.sid, right.sid], name="yes"
    )
    nodes = NodeIndex([root, left, right, choice])
    assert root.serialize(nodes)["children"] == ["left", "right"]
    assert root.serialize(nodes)["measurement_type"]["choices"] == ["answer"]


@pytest.mark.parametrize("problem", ["duplicate", "parent", "cycle"])
def test_index_rejects_invalid_graph(problem):
    from info_nodes.graph import NodeIndex
    from info_nodes.node import InfoNode

    nodes = [InfoNode("root", "Root.", [])]
    if problem == "duplicate":
        nodes.append(InfoNode("root", "Duplicate.", []))
    elif problem == "parent":
        nodes.append(InfoNode("child", "Child.", ["missing"]))
    else:
        nodes[0].parents = ["root"]
    with pytest.raises(ValueError):
        NodeIndex(nodes)


def test_index_builds_relationships_once():
    from info_nodes.graph import NodeIndex
    from info_nodes.node import InfoNode

    class CountedParents(list):
        reads = 0

        def __iter__(self):
            type(self).reads += 1
            return super().__iter__()

        def __contains__(self, value):
            type(self).reads += 1
            return super().__contains__(value)

    nodes = [InfoNode("root", "Root.", [])]
    nodes.extend(InfoNode(f"child-{n}", "Child.", ["root"]) for n in range(100))
    for node in nodes:
        node.parents = CountedParents(node.parents)
    index = NodeIndex(nodes)
    for node in index:
        node.serialize(index)
    assert CountedParents.reads <= 3 * len(nodes)


def test_plain_list_children_reflect_edits():
    from info_nodes.node import InfoNode

    root = InfoNode("root", "Root.", [])
    nodes = [root]
    assert root.children(nodes, force_calculation=False) == []
    child = InfoNode("child", "Child.", [root.sid])
    nodes.append(child)
    assert root.children(nodes, force_calculation=False) == [child]
