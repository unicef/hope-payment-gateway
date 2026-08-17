from __future__ import annotations

from typing import Any


class FSPClient:
    def create_transaction(self, base_payload: dict[str, Any], update: bool = True) -> Any:
        raise NotImplementedError

    def status(self, transaction_id: str, update: bool) -> Any:
        raise NotImplementedError

    def status_update(self, transaction_id: str, update: bool) -> Any:
        raise NotImplementedError

    def refund(self, transaction_id: str, base_payload: dict[str, Any]) -> Any:
        raise NotImplementedError
