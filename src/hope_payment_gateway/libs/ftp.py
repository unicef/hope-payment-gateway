# https://github.com/rajansahu713/Working-with-Python-Libraries/tree/main/SFTP_work

from django.conf import settings

import paramiko


def ls():
    t = paramiko.Transport((settings.FTP_WESTERN_UNION_SERVER, settings.FTP_WESTERN_UNION_PORT))
    t.connect(username=settings.FTP_WESTERN_UNION_USERNAME, password=settings.FTP_WESTERN_UNION_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(t)
    return sftp.listdir()
