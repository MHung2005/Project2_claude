"""
backend/app/repositories/account_repository.py

Tầng truy cập dữ liệu thuần (Redis) cho tài khoản Manager.
Tài khoản Employee được lưu trong EmployeeRepository (gắn vào hash employee:{id}).
"""

from .redis_client import get_redis


class AccountRepository:
    def __init__(self):
        self.redis = get_redis()

    def save_manager(self, username: str, hashed_password: str) -> None:
        self.redis.hset(f"manager:{username}", mapping={
            "username": username.encode(),
            "password": hashed_password.encode(),
            "role":     b"manager",
        })

    def get_manager(self, username: str) -> dict | None:
        key = f"manager:{username}"
        if not self.redis.exists(key):
            return None
        data = self.redis.hgetall(key)
        return {k.decode(): v.decode() for k, v in data.items()}
