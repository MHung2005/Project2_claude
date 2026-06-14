"""
backend/app/api/auth.py

Controller — Authentication:
  - POST /auth/login            (manager)
  - GET  /auth/me                (manager)
  - POST /auth/employee/login    (employee)
"""

from fastapi import APIRouter, Depends

from ..core.response import success_response
from ..core.security import get_current_manager, get_current_employee
from ..schemas.auth_schema import ManagerLoginRequest, EmployeeLoginRequest
from ..services.auth_service import AuthService

auth_router = APIRouter(prefix="/auth", tags=["Auth"])
employee_auth_router = APIRouter(prefix="/auth", tags=["Auth"])

auth_service = AuthService()


# ── MANAGER ──────────────────────────────────────────────────────────────
@auth_router.post("/login")
def login_manager(body: ManagerLoginRequest):
    data = auth_service.login_manager(body.username, body.password)
    return success_response("Đăng nhập thành công", data)


@auth_router.get("/me")
def get_me(current_manager: dict = Depends(get_current_manager)):
    data = auth_service.get_manager_profile(current_manager)
    return success_response("OK", data)


# ── EMPLOYEE ─────────────────────────────────────────────────────────────
@employee_auth_router.post("/employee/login")
def login_employee(body: EmployeeLoginRequest):
    data = auth_service.login_employee(body.username, body.password)
    return success_response("Đăng nhập thành công", data)
