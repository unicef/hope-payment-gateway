class FSPError(Exception):
    """Base exception for all FSP-related errors."""


class InvalidCorridorError(FSPError):
    """Raised when a payment corridor (country/currency pair) is not supported."""


class PayloadError(FSPError):
    """Raised when a payload fails validation before sending to the FSP."""


class PayloadMissingKeyError(PayloadError):
    """Raised when a required key is missing from the payment payload."""


class MissingValueInCorridorError(PayloadError):
    """Raised when a required value is missing from the corridor configuration."""


class InvalidChoiceFromCorridorError(PayloadError):
    """Raised when an invalid choice is provided for a corridor field."""


class PayloadIncompatibleError(PayloadError):
    """Raised when the payload is incompatible with the selected FSP/corridor."""


class TokenError(FSPError):
    """Raised when there is an authentication/token issue with the FSP API."""


class InvalidTokenError(TokenError):
    """Raised when the API token is invalid or rejected by the FSP."""


class ExpiredTokenError(TokenError):
    """Raised when the API token has expired."""


class InvalidRequestError(FSPError):
    """Raised when the FSP API rejects the request as invalid."""


class PotentialDuplicateError(FSPError):
    """Raised when a transaction may already exist (duplicate detection)."""  # noqa: E501
