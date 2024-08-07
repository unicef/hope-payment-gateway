import os
from typing import Any

from django.core.files.storage import FileSystemStorage

from storages.backends.azure_storage import AzureStorage


class DataSetStorage(FileSystemStorage):
    def get_available_name(self, name: str, max_length: int | None = None) -> str:
        if self.exists(name):
            self.delete(name)
        return name

    def save(self, name: str, content: Any, max_length: int | None = None) -> None:
        raise RuntimeError("This storage cannot save files")

    def delete(self, name: str) -> None:
        raise RuntimeError("This storage cannot delete files")

    def open(self, name: str, mode: str = "rb") -> Any:
        if "w" in mode:
            raise RuntimeError("This storage cannot open files in write mode")
        return super().open(name, mode="rb")


class SettingsStorage(AzureStorage):
    prefix = ""

    def get_default_settings(self):
        base = super().get_default_settings()
        for k, _ in base.items():
            if value := os.getenv(f"{self.prefix}_AZURE_{k.upper()}", None):
                base[k] = value
        return base


class UniqueStorageMixin:
    def get_available_name(self, name: str, max_length: int | None = None) -> str:
        if self.exists(name):
            self.delete(name)
        return name


class MediaStorage(UniqueStorageMixin, SettingsStorage):
    prefix = "MEDIA"


class StaticStorage(UniqueStorageMixin, SettingsStorage):
    prefix = "STATIC"
