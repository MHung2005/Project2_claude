"""
backend/app/repositories/employee_repository.py  (3NF Refactor)

Ba entity riêng biệt, mỗi entity một prefix:

  [Entity 1] employee:{user_id}
      user_id, name, department, position, email, phone
      Chỉ chứa thông tin nhân sự thuần — KHÔNG có password/username/vector

  [Entity 2] account:{user_id}
      user_id, username, password_hash, role
      account_index:{username} → user_id   (lookup ngược)
      Tách biệt xác thực khỏi hồ sơ nhân sự

  [Entity 3] face:{user_id}
      user_id, vector_embedding (BINARY), registered_at
      biometric_status được tính = "approved" nếu key tồn tại, else "none"
      KHÔNG lưu trong employee hash → không còn transitive dependency
"""

from datetime import datetime

import numpy as np

from .redis_client import get_redis

# Các field được phép đọc từ employee hash
EMPLOYEE_TEXT_FIELDS = {"user_id", "name", "department", "position", "email", "phone"}


class EmployeeRepository:
    def __init__(self):
        self.redis = get_redis()

    # ════════════════════════════════════════════════════════════════
    # ENTITY 1 — Employee (hồ sơ nhân sự thuần)
    # ════════════════════════════════════════════════════════════════

    def create_employee(self, user_id: str, fields: dict) -> None:
        """
        Tạo hồ sơ nhân sự. Chỉ lưu các trường nhân sự — không có
        thông tin xác thực hay sinh trắc học.
        """
        mapping = {
            "user_id":    user_id.encode(),
            "name":       fields.get("name", "").encode(),
            "department": fields.get("department", "").encode(),
            "position":   fields.get("position", "").encode(),
            "email":      fields.get("email", "").encode(),
            "phone":      fields.get("phone", "").encode(),
        }
        self.redis.hset(f"employee:{user_id}", mapping=mapping)

    def update_employee(self, user_id: str, name: str, department: str, position: str) -> bool:
        key = f"employee:{user_id}"
        if not self.redis.exists(key):
            return False
        self.redis.hset(key, mapping={
            "name":       name.encode(),
            "department": department.encode(),
            "position":   position.encode(),
        })
        return True

    def delete_employee(self, user_id: str) -> bool:
        """Xóa employee + account + face — cascade."""
        # Lấy username để xóa index ngược
        account = self._get_account_raw(user_id)
        if account:
            username = account.get(b"username", b"").decode()
            if username:
                self.redis.delete(f"account_index:{username}")
        deleted = self.redis.delete(f"employee:{user_id}") > 0
        self.redis.delete(f"account:{user_id}")
        self.redis.delete(f"face:{user_id}")
        return deleted

    def exists(self, user_id: str) -> bool:
        return bool(self.redis.exists(f"employee:{user_id}"))

    def get_raw(self, user_id: str) -> dict:
        """Trả về raw bytes dict của employee hash."""
        return self.redis.hgetall(f"employee:{user_id}")

    def get_employee(self, user_id: str) -> dict | None:
        """Trả về thông tin nhân sự đã decode, kèm biometric_status tính toán."""
        data = self.redis.hgetall(f"employee:{user_id}")
        if not data:
            return None
        decoded = {
            k.decode(): v.decode()
            for k, v in data.items()
            if k.decode() in EMPLOYEE_TEXT_FIELDS
        }
        # biometric_status là derived attribute — tính từ sự tồn tại của face key
        decoded["biometric_status"] = (
            "approved" if self.redis.exists(f"face:{user_id}") else "none"
        )
        return decoded

    def get_all(self) -> list[dict]:
        employees = []
        for key in self.redis.scan_iter("employee:*"):
            try:
                data = self.redis.hgetall(key)
                if not data:
                    continue
                decoded = {}
                for k, v in data.items():
                    field = k.decode() if isinstance(k, bytes) else k
                    if field in EMPLOYEE_TEXT_FIELDS:
                        decoded[field] = v.decode() if isinstance(v, bytes) else v
                if "user_id" not in decoded:
                    continue
                uid = decoded["user_id"]
                decoded["biometric_status"] = (
                    "approved" if self.redis.exists(f"face:{uid}") else "none"
                )
                employees.append(decoded)
            except Exception as e:
                print(f"[EmployeeRepository.get_all] Lỗi key '{key}': {e}")
        return employees

    # ════════════════════════════════════════════════════════════════
    # ENTITY 2 — Account (xác thực — tách biệt khỏi Employee)
    # ════════════════════════════════════════════════════════════════

    def attach_account(self, user_id: str, username: str, hashed_password: str,
                        role: str = "employee") -> None:
        """
        Tạo/cập nhật tài khoản xác thực cho employee.
        Lưu tại account:{user_id} — KHÔNG lưu trong employee hash.
        Tạo thêm index ngược account_index:{username} → user_id.
        """
        self.redis.hset(f"account:{user_id}", mapping={
            "user_id":       user_id.encode(),
            "username":      username.encode(),
            "password_hash": hashed_password.encode(),
            "role":          role.encode(),
        })
        # Index ngược để login bằng username
        self.redis.set(f"account_index:{username}", user_id.encode())

    def _get_account_raw(self, user_id: str) -> dict:
        return self.redis.hgetall(f"account:{user_id}")

    def get_account_by_userid(self, user_id: str) -> dict | None:
        data = self.redis.hgetall(f"account:{user_id}")
        if not data:
            return None
        return {k.decode(): v.decode() for k, v in data.items()}

    def get_account_by_username(self, username: str) -> dict | None:
        """Lookup tài khoản qua username dùng index ngược."""
        user_id_bytes = self.redis.get(f"account_index:{username}")
        if not user_id_bytes:
            return None
        user_id = user_id_bytes.decode()
        return self.get_account_by_userid(user_id)

    def update_password(self, user_id: str, hashed_password: str) -> bool:
        key = f"account:{user_id}"
        if not self.redis.exists(key):
            return False
        self.redis.hset(key, "password_hash", hashed_password.encode())
        return True

    # ════════════════════════════════════════════════════════════════
    # ENTITY 3 — FaceVector (sinh trắc học — tách biệt khỏi Employee)
    # ════════════════════════════════════════════════════════════════

    def save_face_vector(self, user_id: str, vector: np.ndarray) -> None:
        """
        Lưu face vector tại face:{user_id}.
        Không đụng đến employee hash → không vi phạm 3NF.
        registered_at được ghi lại để audit.
        """
        vector_bytes = np.array(vector, dtype=np.float32).tobytes()
        self.redis.hset(f"face:{user_id}", mapping={
            "user_id":          user_id.encode(),
            "vector_embedding": vector_bytes,
            "registered_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S").encode(),
        })

    def get_face_vector(self, user_id: str) -> np.ndarray | None:
        """Lấy face vector của user_id. Trả về None nếu chưa đăng ký."""
        data = self.redis.hgetall(f"face:{user_id}")
        if not data:
            return None
        raw = data.get(b"vector_embedding")
        if raw is None:
            return None
        return np.frombuffer(raw, dtype=np.float32)

    def has_face(self, user_id: str) -> bool:
        """Kiểm tra nhân viên đã đăng ký khuôn mặt chưa."""
        return bool(self.redis.exists(f"face:{user_id}"))

    # ════════════════════════════════════════════════════════════════
    # LEGACY HELPERS — giữ backward compat với service hiện tại
    # ════════════════════════════════════════════════════════════════

    def get_login_account(self, username: str) -> dict | None:
        """
        Dùng bởi AuthService.login_employee.
        Trả về dict gồm thông tin account + user_id.
        """
        account = self.get_account_by_username(username)
        if not account:
            return None
        # Rename password_hash → password để tương thích với verify_password hiện tại
        account["password"] = account.pop("password_hash", "")
        return account

    @staticmethod
    def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))