import datetime
import json
import logging
import math
import os  # noqa: F401
from typing import Any, Dict, List, Optional, Tuple  # noqa: F401

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_correlation_graph(
    correlation_matrix: Dict[str, Dict[str, float]],
    threshold: float = 0.7,
) -> Dict[str, Any]:
    nodes: List[str] = list(correlation_matrix.keys())
    edges: List[Dict[str, Any]] = []
    seen: set = set()
    for source in nodes:
        for target, weight in correlation_matrix[source].items():
            if source == target:
                continue
            pair = tuple(sorted([source, target]))
            if pair in seen:
                continue
            seen.add(pair)
            if float(str(weight)) >= threshold:
                edges.append(
                    {
                        "source": str(source),
                        "target": str(target),
                        "weight": round(float(str(weight)), 4),
                    }
                )
    result: Dict[str, Any] = {
        "nodes": nodes,
        "edges": edges,
        "edge_count": len(edges),
    }
    logger.info("Graph built: %d nodes, %d edges", len(nodes), len(edges))
    return result


def calculate_node_centrality(graph: Dict[str, Any]) -> Dict[str, float]:
    nodes: List[str] = graph["nodes"]
    edges: List[Dict[str, Any]] = graph["edges"]
    n = len(nodes)
    if n <= 1:
        return {node: 0.0 for node in nodes}

    degree: Dict[str, int] = {node: 0 for node in nodes}
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        if source in degree:
            degree[source] += 1
        if target in degree:
            degree[target] += 1

    centrality: Dict[str, float] = {
        node: round(float(degree[node]) / float(n - 1), 4) for node in nodes
    }
    if centrality:
        leader = max(centrality, key=lambda k: centrality[k])
        logger.info("Most central ticker: %s (%.4f)", leader, centrality[leader])
    return centrality


def find_market_clusters(graph: Dict[str, Any]) -> List[List[str]]:
    nodes: List[str] = graph["nodes"]
    edges: List[Dict[str, Any]] = graph["edges"]

    adjacency: Dict[str, List[str]] = {node: [] for node in nodes}
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        if source in adjacency:
            adjacency[source].append(target)
        if target in adjacency:
            adjacency[target].append(source)

    visited: set = set()
    clusters: List[List[str]] = []

    for node in nodes:
        if node in visited:
            continue
        cluster: List[str] = []
        stack = [node]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            cluster.append(current)
            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    stack.append(neighbor)
        clusters.append(sorted(cluster))

    sizes = [len(c) for c in clusters]
    logger.info("Clusters found: %d, sizes: %s", len(clusters), sizes)
    return clusters


def detect_market_leader(
    graph: Dict[str, Any],
    centrality: Dict[str, float],
) -> str:
    if not centrality:
        return ""
    leader = max(centrality, key=lambda k: centrality[k])
    logger.info("Market leader identified: %s", leader)
    return leader


def calculate_market_stability(graph: Dict[str, Any]) -> Dict[str, Any]:
    nodes: List[str] = graph["nodes"]
    edges: List[Dict[str, Any]] = graph["edges"]
    n = len(nodes)
    max_edges = float(n * (n - 1)) / 2.0 if n > 1 else 1.0
    density = float(len(edges)) / max_edges if max_edges > 0 else 0.0

    if density < 0.3:
        stability = "stable"
        risk_level = "low"
    elif density < 0.7:
        stability = "moderate"
        risk_level = "medium"
    else:
        stability = "correlated"
        risk_level = "high"

    result: Dict[str, Any] = {
        "density": round(density, 4),
        "stability": stability,
        "risk_level": risk_level,
    }
    logger.info("Market stability: %s (density=%.4f, risk=%s)", stability, density, risk_level)
    return result


def _pearson_correlation(x: List[float], y: List[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den_x = math.sqrt(sum((v - mean_x) ** 2 for v in x))
    den_y = math.sqrt(sum((v - mean_y) ** 2 for v in y))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def run_market_graph_analysis(
    ticker_prices: Dict[str, List[float]],
    bucket: str,
) -> Dict[str, Any]:
    tickers = list(ticker_prices.keys())
    corr_matrix: Dict[str, Dict[str, float]] = {}
    for t1 in tickers:
        corr_matrix[t1] = {}
        for t2 in tickers:
            if t1 == t2:
                corr_matrix[t1][t2] = 1.0
            else:
                p1 = ticker_prices[t1]
                p2 = ticker_prices[t2]
                min_len = min(len(p1), len(p2))
                corr_matrix[t1][t2] = round(_pearson_correlation(p1[:min_len], p2[:min_len]), 4)

    graph = build_correlation_graph(corr_matrix)
    centrality = calculate_node_centrality(graph)
    clusters = find_market_clusters(graph)
    leader = detect_market_leader(graph, centrality)
    stability = calculate_market_stability(graph)

    result: Dict[str, Any] = {
        "tickers": tickers,
        "correlation_matrix": corr_matrix,
        "graph": {"nodes": graph["nodes"], "edge_count": graph["edge_count"]},
        "centrality": centrality,
        "clusters": clusters,
        "leader": leader,
        "stability": stability,
        "analyzed_at": datetime.datetime.utcnow().isoformat(),
    }

    now = datetime.datetime.utcnow()
    s3_key = "processed/graph_analysis/{}/{}/{}/analysis.json".format(
        now.strftime("%Y"),
        now.strftime("%m"),
        now.strftime("%d"),
    )

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(result),
            ContentType="application/json",
        )
        logger.info("Saved graph analysis to s3://%s/%s", bucket, s3_key)
    except Exception as e:
        logger.warning("S3 upload skipped: %s", str(e))

    logger.info("Market Graph Analysis Complete")
    return result


if __name__ == "__main__":
    pass
