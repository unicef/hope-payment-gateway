class InvalidCorridorError(BaseException):
    pass


class PayloadException(BaseException):
    pass


class InvalidRequest(BaseException):
    pass


class PayloadMissingKeyError(PayloadException):
    pass


class MissingValueInCorridor(PayloadException):
    pass


class InvalidChoiceFromCorridor(PayloadException):
    pass


class PayloadIncompatible(PayloadException):
    pass
