from enum import Enum, auto, unique
from typing import Any


@unique
class Grant(Enum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[Any]) -> Any:
        return name

    API_READ_ONLY = auto()
    API_PLAN_UPLOAD = auto()
    API_PLAN_MANAGE = auto()

    @property
    def level(self) -> int:
        """Return the privilege level, ordered as declared from lowest to highest."""
        return list(Grant).index(self)

    @classmethod
    def choices(cls) -> tuple[tuple[str, str], ...]:
        return tuple((member.value, member.name.replace("_", " ").title()) for member in cls)
