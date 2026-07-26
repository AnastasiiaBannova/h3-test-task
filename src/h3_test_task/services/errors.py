from h3_test_task.core.errors import BaseError


class InvalidHexIdxError(BaseError):
    message = "Invalid hex index"


class InvalidResolutionError(BaseError):
    message = "Invalid resolution"


class InvalidBorderError(BaseError):
    message = "Invalid border"
