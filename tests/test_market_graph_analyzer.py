import pytest  # noqa: F401

from ingestion.market_graph_analyzer import (
    build_correlation_graph,
    calculate_market_stability,
    calculate_node_centrality,
    detect_market_leader,
)


def test_build_correlation_graph_structure():
    matrix = {
        "AAPL": {"AAPL": 1.0, "MSFT": 0.85, "TSLA": 0.4},
        "MSFT": {"AAPL": 0.85, "MSFT": 1.0, "TSLA": 0.5},
        "TSLA": {"AAPL": 0.4, "MSFT": 0.5, "TSLA": 1.0},
    }
    result = build_correlation_graph(matrix)
    assert "nodes" in result
    assert "edges" in result
    assert "edge_count" in result


def test_build_correlation_graph_threshold():
    matrix = {
        "AAPL": {"AAPL": 1.0, "MSFT": 0.9, "TSLA": 0.3},
        "MSFT": {"AAPL": 0.9, "MSFT": 1.0, "TSLA": 0.2},
        "TSLA": {"AAPL": 0.3, "MSFT": 0.2, "TSLA": 1.0},
    }
    result = build_correlation_graph(matrix, threshold=0.7)
    assert result["edge_count"] == 1
    edge = result["edges"][0]
    assert set([edge["source"], edge["target"]]) == {"AAPL", "MSFT"}


def test_calculate_node_centrality_structure():
    graph = {
        "nodes": ["AAPL", "MSFT", "GOOGL"],
        "edges": [
            {"source": "AAPL", "target": "MSFT", "weight": 0.85},
            {"source": "AAPL", "target": "GOOGL", "weight": 0.75},
        ],
    }
    result = calculate_node_centrality(graph)
    assert isinstance(result, dict)
    assert "AAPL" in result
    assert "MSFT" in result


def test_calculate_market_stability_low():
    graph = {
        "nodes": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
        "edges": [{"source": "AAPL", "target": "MSFT", "weight": 0.8}],
    }
    result = calculate_market_stability(graph)
    assert result["risk_level"] == "low"
    assert result["stability"] == "stable"


def test_detect_market_leader_returns_ticker():
    graph = {"nodes": ["AAPL", "MSFT", "GOOGL"], "edges": []}
    centrality = {"AAPL": 0.8, "MSFT": 0.5, "GOOGL": 0.3}
    leader = detect_market_leader(graph, centrality)
    assert leader == "AAPL"
    assert isinstance(leader, str)
