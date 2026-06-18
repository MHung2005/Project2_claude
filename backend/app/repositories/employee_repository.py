"""
backend/app/repositories/employee_repository.py

Ba bảng quan hệ riêng biệt — tương ứng 3 entity Redis cũ:

  [Bảng 1] employees
      user_id, name, department, position, email, phone
      Chỉ chứa thông tin nhân sự thuần — KHÔNG có password/username/vector.

  [Bảng 2] accounts
      user_id (FK), username (UNIQUE), password_hash, role
      Tách biệt xác thực khỏi hồ sơ nhân sự. UNIQUE(username) thay cho
      account_index:{username} của Redid — và còn CHẶT hơn: CSDL quan hệ
      tự đảm bảo không thể có 2 account trùng username (Redis cũ không
      đảm bảo được điều này, set sau sẽ âm thầm đè set trước).

  [Bảng 3] faces
      user_id (FK), vector_embedding (BLOB), registered_at
      biometric_status được derive = "approved" nếu có dòng face tương ứng.

FOREIGN KEY ... ON DELETE CASCADE đảm nhiệm việc xoá cascade
employee -> account/face mà bản Redis cũ phải tự code thủ công trong
delete_employee().
"""

from datetime import datetime

import numpy as np

from .db import get_db, get_lock

EMPLOYEE_TEXT_FIELDS = {"user_id", "name", "department", "position", "email", "phone"}


class EmployeeRepository:
    def __init__(self):
        self.db = get_db()
        self.lock = get_lock()

    # ════════════════════════════════════════════════════════════════
    # BẢNG 1 — employees (hồ sơ nhân sự thuần)
    # ════════════════════════════════════════════════════════════════

    def create_employee(self, user_id: str, fields: dict) -> None:
        """Tạo (hoặc upsert) hồ sơ nhân sự. Không lưu xác thực/sinh trắc học."""
        with self.lock:
            self.db.execute(
                """
                INSERT INTO employees (user_id, name, department, position, email, phone)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name       = excluded.name,
                    department = excluded.department,
                    position   = excluded.position,
                    email      = excluded.email,
                    phone      = excluded.phone
                """,
                (
                    user_id,
                    fields.get("name", ""),
                    fields.get("department", ""),
                    fields.get("position", ""),
                    fields.get("email", ""),
                    fields.get("phone", ""),
                ),
            )

    def update_employee(self, user_id: str, name: str, department: str, position: str) -> bool:
        with self.lock:
            cur = self.db.execute(
                "UPDATE employees SET name = ?, department = ?, position = ? WHERE user_id = ?",
                (name, department, position, user_id),
            )
            return cur.rowcount > 0

    def delete_employee(self, user_id: str) -> bool:
        """Xoá employee — accounts/faces tự xoá theo (ON DELETE CASCADE)."""
        with self.lock:
            cur = self.db.execute("DELETE FROM employees WHERE user_id = ?", (user_id,))
            return cur.rowcount > 0

    def exists(self, user_id: str) -> bool:
        with self.lock:
            row = self.db.execute(
                "SELECT 1 FROM employees WHERE user_id = ?", (user_id,)
            ).fetchone()
        return row is not None

    def get_raw(self, user_id: str) -> dict:
        with self.lock:
            row = self.db.execute(
                "SELECT * FROM employees WHERE user_id = ?", (user_id,)
            ).fetchone()
        return dict(row) if row else {}

    def get_employee(self, user_id: str) -> dict | None:
        """Trả về thông tin nhân sự, kèm biometric_status tính toán (derived)."""
        with self.lock:
            row = self.db.execute(
                "SELECT user_id, name, department, position, email, phone "
                "FROM employees WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                return None
            has_face = self.db.execute(
                "SELECT 1 FROM faces WHERE user_id = ?", (user_id,)
            ).fetchone() is not None

        decoded = dict(row)
        decoded["biometric_status"] = "approved" if has_face else "none"
        return decoded

    def get_all(self) -> list[dict]:
        with self.lock:
            rows = self.db.execute(
                "SELECT user_id, name, department, position, email, phone "
                "FROM employees ORDER BY name"
            ).fetchall()
            face_ids = {
                r["user_id"] for r in self.db.execute("SELECT user_id FROM faces").fetchall()
            }

        employees = []
        for row in rows:
            decoded = dict(row)
            decoded["biometric_status"] = "approved" if decoded["user_id"] in face_ids else "none"
            employees.append(decoded)
        return employees

    # ════════════════════════════════════════════════════════════════
    # BẢNG 2 — accounts (xác thực — tách biệt khỏi employees)
    # ════════════════════════════════════════════════════════════════

    def attach_account(self, user_id: str, username: str, hashed_password: str,
                        role: str = "employee") -> None:
        """
        Tạo/cập nhật tài khoản xác thực cho employee.
        Yêu cầu employees.user_id đã tồn tại (FOREIGN KEY).
        UNIQUE(username) sẽ raise sqlite3.IntegrityError nếu username đã
        thuộc về user_id khác — caller (bulk import) đã có try/except để
        bắt lỗi này theo từng dòng.
        """
        with self.lock:
            self.db.execute(
                """
                INSERT INTO accounts (user_id, username, password_hash, role)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username      = excluded.username,
                    password_hash = excluded.password_hash,
                    role          = excluded.role
                """,
                (user_id, username, hashed_password, role),
            )

    def get_account_by_userid(self, user_id: str) -> dict | None:
        with self.lock:
            row = self.db.execute(
                "SELECT user_id, username, password_hash, role FROM accounts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_account_by_username(self, username: str) -> dict | None:
        with self.lock:
            row = self.db.execute(
                "SELECT user_id, username, password_hash, role FROM accounts WHERE username = ?",
                (username,),
            ).fetchone()
        return dict(row) if row else None

    def update_password(self, user_id: str, hashed_password: str) -> bool:
        with self.lock:
            cur = self.db.execute(
                "UPDATE accounts SET password_hash = ? WHERE user_id = ?",
                (hashed_password, user_id),
            )
            return cur.rowcount > 0

    # ════════════════════════════════════════════════════════════════
    # BẢNG 3 — faces (sinh trắc học — tách biệt khỏi employees)
    # ════════════════════════════════════════════════════════════════

    def save_face_vector(self, user_id: str, vector: np.ndarray) -> None:
        """Lưu face vector — không đụng đến bảng employees."""
        vector_bytes = np.array(vector, dtype=np.float32).tobytes()
        registered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            self.db.execute(
                """
                INSERT INTO faces (user_id, vector_embedding, registered_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    vector_embedding = excluded.vector_embedding,
                    registered_at    = excluded.registered_at
                """,
                (user_id, vector_bytes, registered_at),
            )

    def get_face_vector(self, user_id: str) -> np.ndarray | None:
        with self.lock:
            row = self.db.execute(
                "SELECT vector_embedding FROM faces WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            return None
        return np.frombuffer(row["vector_embedding"], dtype=np.float32)

    def has_face(self, user_id: str) -> bool:
        with self.lock:
            row = self.db.execute(
                "SELECT 1 FROM faces WHERE user_id = ?", (user_id,)
            ).fetchone()
        return row is not None

    # ════════════════════════════════════════════════════════════════
    # LEGACY HELPERS — giữ backward compat với service hiện tại
    # ════════════════════════════════════════════════════════════════

    def get_login_account(self, username: str) -> dict | None:
        account = self.get_account_by_username(username)
        if not account:
            return None
        account["password"] = account.pop("password_hash", "")
        return account

    @staticmethod
    def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))