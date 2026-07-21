from unittest.mock import MagicMock, patch

from ingestion.distributed_task_manager import (
    chunk_list,
    run_batch_s3_uploads,
    run_parallel_tasks,
    run_parallel_ticker_processing,
)


def test_run_parallel_tasks_all_succeed():
    tasks = [
        {"name": "task1", "func": lambda: 1, "args": (), "kwargs": {}},
        {"name": "task2", "func": lambda: 2, "args": (), "kwargs": {}},
        {"name": "task3", "func": lambda: 3, "args": (), "kwargs": {}},
    ]
    results = run_parallel_tasks(tasks, max_workers=3)
    statuses = [str(r["status"]) for r in results]
    assert all(s == "success" for s in statuses)


def test_run_parallel_tasks_returns_all():
    tasks = [{"name": f"task{i}", "func": lambda: i, "args": (), "kwargs": {}} for i in range(5)]
    results = run_parallel_tasks(tasks, max_workers=5)
    assert len(results) == 5


def test_chunk_list_correct_size():
    items = list(range(10))
    chunks = chunk_list(items, chunk_size=3)
    assert len(chunks) == 4


def test_run_batch_s3_uploads_structure():
    files = [
        {"key": "test/file1.json", "data": {"value": 1}},
        {"key": "test/file2.json", "data": {"value": 2}},
    ]
    with patch("ingestion.distributed_task_manager.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        result = run_batch_s3_uploads(files, bucket="test-bucket", max_workers=2)
    assert "uploaded" in result
    assert "failed" in result
    assert "total_seconds" in result


def test_run_parallel_ticker_processing_structure():
    def mock_process(ticker, **kwargs):
        return {"ticker": ticker, "done": True}

    result = run_parallel_ticker_processing(
        ["AAPL", "MSFT", "GOOGL"],
        mock_process,
        max_workers=3,
    )
    assert "success_count" in result
    assert "failed_count" in result
    assert result["success_count"] == 3
