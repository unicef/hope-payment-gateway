from hope_payment_gateway.apps.gateway.registry import FSPProcessor


class WesternUnionHandler(FSPProcessor):
    pass


class CSVExportStrategy(FSPProcessor):
    def export(self) -> None:
        pass
