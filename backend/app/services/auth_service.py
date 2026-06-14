"""
backend/app/services/auth_service.py

Business logic cho đăng nhập (Manager & Employee).
"""

from ..core.security import verify_password, create_token
from ..core.response import UnauthorizedException
from ..repositories.account_repository import AccountRepository
from ..repositories.employee_repository import EmployeeRepository


class AuthService:
    def __init__(self):
        self.account_repo = AccountRepository()
        self.employee_repo = EmployeeRepository()

    # ── MANAGER ──────────────────────────────────────────────────────
    def login_manager(self, username: str, password: str) -> dict:
        manager = self.account_repo.get_manager(username)
        if not manager:
            raise UnauthorizedException("Tài khoản không tồn tại")
        if not verify_password(password, manager["password"]):
            raise UnauthorizedException("Sai mật khẩu")

        token = create_token({"username": manager["username"], "role": "manager"})
        return {
            "access_token": token,
            "token_type":   "bearer",
            "username":     manager["username"],
            "role":         "manager",
        }

    def get_manager_profile(self, payload: dict) -> dict:
        return {"username": payload["username"], "role": payload["role"]}

    # ── EMPLOYEE ─────────────────────────────────────────────────────
    def login_employee(self, username: str, password: str) -> dict:
        account = self.employee_repo.get_login_account(username)
        if not account:
            raise UnauthorizedException("Tài khoản không tồn tại")
        if not verify_password(password, account["password"]):
            raise UnauthorizedException("Sai mật khẩu")

        token = create_token({
            "username": account["username"],
            "user_id":  account["user_id"],
            "role":     "employee",
        })
        return {
            "access_token": token,
            "token_type":   "bearer",
            "username":     account["username"],
            "user_id":      account["user_id"],
            "role":         "employee",
        }
