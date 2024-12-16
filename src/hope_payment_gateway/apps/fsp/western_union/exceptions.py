class InvalidCorridor(BaseException):
    pass


class PayloadException(BaseException):
    pass


class InvalidRequest(BaseException):
    pass


class PayloadMissingKey(PayloadException):
    pass


class MissingValueInCorridor(PayloadException):
    pass


class InvalidChoiceFromCorridor(PayloadException):
    pass


class PayloadIncompatible(PayloadException):
    pass
