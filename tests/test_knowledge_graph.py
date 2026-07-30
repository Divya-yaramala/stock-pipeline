import json
from unittest.mock import MagicMock, patch

from ingestion.knowledge_graph import (
    add_entity,
    add_relationship,
    build_stock_knowledge_graph,
    find_connected_entities,
    get_entity_relationships,
)


def _make_s3_mock():
    mock_s3 = MagicMock()
    mock_s3.get_paginator.return_value.paginate.return_value = [{"Contents": []}]
    return mock_s3


def test_add_entity_success():
    with patch("ingestion.knowledge_graph.boto3.client") as mock_client:
        mock_client.return_value = _make_s3_mock()
        result = add_entity("AAPL", "stock", {"name": "Apple"}, "test-bucket")
    assert result is True


def test_add_relationship_returns_id():
    with patch("ingestion.knowledge_graph.boto3.client") as mock_client:
        mock_client.return_value = _make_s3_mock()
        rel_id = add_relationship("AAPL", "Technology", "BELONGS_TO", {}, "test-bucket")
    assert isinstance(rel_id, str)
    assert len(rel_id) > 0


def test_get_entity_relationships_returns_list():
    rel = {
        "relationship_id": "abc123",
        "source_id": "AAPL",
        "target_id": "Technology",
        "relationship_type": "BELONGS_TO",
        "properties": {},
        "created_at": "2026-07-30T00:00:00",
    }
    with patch("ingestion.knowledge_graph.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": "knowledge_graph/relationships/BELONGS_TO/abc123.json"}]}
        ]
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: json.dumps(rel).encode())}
        mock_client.return_value = mock_s3
        result = get_entity_relationships("AAPL", "test-bucket")
    assert isinstance(result, list)


def test_find_connected_entities_returns_list():
    rel = {
        "source_id": "AAPL",
        "target_id": "Technology",
        "relationship_type": "BELONGS_TO",
    }
    with patch("ingestion.knowledge_graph.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": "knowledge_graph/relationships/BELONGS_TO/abc.json"}]}
        ]
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: json.dumps(rel).encode())}
        mock_client.return_value = mock_s3
        result = find_connected_entities("AAPL", "BELONGS_TO", "test-bucket")
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, str)


def test_build_stock_knowledge_graph_structure():
    with patch("ingestion.knowledge_graph.boto3.client") as mock_client:
        mock_client.return_value = _make_s3_mock()
        result = build_stock_knowledge_graph("test-bucket")
    assert isinstance(result, dict)
    assert "entities_created" in result
    assert "relationships_created" in result
    assert result["entities_created"] > 0
