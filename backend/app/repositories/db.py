"""
backend/app/repositories/db.py

Lớp kết nối CSDL — SQLite (thay thế Redis).

Mapping schema cũ (Redis) -> schema mới (SQLite quan hệ, 3NF):

  employee:{user_id}            ->  bảng employees
  account:{user_id}
    + account_index:{username}  ->  bảng accounts (username UNIQUE, FK user_id)
  face:{user_id}                ->  bảng faces (FK user_id)
  checkin:{date}:{user_id}      ->  bảng checkins (PK composite date+user_id, FK user_id)
  manager:{username}            ->  bảng managers
  location:config               ->  bảng location_config (luôn đúng 1 dòng id=1)
  schedule:config                ->  bảng schedule_config (luôn đúng 1 dòng id=1)

Ưu điểm so với Redis: FOREIGN KEY ... ON DELETE CASCADE đảm nhiệm việc xoá
cascade employee -> account/face mà trước đây EmployeeRepository.delete_employee()
phải tự code thủ công (xoá từng key Redis một).
"""

import sqlite3
import threading
from pathlib import Path

from ..core.config import settings

# sqlite3 cho phép dùng 1 connection từ nhiều thread (check_same_thread=False)
# nhưng KHÔNG tự đồng bộ các lệnh ghi đồng thời -> dùng 1 lock chung để
# tuần tự hoá, tương tự cách RedisClient cũ chỉ giữ 1 connection dùng chung.
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    user_id     TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    department  TEXT NOT NULL DEFAULT '',
    position    TEXT NOT NULL DEFAULT '',
    email       TEXT NOT NULL DEFAULT '',
    phone       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS accounts (
    user_id       TEXT PRIMARY KEY
                  REFERENCES employees(user_id) ON DELETE CASCADE,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'employee'
);

CREATE TABLE IF NOT EXISTS faces (
    user_id          TEXT PRIMARY KEY
                     REFERENCES employees(user_id) ON DELETE CASCADE,
    vector_embedding BLOB NOT NULL,
    registered_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkins (
    date            TEXT NOT NULL,
    user_id         TEXT NOT NULL
                    REFERENCES employees(user_id) ON DELETE CASCADE,
    checkin_time    TEXT,
    checkin_status  TEXT,
    checkin_lat     REAL,
    checkin_lng     REAL,
    checkin_gps_ok  INTEGER NOT NULL DEFAULT 0,
    checkout_time   TEXT,
    checkout_lat    REAL,
    checkout_lng    REAL,
    PRIMARY KEY (date, user_id)
);

CREATE TABLE IF NOT EXISTS managers (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'manager'
);

CREATE TABLE IF NOT EXISTS location_config (
    id     INTEGER PRIMARY KEY CHECK (id = 1),
    lat    REAL NOT NULL,
    lng    REAL NOT NULL,
    radius REAL NOT NULL DEFAULT 200
);

CREATE TABLE IF NOT EXISTS schedule_config (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    start_time    TEXT NOT NULL DEFAULT '08:00',
    end_time      TEXT NOT NULL DEFAULT '17:00',
    grace_minutes INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_checkins_user ON checkins(user_id);
"""


class SQLiteClient:
    """Singleton — tương tự RedisClient cũ, giữ đúng 1 connection dùng chung."""

    _instance: "SQLiteClient | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self):
        db_path = Path(settings.DB_PATH)
        if db_path.parent and str(db_path.parent) != ".":
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,   # FastAPI route đồng bộ chạy trong threadpool
            isolation_level=None,      # autocommit — mỗi execute là 1 transaction
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.executescript(SCHEMA)
        print(f"✅ Đã kết nối SQLite tại: {db_path.resolve()}")


def get_db() -> sqlite3.Connection:
    return SQLiteClient().conn


def get_lock() -> threading.RLock:
    """Lock dùng chung cho mọi repository — tuần tự hoá truy cập connection."""
    return _lock