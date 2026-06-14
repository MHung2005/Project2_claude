"""
backend/app/repositories/config_repository.py

Tầng truy cập dữ liệu thuần (Redis) cho cấu hình hệ thống:
  - Vị trí GPS cho phép chấm công (location:config)
  - Lịch làm việc (schedule:config)
"""

from .redis_client import get_redis

DEFAULT_SCHEDULE = {"start_time": "08:00", "end_time": "17:00", "grace_minutes": "0"}


class ConfigRepository:
    def __init__(self):
        self.redis = get_redis()

    # ── LOCATION ─────────────────────────────────────────────────────
    def set_location(self, lat: float, lng: float, radius: float) -> None:
        self.redis.hset("location:config", mapping={
            "lat":    str(lat).encode(),
            "lng":    str(lng).encode(),
            "radius": str(radius).encode(),
        })

    def get_location(self) -> dict | None:
        data = self.redis.hgetall("location:config")
        if not data:
            return None
        return {k.decode(): float(v.decode()) for k, v in data.items()}

    # ── SCHEDULE ─────────────────────────────────────────────────────
    def set_schedule(self, start_time: str, end_time: str, grace_minutes: int = 0) -> None:
        self.redis.hset("schedule:config", mapping={
            "start_time":    start_time.encode(),
            "end_time":      end_time.encode(),
            "grace_minutes": str(grace_minutes).encode(),
        })

    def get_schedule(self) -> dict:
        data = self.redis.hgetall("schedule:config")
        if not data:
            return dict(DEFAULT_SCHEDULE)
        return {k.decode(): v.decode() for k, v in data.items()}
