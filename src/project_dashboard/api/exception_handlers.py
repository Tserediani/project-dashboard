from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from project_dashboard.core.exceptions import (
    ConflictError,
    InvalidTokenError,
    NotFoundError,
    PayloadTooLargeError,
    PermissionDeniedError,
    UnsupportedDocumentTypeError,
)


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def permission_denied_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


async def invalid_token_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


async def conflict_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def payload_too_large_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=413, content={"detail": str(exc)})


async def unsupported_document_type_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(status_code=415, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(PermissionDeniedError, permission_denied_handler)
    app.add_exception_handler(InvalidTokenError, invalid_token_handler)
    app.add_exception_handler(ConflictError, conflict_handler)
    app.add_exception_handler(PayloadTooLargeError, payload_too_large_handler)
    app.add_exception_handler(
        UnsupportedDocumentTypeError, unsupported_document_type_handler
    )
