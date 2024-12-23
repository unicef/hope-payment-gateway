import io
import logging

from django.conf import settings

import paramiko

logger = logging.getLogger(__name__)


class FTPClient:
    client = None

    def __init__(self):
        transport = paramiko.Transport((settings.FTP_WESTERN_UNION_SERVER, settings.FTP_WESTERN_UNION_PORT))
        transport.connect(
            username=settings.FTP_WESTERN_UNION_USERNAME,
            password=settings.FTP_WESTERN_UNION_PASSWORD,
        )
        self.client = paramiko.SFTPClient.from_transport(transport)

    def disconnect(self):
        self.client.close()

    def ls(self):
        return self.client.listdir()

    def get(self, filename, local_folder="/"):
        local_file_path = f"{local_folder}/{filename}"
        try:
            self.client.get(filename, local_file_path)
        except FileNotFoundError:
            logger.info(f"File: {filename} was not found on the source server")

    def download(self, filename):
        fl = io.BytesIO()
        self.client.getfo(filename, fl)
        fl.seek(0)
        return fl
