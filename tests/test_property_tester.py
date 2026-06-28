from ingestion.property_tester import (
    generate_edge_case_events,
    generate_random_stock_event,
    run_property_tests,
)


def test_generate_random_stock_event_valid():
    event = generate_random_stock_event()
    assert "crypto_id" in event
    assert "price_usd" in event
    assert "timestamp" in event


def test_generate_edge_case_events_count():
    events = generate_edge_case_events()
    assert len(events) == 7


def test_run_property_tests_structure():
    def always_passes(event):
        pass

    result = run_property_tests(always_passes, num_samples=10)
    assert "passed" in result
    assert "failed" in result
    assert "pass_rate" in result


def test_property_tests_catch_failures():
    def always_fails(event):
        raise AssertionError("always fails")

    result = run_property_tests(always_fails, num_samples=5)
    assert result["failed"] == 5


def test_edge_cases_have_boundary_values():
    events = generate_edge_case_events()
    prices = [e["price_usd"] for e in events]
    assert 0.0001 in prices
    assert 999999.99 in prices
