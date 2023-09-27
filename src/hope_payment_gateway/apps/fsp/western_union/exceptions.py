class InvalidCorridor(BaseException):
    pass


class PayloadException(BaseException):
    pass


class MissingValueInCorridor(PayloadException):
    pass


class InvalidChoiceFromCorridor(PayloadException):
    pass


class PayloadIncompatible(PayloadException):
    pass
