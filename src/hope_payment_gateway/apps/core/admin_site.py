from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from django.contrib import admin
from django.contrib.admin.apps import AdminConfig as DjangoAdminConfig
from django.db import models
from django.db.models.base import ModelBase
from django.utils.safestring import mark_safe

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from django.db.models import Model
    from django.http import HttpRequest


class PrettyJSONAdminMixin:
    """Show ``JSONField`` values read-only, pretty-printed, without per-field wiring.

    JSON fields are system-managed and are never edited from the admin. This mixin
    excludes every ``JSONField`` from the change form and adds an auto-generated
    read-only display method (``<field>_display``) that pretty-prints the value.
    """

    model: type[Model]

    def _json_field_names(self) -> set[str]:
        return {field.name for field in self.model._meta.fields if isinstance(field, models.JSONField)}

    def _make_json_display(self, field_name: str) -> Callable[[Model], str]:
        def display(obj: Model) -> str:
            value = getattr(obj, field_name, None)
            if value is None:
                return ""
            try:
                formatted = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
            except TypeError, ValueError:
                formatted = str(value)
            safe = formatted.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return mark_safe(f"<pre>{safe}</pre>")  # noqa: S308

        setattr(display, "short_description", field_name.replace("_", " ").title())  # noqa: B010
        return display

    def get_exclude(self, request: HttpRequest, obj: Model | None = None) -> list[str]:
        exclude = list(super().get_exclude(request, obj) or [])  # type: ignore[misc]
        for name in sorted(self._json_field_names()):
            if name not in exclude:
                exclude.append(name)
        return exclude

    def get_readonly_fields(self, request: HttpRequest, obj: Model | None = None) -> list[str]:
        json_names = self._json_field_names()
        readonly = [name for name in super().get_readonly_fields(request, obj) if name not in json_names]  # type: ignore[misc]
        for json_name in sorted(json_names):
            display = f"{json_name}_display"
            if display not in readonly:
                readonly.append(display)
            if not hasattr(self, display):
                setattr(self, display, self._make_json_display(json_name))
        return readonly


def _has_json_field(model: Any) -> bool:
    fields = getattr(getattr(model, "_meta", None), "fields", ())
    return any(isinstance(field, models.JSONField) for field in fields)


class PrettyJSONAdminSite(admin.AdminSite):
    """Admin site that applies :class:`PrettyJSONAdminMixin` by default."""

    def register(
        self,
        model_or_iterable: type[Model] | Iterable[type[Model]],
        admin_class: type[admin.ModelAdmin[Any]] | None = None,
        **options: Any,
    ) -> None:
        registered = [model_or_iterable] if isinstance(model_or_iterable, ModelBase) else list(model_or_iterable)
        if any(_has_json_field(model) for model in registered):
            base = admin_class or admin.ModelAdmin
            admin_class = cast(
                "type[admin.ModelAdmin[Any]]",
                type(base.__name__, (PrettyJSONAdminMixin, base), {"__module__": base.__module__}),
            )
        super().register(model_or_iterable, admin_class, **options)


class AdminConfig(DjangoAdminConfig):
    default_site = "hope_payment_gateway.apps.core.admin_site.PrettyJSONAdminSite"
