from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FSPClient(ABC):
    """Abstract base class for Financial Service Provider API clients.

    Defines the interface that all FSP integrations must implement.
    Subclasses must implement ``create_transaction`` and ``status``.
    """

    @abstractmethod
    def create_transaction(self, base_payload: dict[str, Any], update: bool = True) -> Any:
        """Create a transaction with the FSP."""

    @abstractmethod
    def status(self, transaction_id: str, update: bool = False) -> Any:
        """Query the status of a transaction from the FSP."""

    def status_update(self, transaction_id: str, update: bool = True) -> Any:
        """Query and update the status of a transaction."""
        return self.status(transaction_id, update=update)

    def refund(self, transaction_id: str, base_payload: dict[str, Any]) -> Any:
        """Refund a transaction. Override in subclass if supported."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support refunds")
