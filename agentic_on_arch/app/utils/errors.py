"""Unified exception handling."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: int = 400, detail: str = None):
        self.message = message
        self.code = code
        self.detail = detail


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, code=404)


class AuthError(AppError):
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, code=403)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.code,
            content={"success": False, "message": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "服务器内部错误"},
        )
