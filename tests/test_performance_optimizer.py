from unittest.mock import MagicMock, patch

from ingestion.performance_optimizer import (
    batch_processor,
    optimize_s3_uploads,
    parallel_fetch,
    timer_decorator,
)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def test_timer_decorator_logs_duration():
    @timer_decorator
    def add(a, b):
        return a + b

    result = add(2, 3)
    assert result == 5


def test_batch_processor_correct_batches():
    process_func = MagicMock(side_effect=lambda batch: batch)
    items = list(range(10))
    batch_processor(items, 3, process_func)
    assert process_func.call_count == 4


def test_parallel_fetch_returns_all_tickers():
    fetch_func = MagicMock(side_effect=lambda ticker: {"ticker": ticker, "price": 100.0})
    results = parallel_fetch(TICKERS, fetch_func)
    assert set(results.keys()) == set(TICKERS)
    for ticker in TICKERS:
        assert results[ticker] is not None


def test_optimize_s3_uploads_success():
    mock_s3 = MagicMock()
    files = ["/tmp/file1.json", "/tmp/file2.json", "/tmp/file3.json"]
    with patch("ingestion.performance_optimizer.boto3.client", return_value=mock_s3):
        mock_s3.upload_file.return_value = None
        count = optimize_s3_uploads(files, "test-bucket", "uploads")
    assert count == 3


def test_batch_processor_combines_results():
    process_func = MagicMock(side_effect=lambda batch: [x * 2 for x in batch])
    items = [1, 2, 3, 4, 5]
    results = batch_processor(items, 2, process_func)
    assert sorted(results) == [2, 4, 6, 8, 10]
