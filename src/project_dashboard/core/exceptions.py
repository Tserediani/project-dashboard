class AppError(Exception):
    """Base Class for all application errors."""


class InvalidTokenError(AppError): ...


class NotFoundError(AppError): ...


class PermissionDeniedError(AppError): ...


class ConflictError(AppError): ...
