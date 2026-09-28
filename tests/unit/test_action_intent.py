
import pytest

from app.core.action_intent import is_advice_request


@pytest.mark.parametrize(
    "query",
    [
        "Should I rerun customer_ingestion?",
        "Should we restart the failed pipeline?",
        "Do I need to rerun customer_ingestion?",
        "Is it safe to rerun customer_ingestion?",
        "What happens if I restart the pipeline?",
    ],
)
def test_advice_requests(query):
    assert is_advice_request(query) is True


@pytest.mark.parametrize(
    "query",
    [
        "Rerun customer_ingestion.",
        "Request a rerun of customer_ingestion.",
        "Restart the failed pipeline.",
        "Please rerun customer_ingestion.",
    ],
)
def test_explicit_action_requests(query):
    assert is_advice_request(query) is False