"""
backend/app/core/response.py

Chuẩn hóa response trả về cho TOÀN BỘ API.
Mọi response đều có dạng:
{
  "success": true/false,
  "message": "...",
  "data": {} | [] | null
}
"""

from typing import Any, Optional
from fastapi.responses import JSONResponse
from fastapi import status


def success_response(message: str = "OK", data: Any = None,
                      status_code: int = status.HTTP_200_OK) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "message": message, "data": data},
    )


def error_response(message: str = "Đã xảy ra lỗi", data: Any = None,
                    status_code: int = status.HTTP_400_BAD_REQUEST) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "data": data},
    )


class AppException(Exception):
    """
    Exception nghiệp vụ chuẩn hóa — được AppExceptionHandler bắt và
    chuyển thành unified JSON response.
    """
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST,
                 data: Any = None):
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)


# ── Các exception nghiệp vụ thường gặp (tiện dùng) ─────────────────────────
class NotFoundException(AppException):
    def __init__(self, message: str = "Không tìm thấy dữ liệu", data: Any = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, data)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Không có quyền truy cập", data: Any = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, data)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Không có quyền thực hiện hành động này", data: Any = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, data)


class ConflictException(AppException):
    def __init__(self, message: str = "Dữ liệu bị xung đột", data: Any = None):
        super().__init__(message, status.HTTP_409_CONFLICT, data)


class ValidationException(AppException):
    def __init__(self, message: str = "Dữ liệu không hợp lệ", data: Any = None):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, data)
