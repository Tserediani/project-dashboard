class AppError(Exception):
    """Base Class for all application errors."""


class InvalidTokenError(AppError): ...
