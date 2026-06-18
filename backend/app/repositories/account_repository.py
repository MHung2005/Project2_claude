"""
backend/app/repositories/account_repository.py  (3NF Refactor)

[Entity 6] manager:{username}
    Tài khoản manager — đơn giản, không thay đổi từ thiết kế cũ vì
    manager không có entity Employee tương ứng.

    manager:{username} → { username, password_hash, role='manager' }
"""

from .redis_client import get_redis


class AccountRepository:
    def __init__(self):
        self.redis = get_redis()

    def save_manager(self, username: str, hashed_password: str) -> None:
        self.redis.hset(f"manager:{username}", mapping={
            "username":      username.encode(),
            "password_hash": hashed_password.encode(),
            "role":          b"manager",
        })

    def get_manager(self, username: str) -> dict | None:
        key = f"manager:{username}"
        if not self.redis.exists(key):
            return None
        data = self.redis.hgetall(key)
        decoded = {k.decode(): v.decode() for k, v in data.items()}
        # Normalize: đổi password_hash → password để tương thích verify_password
        decoded["password"] = decoded.pop("password_hash", decoded.get("password", ""))
        return decoded