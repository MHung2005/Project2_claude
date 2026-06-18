"""
backend/app/repositories/attendance_repository.py  (3NF Refactor)

[Entity 4] checkin:{date}:{user_id}
    Chỉ lưu FK (user_id) + dữ liệu thuộc về sự kiện chấm công.
    KHÔNG sao chép name / department / position từ Employee.

    Trước (vi phạm 2NF):
        checkin:{date}:{user_id} → { user_id, name, department, position,   ← ❌ copy từ Employee
                                      timestamp, lat, lng, gps_ok, status,
                                      checkout_time, ... }

    Sau (đạt 3NF):
        checkin:{date}:{user_id} → { user_id,                               ← ✅ chỉ FK
                                      checkin_time, checkin_lat, checkin_lng,
                                      checkin_gps_ok, checkin_status,
                                      checkout_time, checkout_lat, checkout_lng }

Khi cần hiển thị name/department/position → JOIN với employee:{user_id}.
"""

from datetime import datetime, timedelta

from .redis_client import get_redis

CHECKIN_TTL_SECONDS = 60 * 60 * 24 * 90   # 90 ngày


class AttendanceRepository:
    def __init__(self):
        self.redis = get_redis()

    # ── WRITE ────────────────────────────────────────────────────────

    def save_checkin(
        self,
        user_id: str,
        checkin_time: str,
        checkin_status: str,
        lat: float | None = None,
        lng: float | None = None,
        gps_ok: bool = False,
    ) -> None:
        """
        Lưu bản ghi check-in.
        Chỉ lưu user_id (FK) + các thuộc tính của sự kiện chấm công.
        name/department/position KHÔNG được lưu ở đây → tránh vi phạm 2NF.
        """
        date_str = checkin_time.split(" ")[0]
        key = f"checkin:{date_str}:{user_id}"
        self.redis.hset(key, mapping={
            "user_id":         user_id.encode(),
            "checkin_time":    checkin_time.encode(),
            "checkin_status":  checkin_status.encode(),
            "checkin_lat":     str(lat or "").encode(),
            "checkin_lng":     str(lng or "").encode(),
            "checkin_gps_ok":  (b"true" if gps_ok else b"false"),
        })
        self.redis.expire(key, CHECKIN_TTL_SECONDS)

    def save_checkout(
        self,
        user_id: str,
        date_str: str,
        checkout_time: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> bool:
        key = f"checkin:{date_str}:{user_id}"
        if not self.redis.exists(key):
            return False
        self.redis.hset(key, mapping={
            "checkout_time": checkout_time.encode(),
            "checkout_lat":  str(lat or "").encode(),
            "checkout_lng":  str(lng or "").encode(),
        })
        return True

    # ── READ — single record ─────────────────────────────────────────

    def exists_for_date(self, user_id: str, date_str: str) -> bool:
        return bool(self.redis.exists(f"checkin:{date_str}:{user_id}"))

    def has_checked_out(self, user_id: str, date_str: str) -> bool:
        data = self.redis.hgetall(f"checkin:{date_str}:{user_id}")
        return b"checkout_time" in data

    def get_record(self, user_id: str, date_str: str) -> dict | None:
        """
        Trả về bản ghi chấm công thô (chỉ có FK + event fields).
        Caller tự JOIN với EmployeeRepository nếu cần name/dept/position.
        """
        data = self.redis.hgetall(f"checkin:{date_str}:{user_id}")
        if not data:
            return None
        return {k.decode(): v.decode() for k, v in data.items()}

    # ── READ — by date ───────────────────────────────────────────────

    def get_by_date(self, date_str: str) -> list[dict]:
        """Trả về tất cả bản ghi chấm công trong ngày (chỉ có FK + event data)."""
        records = []
        for key in self.redis.scan_iter(f"checkin:{date_str}:*"):
            data = self.redis.hgetall(key)
            records.append({k.decode(): v.decode() for k, v in data.items()})
        records.sort(key=lambda x: x.get("checkin_time", ""))
        return records

    def get_map_by_date(self, date_str: str) -> dict[str, dict]:
        """Trả về {user_id: record} cho 1 ngày."""
        result = {}
        for key in self.redis.scan_iter(f"checkin:{date_str}:*"):
            data = self.redis.hgetall(key)
            decoded = {k.decode(): v.decode() for k, v in data.items()}
            uid = decoded.get("user_id", "")
            if uid:
                result[uid] = decoded
        return result

    # ── READ — aggregates ────────────────────────────────────────────

    def count_by_date(self, date_str: str) -> int:
        return sum(1 for _ in self.redis.scan_iter(f"checkin:{date_str}:*"))

    def count_by_range(self, start_date: str, end_date: str) -> list[dict]:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end   = datetime.strptime(end_date,   "%Y-%m-%d")
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
        today = datetime.now()
        return [
            {
                "date":  (today - timedelta(days=i)).strftime("%Y-%m-%d"),
                "label": (today - timedelta(days=i)).strftime("%a"),
                "count": self.count_by_date((today - timedelta(days=i)).strftime("%Y-%m-%d")),
            }
            for i in range(6, -1, -1)
        ]

    # ── READ — personal history (dùng bởi EmployeeService) ──────────

    def get_records_in_range(self, user_id: str, start_date: str, end_date: str) -> list[dict]:
        """
        Trả về các bản ghi chấm công của một nhân viên trong khoảng ngày.
        Chỉ trả về dữ liệu thuần của sự kiện, không có employee info.
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end   = datetime.strptime(end_date,   "%Y-%m-%d")
        except ValueError:
            return []
        records = []
        day = start
        while day <= end:
            date_str = day.strftime("%Y-%m-%d")
            rec = self.get_record(user_id, date_str)
            if rec:
                records.append(rec)
            day += timedelta(days=1)
        return records