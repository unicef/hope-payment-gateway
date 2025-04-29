import io
from unittest.mock import patch

import pytest

from hope_payment_gateway.libs.ftp import FTPClient


@pytest.fixture
def mock_sftp_client():
    with patch("paramiko.Transport"), patch("paramiko.SFTPClient") as mock_sftp:
        sftp_instance = mock_sftp.from_transport.return_value

        yield sftp_instance


@pytest.fixture
def ftp_client(mock_sftp_client):
    return FTPClient()


def test_disconnect(ftp_client, mock_sftp_client):
    ftp_client.disconnect()
    mock_sftp_client.close.assert_called_once()


def test_ls(ftp_client, mock_sftp_client):
    expected_files = ["file1.txt", "file2.txt"]
    mock_sftp_client.listdir.return_value = expected_files

    result = ftp_client.ls()

    assert result == expected_files
    mock_sftp_client.listdir.assert_called_once()


def test_get_existing_file(ftp_client, mock_sftp_client):
    filename = "test.txt"
    local_folder = "/tmp"
    expected_path = f"{local_folder.rstrip('/')}/{filename}"

    ftp_client.get(filename, local_folder)

    mock_sftp_client.get.assert_called_once_with(filename, expected_path)


def test_get_nonexistent_file(ftp_client, mock_sftp_client, caplog):
    filename = "nonexistent.txt"
    local_folder = "/tmp"

    mock_sftp_client.get.side_effect = FileNotFoundError()

    with caplog.at_level("INFO"):
        ftp_client.get(filename, local_folder)

    assert f"File: {filename} was not found on the source server" in caplog.text

    mock_sftp_client.get.assert_called_once_with(filename, f"{local_folder}/{filename}")


def test_download(ftp_client, mock_sftp_client):
    filename = "test.txt"
    test_data = b"test file content"

    def mock_getfo(remote_path, fl):
        fl.write(test_data)

    mock_sftp_client.getfo.side_effect = mock_getfo

    result = ftp_client.download(filename)

    assert isinstance(result, io.BytesIO)
    assert result.getvalue() == test_data
    mock_sftp_client.getfo.assert_called_once()
