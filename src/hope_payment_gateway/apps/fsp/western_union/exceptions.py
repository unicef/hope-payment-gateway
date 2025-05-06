class InvalidCorridorError(Exception):
    pass


class PayloadError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


class PayloadMissingKeyError(PayloadError):
    pass


class MissingValueInCorridorError(PayloadError):
    pass


class InvalidChoiceFromCorridorError(PayloadError):
    pass


class PayloadIncompatibleError(PayloadError):
    pass
