"""
backend/app/repositories/attendance_repository.py

[Bảng] checkins
    PRIMARY KEY (date, user_id), FOREIGN KEY user_id -> employees(user_id).
    Chỉ lưu FK (user_id) + dữ liệu của sự kiện chấm công — KHÔNG sao chép
    name/department/position từ employees (đúng 3NF, giữ nguyên triết lý
    thiết kế Redis cũ).

    Khi cần hiển thị name/department/position -> JOIN với bảng employees
    tại thời điểm đọc (xem ManagerService._enrich_attendance_records).
"""

from datetime import datetime, timedelta

from .db import get_db, get_lock


def _row_to_record(row) -> dict:
    """Chuẩn hoá 1 row CSDL về dict tương thích với format API cũ (string-based)."""
    d = dict(row)
    d["checkin_gps_ok"] = "true" if d.get("checkin_gps_ok") else "false"
    for k, v in list(d.items()):
        if v is None:
            d[k] = ""
    return d


class AttendanceRepository:
    def __init__(self):
        self.db = get_db()
        self.lock = get_lock()

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
        date_str = checkin_time.split(" ")[0]
        with self.lock:
            self.db.execute(
                """
                INSERT INTO checkins
                    (date, user_id, checkin_time, checkin_status,
                     checkin_lat, checkin_lng, checkin_gps_ok)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, user_id) DO UPDATE SET
                    checkin_time   = excluded.checkin_time,
                    checkin_status = excluded.checkin_status,
                    checkin_lat    = excluded.checkin_lat,
                    checkin_lng    = excluded.checkin_lng,
                    checkin_gps_ok = excluded.checkin_gps_ok
                """,
                (date_str, user_id, checkin_time, checkin_status,
                 lat, lng, 1 if gps_ok else 0),
            )

    def save_checkout(
        self,
        user_id: str,
        date_str: str,
        checkout_time: str,
        lat: float | None = None,
        lng: float | None = None,
    ) -> bool:
        with self.lock:
            cur = self.db.execute(
                """
                UPDATE checkins
                SET checkout_time = ?, checkout_lat = ?, checkout_lng = ?
                WHERE date = ? AND user_id = ?
                """,
                (checkout_time, lat, lng, date_str, user_id),
            )
            return cur.rowcount > 0

    # ── READ — single record ─────────────────────────────────────────

    def exists_for_date(self, user_id: str, date_str: str) -> bool:
        with self.lock:
            row = self.db.execute(
                "SELECT 1 FROM checkins WHERE date = ? AND user_id = ?",
                (date_str, user_id),
            ).fetchone()
        return row is not None

    def has_checked_out(self, user_id: str, date_str: str) -> bool:
        with self.lock:
            row = self.db.execute(
                "SELECT checkout_time FROM checkins WHERE date = ? AND user_id = ?",
                (date_str, user_id),
            ).fetchone()
        return bool(row and row["checkout_time"])

    def get_record(self, user_id: str, date_str: str) -> dict | None:
        with self.lock:
            row = self.db.execute(
                "SELECT * FROM checkins WHERE date = ? AND user_id = ?",
                (date_str, user_id),
            ).fetchone()
        return _row_to_record(row) if row else None

    # ── READ — by date ───────────────────────────────────────────────

    def get_by_date(self, date_str: str) -> list[dict]:
        with self.lock:
            rows = self.db.execute(
                "SELECT * FROM checkins WHERE date = ? ORDER BY checkin_time",
                (date_str,),
            ).fetchall()
        return [_row_to_record(r) for r in rows]

    def get_map_by_date(self, date_str: str) -> dict[str, dict]:
        """Trả về {user_id: record} cho 1 ngày."""
        return {r["user_id"]: r for r in self.get_by_date(date_str)}

    # ── READ — aggregates ────────────────────────────────────────────

    def count_by_date(self, date_str: str) -> int:
        with self.lock:
            row = self.db.execute(
                "SELECT COUNT(*) AS c FROM checkins WHERE date = ?",
                (date_str,),
            ).fetchone()
        return row["c"] if row else 0

    def count_by_range(self, start_date: str, end_date: str) -> list[dict]:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end   = datetime.strptime(end_date,   "%Y-%m-%d")
        except ValueError:
            return []
        if start > end:
            return []

        with self.lock:
            rows = self.db.execute(
                """
                SELECT date, COUNT(*) AS c FROM checkins
                WHERE date BETWEEN ? AND ?
                GROUP BY date
                """,
                (start_date, end_date),
            ).fetchall()
        counts = {r["date"]: r["c"] for r in rows}

        result = []
        day = start
        while day <= end:
            date_str = day.strftime("%Y-%m-%d")
            result.append({
                "date":  date_str,
                "label": day.strftime("%a"),
                "count": counts.get(date_str, 0),
            })
            day += timedelta(days=1)
        return result

    def get_weekly(self) -> list[dict]:
        today = datetime.now()
        start_date = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        end_date   = today.strftime("%Y-%m-%d")
        return self.count_by_range(start_date, end_date)

    # ── READ — personal history (dùng bởi EmployeeService) ──────────

    def get_records_in_range(self, user_id: str, start_date: str, end_date: str) -> list[dict]:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date,   "%Y-%m-%d")
        except ValueError:
            return []

        with self.lock:
            rows = self.db.execute(
                """
                SELECT * FROM checkins
                WHERE user_id = ? AND date BETWEEN ? AND ?
                ORDER BY date
                """,
                (user_id, start_date, end_date),
            ).fetchall()
        return [_row_to_record(r) for r in rows]