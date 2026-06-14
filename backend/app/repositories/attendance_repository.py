"""
backend/app/repositories/attendance_repository.py

Tầng truy cập dữ liệu thuần (Redis) cho bản ghi chấm công (check-in / check-out).
"""

from datetime import datetime, timedelta

from .redis_client import get_redis

CHECKIN_TTL_SECONDS = 60 * 60 * 24 * 90  # 90 ngày


class AttendanceRepository:
    def __init__(self):
        self.redis = get_redis()

    # ── WRITE ────────────────────────────────────────────────────────
    def save_checkin(self, user_id: str, name: str, department: str, position: str,
                      timestamp: str, status: str,
                      lat=None, lng=None, gps_ok: bool = False) -> None:
        today = timestamp.split(" ")[0]
        key = f"checkin:{today}:{user_id}"
        self.redis.hset(key, mapping={
            "user_id":    user_id.encode(),
            "name":       name.encode(),
            "department": department.encode(),
            "position":   position.encode(),
            "timestamp":  timestamp.encode(),
            "lat":        str(lat or "").encode(),
            "lng":        str(lng or "").encode(),
            "gps_ok":     (b"true" if gps_ok else b"false"),
            "status":     status.encode(),
        })
        self.redis.expire(key, CHECKIN_TTL_SECONDS)

    def save_checkout(self, user_id: str, date_str: str, checkout_time: str,
                       lat=None, lng=None) -> bool:
        key = f"checkin:{date_str}:{user_id}"
        if not self.redis.exists(key):
            return False
        self.redis.hset(key, mapping={
            "checkout_time": checkout_time.encode(),
            "checkout_lat":  str(lat or "").encode(),
            "checkout_lng":  str(lng or "").encode(),
        })
        return True

    # ── READ ─────────────────────────────────────────────────────────
    def exists_for_date(self, user_id: str, date_str: str) -> bool:
        return bool(self.redis.exists(f"checkin:{date_str}:{user_id}"))

    def get_record(self, user_id: str, date_str: str) -> dict | None:
        data = self.redis.hgetall(f"checkin:{date_str}:{user_id}")
        if not data:
            return None
        return {k.decode(): v.decode() for k, v in data.items()}

    def has_checked_out(self, user_id: str, date_str: str) -> bool:
        data = self.redis.hgetall(f"checkin:{date_str}:{user_id}")
        return b"checkout_time" in data

    def get_by_date(self, date_str: str) -> list[dict]:
        records = []
        for key in self.redis.scan_iter(f"checkin:{date_str}:*"):
            data = self.redis.hgetall(key)
            records.append({k.decode(): v.decode() for k, v in data.items()})
        records.sort(key=lambda x: x.get("timestamp", ""))
        return records

    def get_map_by_date(self, date_str: str) -> dict[str, dict]:
        """Trả về map {user_id: record} cho 1 ngày."""
        result = {}
        for key in self.redis.scan_iter(f"checkin:{date_str}:*"):
            data = self.redis.hgetall(key)
            decoded = {k.decode(): v.decode() for k, v in data.items()}
            uid = decoded.get("user_id", "")
            if uid:
                result[uid] = decoded
        return result

    def count_by_date(self, date_str: str) -> int:
        return sum(1 for _ in self.redis.scan_iter(f"checkin:{date_str}:*"))

    def count_by_range(self, start_date: str, end_date: str) -> list[dict]:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return []
        if start > end:
            return []
        result = []
        day = start
        while day <= end:
            date_str = day.strftime("%Y-%m-%d")
            result.append({
                "date":  date_str,
                "label": day.strftime("%a"),
                "count": self.count_by_date(date_str),
            })
            day += timedelta(days=1)
        return result

    def get_weekly(self) -> list[dict]:
        result = []
        today = datetime.now()
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            date_str = day.strftime("%Y-%m-%d")
            result.append({
                "date":  date_str,
                "label": day.strftime("%a"),
                "count": self.count_by_date(date_str),
            })
        return result
