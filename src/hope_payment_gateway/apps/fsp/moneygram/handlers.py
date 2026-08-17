from hope_payment_gateway.apps.gateway.registry import FSPProcessor


class MoneyGramHandler(FSPProcessor):
    """Strategy handler for MoneyGram FSP integration.

    Registered in the FSP processor registry. Configuration and
    transaction logic live in the MoneyGram API client.
    """
