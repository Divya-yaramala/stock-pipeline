import json
from unittest.mock import MagicMock, patch

from ingestion.semantic_search import (
    build_search_index,
    recommend_related_modules,
    search_documents,
)

_SAMPLE_DOCS = [
    {"id": "doc1", "text": "anomaly detection isolation forest score", "metadata": {}},
    {"id": "doc2", "text": "price prediction prophet forecast confidence", "metadata": {}},
    {"id": "doc3", "text": "data quality validation completeness schema", "metadata": {}},
]

_SAMPLE_INDEX = {
    "anomaly": ["doc1"],
    "detection": ["doc1"],
    "isolation": ["doc1"],
    "forest": ["doc1"],
    "price": ["doc2"],
    "prediction": ["doc2"],
    "prophet": ["doc2"],
    "data": ["doc3"],
    "quality": ["doc3"],
}


def test_build_search_index_structure():
    with patch("ingestion.semantic_search.boto3.client") as mock_client:
        mock_client.return_value = MagicMock()
        result = build_search_index(_SAMPLE_DOCS, "test-bucket")
    assert isinstance(result, dict)
    assert "indexed_documents" in result
    assert result["indexed_documents"] == 3


def test_search_documents_returns_list():
    with patch("ingestion.semantic_search.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(_SAMPLE_INDEX).encode())
        }
        mock_client.return_value = mock_s3
        result = search_documents("anomaly detection", "test-bucket")
    assert isinstance(result, list)


def test_search_documents_top_k():
    with patch("ingestion.semantic_search.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(_SAMPLE_INDEX).encode())
        }
        mock_client.return_value = mock_s3
        result = search_documents("anomaly detection quality", "test-bucket", top_k=2)
    assert len(result) <= 2


def test_recommend_related_modules_returns_list():
    index = {
        "anomaly": ["module-anomaly-detector", "module-drift-detector"],
        "detection": ["module-anomaly-detector"],
        "quality": ["module-data-validator"],
    }
    with patch("ingestion.semantic_search.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(index).encode())
        }
        mock_client.return_value = mock_s3
        result = recommend_related_modules("anomaly_detector", "test-bucket")
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, str)


def test_build_search_index_unique_terms():
    docs = [
        {"id": "a", "text": "apple banana cherry", "metadata": {}},
        {"id": "b", "text": "apple date elderberry", "metadata": {}},
    ]
    with patch("ingestion.semantic_search.boto3.client") as mock_client:
        mock_client.return_value = MagicMock()
        result = build_search_index(docs, "test-bucket")
    assert result["unique_terms"] == 5
