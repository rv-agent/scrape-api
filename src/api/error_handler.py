"""
Global error handling middleware for ScrapeAPI.

Provides structured error responses and hides stack traces in production.
"""

import logging
import traceback
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.validation import ValidationError
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Structured error response builder."""

    @staticmethod
    def build(
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> JSONResponse:
        """
        Build a structured JSON error response.

        Args:
            code: Machine-readable error code
            message: Human-readable error message
            status_code: HTTP status code
            details: Additional error details (hidden in production)
            request_id: Request correlation ID

        Returns:
            JSONResponse with structured error body
        """
        body: Dict[str, Any] = {
            "error": {
                "code": code,
                "message": message,
            }
        }

        # Include details only in development
        if details and settings.DEBUG:
            body["error"]["details"] = details

        if request_id:
            body["error"]["request_id"] = request_id

        return JSONResponse(
            status_code=status_code,
            content=body,
        )


def register_error_handlers(app: FastAPI) -> None:
    """
    Register global error handlers on the FastAPI app.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """Handle custom validation errors."""
        logger.warning("Validation error: %s — %s", exc.code, exc.message)
        return ErrorResponse.build(
            code=exc.code,
            message=exc.message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def pydantic_validation_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic request validation errors."""
        errors = exc.errors()
        logger.warning("Request validation failed: %d errors", len(errors))

        # Simplify error messages for API consumers
        simplified = []
        for err in errors:
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            simplified.append({
                "field": loc,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "validation_error"),
            })

        return ErrorResponse.build(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": simplified} if settings.DEBUG else None,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions with structured response."""
        # Map common status codes to error codes
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            429: "RATE_LIMITED",
            500: "INTERNAL_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE",
        }

        error_code = code_map.get(exc.status_code, "HTTP_ERROR")
        message = str(exc.detail) if exc.detail else "An error occurred"

        return ErrorResponse.build(
            code=error_code,
            message=message,
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions — hide details in production."""
        # Always log full traceback
        logger.exception("Unhandled exception: %s", str(exc))

        if settings.DEBUG:
            return ErrorResponse.build(
                code="INTERNAL_ERROR",
                message=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={
                    "type": type(exc).__name__,
                    "traceback": traceback.format_exc().split("\n"),
                },
            )

        # Production: generic message, no stack trace
        return ErrorResponse.build(
            code="INTERNAL_ERROR",
            message="An internal error occurred. Please try again later.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
