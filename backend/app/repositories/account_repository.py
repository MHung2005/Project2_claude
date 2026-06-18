"""
backend/app/repositories/account_repository.py

[Bảng] managers
    Tài khoản quản lý (manager) — không có entity Employee tương ứng nên
    vẫn là bảng độc lập, giống thiết kế Redis cũ (manager:{username}).
"""

from .db import get_db, get_lock


class AccountRepository:
    def __init__(self):
        self.db = get_db()
        self.lock = get_lock()

    def save_manager(self, username: str, hashed_password: str) -> None:
        with self.lock:
            self.db.execute(
                """
                INSERT INTO managers (username, password_hash, role)
                VALUES (?, ?, 'manager')
                ON CONFLICT(username) DO UPDATE SET
                    password_hash = excluded.password_hash
                """,
                (username, hashed_password),
            )

    def get_manager(self, username: str) -> dict | None:
        with self.lock:
            row = self.db.execute(
                "SELECT username, password_hash, role FROM managers WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        # Giữ tương thích với code cũ: đổi tên password_hash -> password
        data["password"] = data.pop("password_hash")
        return data