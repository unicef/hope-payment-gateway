import logging

from hope_payment_gateway.apps.core.models import Singleton
from hope_payment_gateway.apps.fsp.client import FSPClient

logger = logging.getLogger(__name__)


class PayloadMissingKeyError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


class ExpiredTokenError(Exception):
    pass


class PalPayClient(FSPClient, metaclass=Singleton):
    def __init__(self):
        pass
