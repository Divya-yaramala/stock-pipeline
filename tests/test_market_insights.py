from unittest.mock import MagicMock, patch

from ingestion.market_insights import (
    build_prompt,
    generate_insight,
    load_todays_data,
    save_insight_to_s3,
)


def _make_sample_data() -> dict:
    return {
        "raw": {
            "Open": {"0": 150.0},
            "High": {"0": 155.0},
            "Low": {"0": 148.0},
            "Close": {"0": 153.0},
            "Volume": {"0": 1_000_000},
        },
        "anomalies": {
            "is_anomaly": {"0": False},
            "anomaly_score": {"0": 0.1},
        },
        "predictions": {
            "ds": {
                "0": "2026-05-17",
                "1": "2026-05-18",
                "2": "2026-05-19",
                "3": "2026-05-20",
                "4": "2026-05-21",
            },
            "yhat": {"0": 154.0, "1": 155.0, "2": 156.0, "3": 157.0, "4": 158.0},
            "yhat_lower": {"0": 149.0, "1": 150.0, "2": 151.0, "3": 152.0, "4": 153.0},
            "yhat_upper": {"0": 159.0, "1": 160.0, "2": 161.0, "3": 162.0, "4": 163.0},
        },
    }


def test_build_prompt_contains_ticker():
    result = build_prompt("AAPL", _make_sample_data())
    assert "AAPL" in result


def test_build_prompt_contains_ohlcv():
    result = build_prompt("AAPL", _make_sample_data())
    assert "150" in result  # Open
    assert "155" in result  # High
    assert "148" in result  # Low
    assert "153" in result  # Close


def test_generate_insight_success():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "AAPL shows strong upward momentum this week."
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("ingestion.market_insights.openai.OpenAI", return_value=mock_client):
        result = generate_insight("test prompt", "AAPL")

    assert result != ""


def test_generate_insight_api_failure():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API connection error")

    with patch("ingestion.market_insights.openai.OpenAI", return_value=mock_client):
        result = generate_insight("test prompt", "AAPL")

    assert result == ""


def test_save_insight_to_s3_success():
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}

    with patch("ingestion.market_insights.boto3.client", return_value=mock_s3):
        result = save_insight_to_s3("Test insight.", "AAPL", "test-bucket", "2026/05/16")

    assert result is True


def test_save_insight_to_s3_failure():
    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = Exception("S3 write error")

    with patch("ingestion.market_insights.boto3.client", return_value=mock_s3):
        result = save_insight_to_s3("Test insight.", "AAPL", "test-bucket", "2026/05/16")

    assert result is False


def test_load_todays_data_missing_file():
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception("NoSuchKey")

    with patch("ingestion.market_insights.boto3.client", return_value=mock_s3):
        result = load_todays_data("AAPL", "test-bucket", "2026/05/16")

    assert result["raw"] is None
    assert result["anomalies"] is None
    assert result["predictions"] is None
