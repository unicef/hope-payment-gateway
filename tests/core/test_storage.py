from django.core.files.base import ContentFile

import pytest

from hope_payment_gateway.apps.core.storage import DataSetStorage, MediaStorage, StaticStorage


@pytest.fixture
def data_set_storage(tmp_path):
    return DataSetStorage(location=str(tmp_path))


def test_available_name_with_existing_file(data_set_storage):
    """
    We test to see if a file can be created and deleted
    """
    file_name = "filetest.txt"
    data_set_storage.save(file_name, ContentFile("original content"))
    assert data_set_storage.exists(file_name)
    available_name = data_set_storage.get_available_name(file_name)
    assert available_name == file_name
    assert not data_set_storage.exists(file_name), "The original file should have been deleted"


def test_media_storage_reads_environment_variables(monkeypatch):
    """
    We test to see if it can recognize media variable in environment settings
    """
    monkeypatch.setenv("MEDIA_AZURE_ACCOUNT_NAME", "media_account")
    storage = MediaStorage()
    settings = storage.get_default_settings()

    assert (
        settings["account_name"] == "media_account"
    ), "MediaStorage should override settings based on environment variables"


def test_static_storage_reads_environment_variables(monkeypatch):
    """
    We test to see if it can recognize static variable in environment settings
    """
    monkeypatch.setenv("STATIC_AZURE_ACCOUNT_KEY", "static_key")
    storage = StaticStorage()
    settings = storage.get_default_settings()

    assert (
        settings["account_key"] == "static_key"
    ), "StaticStorage should override settings based on environment variables"
