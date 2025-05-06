class InvalidCorridorError(Exception):
    pass


class PayloadError(Exception):
    pass


class PayloadMissingKeyError(PayloadError):
    pass


class MissingValueInCorridorError(PayloadError):
    pass


class InvalidChoiceFromCorridorError(PayloadError):
    pass


class PayloadIncompatibleError(PayloadError):
    pass


class TokenError(Exception):
    pass


class InvalidTokenError(TokenError):
    pass


class ExpiredTokenError(TokenError):
    pass


class InvalidRequestError(Exception):
    pass
