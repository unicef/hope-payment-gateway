from hope_payment_gateway.apps.gateway.registry import FSPProcessor


class PalPayHandler(FSPProcessor):
    """Strategy handler for PalPay FSP integration.

    Registered in the FSP processor registry. Configuration and
    transaction logic live in the PalPay API client.
    """
