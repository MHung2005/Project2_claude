"""
backend/app/repositories/employee_repository.py

Tầng truy cập dữ liệu thuần (Redis) cho thực thể Employee + face vector.
KHÔNG chứa business logic — chỉ đọc/ghi dữ liệu.
"""

import numpy as np
from redis.commands.search.query import Query

from .redis_client import get_redis, INDEX_NAME

TEXT_FIELDS = {
    b"user_id", b"name", b"department", b"position",
    b"last_attendance", b"biometric_status", b"email",
    b"phone", b"username",
}


class EmployeeRepository:
    def __init__(self):
        self.redis = get_redis()

    # ── CREATE / UPDATE ─────────────────────────────────────────────
    def save_face(self, user_id: str, name: str, department: str, position: str, vector) -> None:
        vector_bytes = np.array(vector, dtype=np.float32).tobytes()
        self.redis.hset(f"employee:{user_id}", mapping={
            "user_id":          user_id.encode(),
            "name":             name.encode(),
            "department":       department.encode(),
            "position":         position.encode(),
            "biometric_status": b"approved",   # auto-approved, no manager review
            "vector_embedding": vector_bytes,
        })

    def update_face_vector(self, user_id: str, vector) -> None:
        vector_bytes = np.array(vector, dtype=np.float32).tobytes()
        self.redis.hset(f"employee:{user_id}", mapping={
            "vector_embedding": vector_bytes,
            "biometric_status": b"approved",   # auto-approved
        })

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

    def set_biometric_status(self, user_id: str, status: str) -> bool:
        key = f"employee:{user_id}"
        if not self.redis.exists(key):
            return False
        self.redis.hset(key, "biometric_status", status.encode())
        return True

    def set_last_attendance(self, user_id: str, date_str: str) -> None:
        self.redis.hset(f"employee:{user_id}", "last_attendance", date_str.encode())

    def create_from_bulk(self, user_id: str, fields: dict) -> None:
        mapping = {
            "user_id":          user_id.encode(),
            "name":             fields.get("name", "").encode(),
            "department":       fields.get("department", "").encode(),
            "position":         fields.get("position", "").encode(),
            "email":            fields.get("email", "").encode(),
            "phone":            fields.get("phone", "").encode(),
            "biometric_status": b"approved",   # auto-approved
        }
        self.redis.hset(f"employee:{user_id}", mapping=mapping)

    def attach_login_account(self, user_id: str, username: str, hashed_password: str) -> None:
        self.redis.hset(f"employee:{user_id}", mapping={
            "username": username.encode(),
            "password": hashed_password.encode(),
            "role":     b"employee",
        })
        self.redis.set(f"emp_login:{username}", user_id.encode())

    def update_password(self, user_id: str, hashed_password: str) -> bool:
        key = f"employee:{user_id}"
        if not self.redis.exists(key):
            return False
        self.redis.hset(key, "password", hashed_password.encode())
        return True

    # ── DELETE ───────────────────────────────────────────────────────
    def delete(self, user_id: str) -> bool:
        return self.redis.delete(f"employee:{user_id}") > 0

    # ── READ ─────────────────────────────────────────────────────────
    def exists(self, user_id: str) -> bool:
        return bool(self.redis.exists(f"employee:{user_id}"))

    def get_raw(self, user_id: str) -> dict:
        return self.redis.hgetall(f"employee:{user_id}")

    def get_face_vector(self, user_id: str):
        """Lấy vector embedding của đúng user_id, trả về numpy array hoặc None."""
        data = self.redis.hgetall(f"employee:{user_id}")
        if not data:
            return None
        raw = data.get(b"vector_embedding")
        if raw is None:
            return None
        return np.frombuffer(raw, dtype=np.float32)

    def get_all(self) -> list[dict]:
        employees = []
        for key in self.redis.scan_iter("employee:*"):
            try:
                data = self.redis.hgetall(key)
                if not data:
                    continue
                decoded = {}
                for k, v in data.items():
                    field_name = k if isinstance(k, bytes) else k.encode()
                    if field_name in TEXT_FIELDS:
                        decoded[k.decode() if isinstance(k, bytes) else k] = (
                            v.decode() if isinstance(v, bytes) else v
                        )
                if "user_id" not in decoded:
                    continue
                employees.append({
                    "user_id":          decoded.get("user_id", ""),
                    "name":             decoded.get("name", ""),
                    "department":       decoded.get("department", ""),
                    "position":         decoded.get("position", ""),
                    "email":            decoded.get("email", ""),
                    "phone":            decoded.get("phone", ""),
                    "biometric_status": decoded.get("biometric_status", "approved"),
                    "last_attendance":  decoded.get("last_attendance", ""),
                })
            except Exception as e:
                print(f"[EmployeeRepository.get_all] Lỗi key '{key}': {e}")
        return employees

    def get_login_account(self, username: str) -> dict | None:
        user_id = self.redis.get(f"emp_login:{username}")
        if not user_id:
            return None
        data = self.redis.hgetall(f"employee:{user_id.decode()}")
        return {k.decode(): v.decode() for k, v in data.items()}

    # ── VECTOR SEARCH (kept for manager use, not for checkin) ────────
    def search_by_vector(self, query_vector, top_k: int = 1) -> dict | None:
        vector_bytes = np.array(query_vector, dtype=np.float32).tobytes()
        q = (
            Query(f"*=>[KNN {top_k} @vector_embedding $vector_param AS score]")
            .sort_by("score")
            .return_fields("user_id", "name", "department", "position", "score")
            .dialect(2)
        )
        results = self.redis.ft(INDEX_NAME).search(q, {"vector_param": vector_bytes})
        if not results.docs:
            return None
        doc = results.docs[0]
        return {
            "user_id":    doc.user_id.decode() if isinstance(doc.user_id, bytes) else doc.user_id,
            "name":       doc.name.decode() if isinstance(doc.name, bytes) else doc.name,
            "department": doc.department.decode() if isinstance(doc.department, bytes) else doc.department,
            "position":   doc.position.decode() if isinstance(doc.position, bytes) else doc.position,
            "score":      1 - float(doc.score),
        }

    def cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Tính cosine similarity giữa 2 vector."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))