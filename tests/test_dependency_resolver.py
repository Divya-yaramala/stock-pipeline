from ingestion.dependency_resolver import (
    build_dependency_graph,
    find_circular_dependencies,
    topological_sort,
    validate_pipeline_config,
)

SAMPLE_STEPS = [
    {"step_id": "A", "name": "step_a", "depends_on": []},
    {"step_id": "B", "name": "step_b", "depends_on": ["A"]},
    {"step_id": "C", "name": "step_c", "depends_on": ["B"]},
]


def test_build_dependency_graph_structure():
    graph = build_dependency_graph(SAMPLE_STEPS)
    assert isinstance(graph, dict)
    assert "A" in graph
    assert "B" in graph["A"]
    assert "C" in graph["B"]


def test_topological_sort_correct_order():
    graph = build_dependency_graph(SAMPLE_STEPS)
    order = topological_sort(graph)
    assert order.index("A") < order.index("B")
    assert order.index("B") < order.index("C")


def test_find_circular_dependencies_none():
    cycles = find_circular_dependencies(SAMPLE_STEPS)
    assert cycles == []


def test_validate_pipeline_config_valid():
    result = validate_pipeline_config(SAMPLE_STEPS)
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_pipeline_config_missing_dep():
    bad_steps = [
        {"step_id": "X", "name": "step_x", "depends_on": ["NONEXISTENT"]},
    ]
    result = validate_pipeline_config(bad_steps)
    assert result["valid"] is False
    assert len(result["errors"]) > 0
