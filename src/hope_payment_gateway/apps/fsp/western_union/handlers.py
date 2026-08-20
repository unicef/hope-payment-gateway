from hope_payment_gateway.apps.gateway.registry import FSPProcessor


class WesternUnionHandler(FSPProcessor):
    """Strategy handler for Western Union FSP integration.

    Registered in the FSP processor registry. Configuration and
    transaction logic live in the Western Union API client.
    """
