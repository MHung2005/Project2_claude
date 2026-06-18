"""
backend/app/repositories/config_repository.py

Tầng truy cập dữ liệu thuần (SQLite) cho cấu hình hệ thống:
  - Vị trí GPS cho phép chấm công (bảng location_config — luôn đúng 1 dòng id=1)
  - Lịch làm việc (bảng schedule_config — luôn đúng 1 dòng id=1)

Dùng "single-row table" (id PRIMARY KEY CHECK(id=1)) thay cho 1 Redis hash
duy nhất location:config / schedule:config — đúng tinh thần quan hệ:
mỗi cấu hình là 1 bản ghi có cấu trúc cố định, không cần derive kiểu dữ liệu
từ chuỗi như khi đọc Redis hash (REAL/INTEGER được lưu đúng kiểu).
"""

from .db import get_db, get_lock

DEFAULT_SCHEDULE = {"start_time": "08:00", "end_time": "17:00", "grace_minutes": 0}


class ConfigRepository:
    def __init__(self):
        self.db = get_db()
        self.lock = get_lock()

    # ── LOCATION ─────────────────────────────────────────────────────
    def set_location(self, lat: float, lng: float, radius: float) -> None:
        with self.lock:
            self.db.execute(
                """
                INSERT INTO location_config (id, lat, lng, radius)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    lat = excluded.lat, lng = excluded.lng, radius = excluded.radius
                """,
                (lat, lng, radius),
            )

    def get_location(self) -> dict | None:
        with self.lock:
            row = self.db.execute(
                "SELECT lat, lng, radius FROM location_config WHERE id = 1"
            ).fetchone()
        return dict(row) if row else None

    # ── SCHEDULE ─────────────────────────────────────────────────────
    def set_schedule(self, start_time: str, end_time: str, grace_minutes: int = 0) -> None:
        with self.lock:
            self.db.execute(
                """
                INSERT INTO schedule_config (id, start_time, end_time, grace_minutes)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    start_time = excluded.start_time,
                    end_time = excluded.end_time,
                    grace_minutes = excluded.grace_minutes
                """,
                (start_time, end_time, grace_minutes),
            )

    def get_schedule(self) -> dict:
        with self.lock:
            row = self.db.execute(
                "SELECT start_time, end_time, grace_minutes FROM schedule_config WHERE id = 1"
            ).fetchone()
        return dict(row) if row else dict(DEFAULT_SCHEDULE)