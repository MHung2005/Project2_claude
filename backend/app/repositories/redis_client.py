"""
backend/app/repositories/redis_client.py  (3NF Refactor)

Thiết kế Redis Key Schema đạt chuẩn 3NF:

  employee:{user_id}          → thông tin nhân sự thuần (không có account/face/attendance)
  account:{user_id}           → xác thực (username, password_hash, role)
  account_index:{username}    → user_id (lookup ngược)
  face:{user_id}              → vector embedding khuôn mặt + metadata
  checkin:{date}:{user_id}    → bản ghi chấm công (chỉ FK, không copy name/dept/pos)
  manager:{username}          → tài khoản manager
  config:location             → cấu hình GPS
  config:schedule             → cấu hình lịch làm việc

Redis Search index chạy trên prefix "employee:" (chỉ dùng cho manager search, không cho checkin).
"""

import redis
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.exceptions import ResponseError

from ..core.config import settings

# ── Index constants ──────────────────────────────────────────────────────
EMPLOYEE_SEARCH_INDEX = "idx_employee"
EMPLOYEE_PREFIX       = "employee:"
FACE_PREFIX           = "face:"
VECTOR_DIM            = 512


class RedisClient:
    _instance: "RedisClient | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self):
        self.conn = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=False,
        )
        self._ensure_employee_index()

    def _ensure_employee_index(self):
        """
        Index chỉ trên employee:{user_id} — các trường nhân sự thuần.
        FaceVector lưu tại face:{user_id} — KHÔNG nằm trong index này.
        """
        schema = (
            TextField("user_id"),
            TextField("name"),
            TextField("department"),
            TextField("position"),
            TextField("email"),
            TextField("phone"),
        )

        index_exists = False
        try:
            info = self.conn.ft(EMPLOYEE_SEARCH_INDEX).info()
            index_exists = True
            # Kiểm tra prefix đúng
            idx_def_raw = info.get(b"index_definition", info.get("index_definition", []))
            if isinstance(idx_def_raw, list):
                idx_def = dict(zip(idx_def_raw[::2], idx_def_raw[1::2]))
            elif isinstance(idx_def_raw, dict):
                idx_def = idx_def_raw
            else:
                idx_def = {}
            prefixes = idx_def.get(b"prefixes", idx_def.get("prefixes", []))
            decoded = [p.decode() if isinstance(p, bytes) else p for p in prefixes]
            if EMPLOYEE_PREFIX not in decoded:
                print("⚠️  Index employee cũ sai prefix, đang tạo lại...")
                self.conn.ft(EMPLOYEE_SEARCH_INDEX).dropindex(dd=False)
                index_exists = False
        except ResponseError as e:
            if "Unknown index name" in str(e) or "no such index" in str(e).lower():
                index_exists = False
            else:
                raise

        if not index_exists:
            try:
                self.conn.ft(EMPLOYEE_SEARCH_INDEX).create_index(
                    fields=schema,
                    definition=IndexDefinition(
                        prefix=[EMPLOYEE_PREFIX],
                        index_type=IndexType.HASH,
                    ),
                )
                print("✅ Đã tạo index employee (3NF schema).")
            except ResponseError as e:
                if "Index already exists" in str(e):
                    print("✅ Index employee đã tồn tại.")
                else:
                    raise
        else:
            print("✅ Index employee hợp lệ.")


def get_redis() -> redis.Redis:
    return RedisClient().conn