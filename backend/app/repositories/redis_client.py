"""
backend/app/repositories/redis_client.py

Khởi tạo Redis connection (singleton) + tạo Redis Search index cho
vector embedding khuôn mặt. Mọi repository khác đều dùng connection này.
"""

import redis
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.exceptions import ResponseError

from ..core.config import settings

INDEX_NAME = "store_faces"
EMPLOYEE_PREFIX = "employee:"
VECTOR_DIM = 512


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
        self._ensure_index()

    def _ensure_index(self):
        schema = (
            TextField("user_id"),
            TextField("name"),
            TextField("department"),
            TextField("position"),
            VectorField("vector_embedding", "HNSW", {
                "TYPE": "FLOAT32",
                "DIM": VECTOR_DIM,
                "DISTANCE_METRIC": "COSINE",
            }),
        )

        index_exists = False
        try:
            info = self.conn.ft(INDEX_NAME).info()
            index_exists = True
            idx_def_raw = info.get(b"index_definition", info.get("index_definition", []))
            if isinstance(idx_def_raw, list):
                idx_def = dict(zip(idx_def_raw[::2], idx_def_raw[1::2]))
            elif isinstance(idx_def_raw, dict):
                idx_def = idx_def_raw
            else:
                idx_def = {}
            prefixes = idx_def.get(b"prefixes", idx_def.get("prefixes", []))
            decoded_prefixes = [p.decode() if isinstance(p, bytes) else p for p in prefixes]
            if EMPLOYEE_PREFIX not in decoded_prefixes:
                print("⚠️ Index cũ sai cấu hình prefix, đang tạo lại...")
                self.conn.ft(INDEX_NAME).dropindex(dd=False)
                index_exists = False
        except ResponseError as e:
            if "Unknown index name" in str(e) or "no such index" in str(e).lower():
                index_exists = False
            else:
                raise

        if not index_exists:
            try:
                self.conn.ft(INDEX_NAME).create_index(
                    fields=schema,
                    definition=IndexDefinition(prefix=[EMPLOYEE_PREFIX], index_type=IndexType.HASH),
                )
                print("✅ Đã khởi tạo thành công chỉ mục Redis Search.")
            except ResponseError as e:
                if "Index already exists" in str(e):
                    print("✅ Index đã tồn tại, bỏ qua.")
                else:
                    raise
        else:
            print("✅ Index hợp lệ, tiếp tục sử dụng.")


def get_redis() -> redis.Redis:
    return RedisClient().conn
