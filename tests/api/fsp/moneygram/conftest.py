import pytest

from hope_payment_gateway.api.moneygram.client import MoneyGramClient


# MoneyGramClient is a singleton. Reset its instances before and after each test
# to prevent state leakage between tests.
@pytest.fixture(autouse=True)
def _clear_moneygram_singleton():
    MoneyGramClient._instances = {}
    yield
    MoneyGramClient._instances = {}
