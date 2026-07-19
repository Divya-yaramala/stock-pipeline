# Testing Guide — Stock Pipeline

## Testing Philosophy
Four-tier testing strategy ensures comprehensive coverage:

| Tier | Tool | Location | Purpose |
|---|---|---|---|
| Unit | pytest | tests/ | Test individual functions |
| Integration | pytest | tests/integration/ | Test module interactions |
| E2E | pytest + TestClient | tests/e2e/ | Test full API contracts |
| Performance | benchmarker | - | Latency + throughput |

## Running Tests

### All Tests
```bash
pytest tests/ tests/integration/ tests/e2e/ -v
```

### With Coverage Report
```bash
pytest tests/ --cov=ingestion --cov-report=html --cov-report=term-missing
start htmlcov/index.html  # Windows
```

### Unit Tests Only
```bash
pytest tests/ -v
```

### Integration Tests Only
```bash
pytest tests/integration/ -v
```

### E2E Tests Only
```bash
pytest tests/e2e/ -v
```

### Single Test File
```bash
pytest tests/test_anomaly_detector.py -v
```

### Single Test Function
```bash
pytest tests/test_anomaly_detector.py::test_detect_anomaly_valid -v
```

## Coverage Thresholds
| Module Category | Target Coverage |
|---|---|
| ingestion/ core modules | > 90% |
| ingestion/ utility modules | > 80% |
| api/ endpoints | > 85% |
| scripts/ | > 70% |

## Writing Good Tests

### Unit Test Template
```python
def test_function_name_scenario():
    # Arrange
    input_data = {"ticker": "AAPL", "price": 185.0}
    expected = {"valid": True}

    # Act
    result = your_function(input_data)

    # Assert
    assert result["valid"] == expected["valid"]
```

### Mocking S3 Template
```python
from unittest.mock import patch, MagicMock

def test_s3_function():
    with patch("ingestion.your_module.boto3.client") as mock_s3:
        mock_s3.return_value.put_object.return_value = {}
        result = your_s3_function("bucket", "key", data)
        assert result is True
```

### Mocking Optional Parameters
```python
from typing import Optional

def your_function(param: Optional[str] = None) -> dict:
    pass
```

## Performance Benchmarks
Run benchmarks to detect regressions:
```bash
python -c "from ingestion.performance_benchmarker import run_benchmark_suite; import os; print(run_benchmark_suite(os.getenv('AWS_BUCKET_NAME')))"
```

Regression threshold: >20% slower than baseline = regression
