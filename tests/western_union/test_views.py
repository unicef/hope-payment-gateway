import io
from unittest.mock import patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
@patch("hope_payment_gateway.api.western_union.views.FTPClient")
def test_api_wu_file_list(mock_ftp_client_class, api_client, admin_user):
    file_names = ["file_number_1.txt", "file_number_2.txt"]
    mock_instance = mock_ftp_client_class.return_value
    mock_instance.ls.return_value = file_names

    api_client.force_authenticate(user=admin_user)
    url = reverse("api:wu-files-list")

    view = api_client.get(url, user=admin_user, expect_errors=True)
    assert view.status_code == 200
    assert isinstance(view.json(), list)

    for index, name in enumerate(file_names):
        _obj = view.json()[index]
        assert name == _obj.get("name")
        assert f"http://testserver{url}{name}" == _obj.get("url")


@pytest.mark.django_db
@patch("hope_payment_gateway.api.western_union.views.FTPClient")
def test_api_wu_file_download(mock_ftp_client_class, api_client, admin_user):
    mock_file_content = b"test file content for testing purposes"
    moke_file = io.BytesIO(mock_file_content)
    mock_instance = mock_ftp_client_class.return_value
    mock_instance.download.return_value = moke_file

    api_client.force_authenticate(user=admin_user)
    file_name = "should_exist.txt"
    url = reverse("api:wu-files-detail", kwargs={"filename": file_name})

    view = api_client.get(url, user=admin_user, expect_errors=True)

    assert view.status_code == 200
    assert view.headers.get("Content-Disposition") == f'attachment; filename="{file_name}"'


@pytest.mark.django_db
@patch("hope_payment_gateway.api.western_union.views.FTPClient")
def test_api_wu_file_download_fail(mock_ftp_client_class, api_client, admin_user):
    mock_instance = mock_ftp_client_class.return_value
    mock_instance.download.side_effect = FileNotFoundError()

    api_client.force_authenticate(user=admin_user)
    url = reverse("api:wu-files-detail", kwargs={"filename": "should_not_exist.txt"})

    view = api_client.get(url, user=admin_user, expect_errors=True)
    assert view.status_code == 404
