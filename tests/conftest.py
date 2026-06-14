import sys
from types import ModuleType
from unittest.mock import MagicMock

# Stub kafka-python before any ingestion modules are imported so that
# tests run without a live Kafka broker installed.
if "kafka" not in sys.modules:
    _kafka_stub = ModuleType("kafka")
    _kafka_stub.KafkaProducer = MagicMock  # type: ignore[attr-defined]
    _kafka_stub.KafkaConsumer = MagicMock  # type: ignore[attr-defined]
    sys.modules["kafka"] = _kafka_stub
