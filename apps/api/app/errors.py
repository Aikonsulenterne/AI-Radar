"""Standardiseret error schema for API'et (Technical Master §11)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class ApiError(Exception):
    """Domænefejl med sikker, brugerrettet besked (aldrig tokens/interne detaljer)."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Ukendte fejl svares som JSON med CORS-header, så frontenden kan vise
        # "Serverfejl" i stedet for at tro, at API'et ikke kan nås. Detaljer
        # står kun i loggen (sammen med request-id).
        import logging

        from app.config import get_settings
        from app.context import request_id_var

        request_id = request_id_var.get() or request.headers.get("x-request-id") or "ukendt"
        logging.getLogger("ai_radar.http").exception(
            "unhandled_error path=%s request_id=%s", request.url.path, request_id
        )
        response = _error_response(
            500,
            "server_error",
            f"Uventet serverfejl ({exc.__class__.__name__}). Request-id {request_id} "
            "står i API-loggen.",
        )
        origin = request.headers.get("origin")
        if origin and origin in get_settings().cors_origin_list:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        return response

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(422, "validation_error", "Ugyldigt input i request.")
