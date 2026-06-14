"""
backend/app/core/exception_handlers.py

Đăng ký global exception handlers để mọi lỗi (kể cả lỗi không lường trước)
đều trả về unified response format.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from .response import AppException, error_response


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return error_response(message=exc.message, data=exc.data, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return error_response(
            message="Dữ liệu đầu vào không hợp lệ",
            data=exc.errors(),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return error_response(
            message=f"Lỗi hệ thống: {exc}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
