"""
backend/app/__init__.py

App factory. Hệ thống có 2 vai trò: employee và manager — không có
public/guest access.

Tất cả response (thành công & lỗi) đều theo format chuẩn:
{
  "success": true/false,
  "message": "...",
  "data": {} | [] | null
}
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.exception_handlers import register_exception_handlers
from .core.response import success_response

from .repositories.account_repository import AccountRepository
from .core.security import hash_password


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # ── Routers ──────────────────────────────────────────────────
    from .api.auth import auth_router, employee_auth_router
    from .api.manager import manager_router
    from .api.employee import employee_router

    app.include_router(auth_router)           # /auth/login, /auth/me
    app.include_router(employee_auth_router)  # /auth/employee/login
    app.include_router(manager_router)        # /manager/*
    app.include_router(employee_router)       # /employee/*

    #── Khởi tạo tài khoản admin nếu chưa có ───────────────────────────────
    account_repo = AccountRepository()
    if not account_repo.get_manager("admin"):
        account_repo.save_manager("admin", hash_password("admin123"))

    @app.get("/health", tags=["System"])
    def health():
        return success_response("Service is healthy", {"status": "ok"})

    return app
