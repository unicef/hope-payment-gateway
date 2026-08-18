import pytest

from hope_payment_gateway.api.moneygram.client import MoneyGramClient


@pytest.fixture(autouse=True)
def _clear_moneygram_singleton():
    MoneyGramClient._instances = {}
    yield
    MoneyGramClient._instances = {}
