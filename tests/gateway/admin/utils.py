from collections.abc import Callable

from admin_extra_buttons.buttons import Button, ChoiceButton
from admin_extra_buttons.handlers import ViewHandler
from django.db.models import Model
from django.test.utils import ContextList
from pytest import fail


def find_button(context: ContextList, label: str) -> Button | None:
    for button in context.get("buttons"):
        if button.label == label:
            return button


def assert_has_expected_choices(button: ChoiceButton, *expected_handlers: Callable) -> None:
    if (handlers := set(expected_handlers)) != (choices := set(button.choices)):
        fail(f"Handlers do not match, check following names: {handlers.symmetric_difference(choices)}")


def get_change_model_url(model: type[Model]) -> str:
    return f"admin:{model._meta.app_label}_{model._meta.model_name}_change"


def get_change_model_list_url(model: type[Model]) -> str:
    return f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"


def get_view_handler_url(model: type[Model], handler: ViewHandler) -> str:
    return f"admin:{model._meta.app_label}_{model._meta.model_name}_{handler.name}"
