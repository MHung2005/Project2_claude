"""
backend/app/services/config_service.py

Business logic cho cấu hình:
  - Vị trí GPS cho phép chấm công
  - Lịch làm việc (giờ vào / giờ ra / số phút trễ cho phép)
  - Tính toán trạng thái "Đúng giờ" / "Đi muộn" dựa trên lịch làm việc
"""

from datetime import datetime

from ..core.response import ValidationException
from ..repositories.config_repository import ConfigRepository


class ConfigService:
    def __init__(self):
        self.config_repo = ConfigRepository()

    # ── LOCATION ─────────────────────────────────────────────────────
    def set_location(self, lat: float, lng: float, radius: float = 200) -> None:
        self.config_repo.set_location(lat, lng, radius)

    def get_location(self) -> dict:
        loc = self.config_repo.get_location()
        return loc or {"lat": None, "lng": None, "radius": 200}

    # ── SCHEDULE ─────────────────────────────────────────────────────
    def get_schedule(self) -> dict:
        return self.config_repo.get_schedule()

    def set_schedule(self, start_time: str, end_time: str, grace_minutes: int = 0) -> None:
        for t in (start_time, end_time):
            parts = t.split(":")
            if len(parts) != 2 or not all(p.isdigit() for p in parts):
                raise ValidationException(f"Định dạng giờ không hợp lệ: {t} (cần HH:MM)")
        if grace_minutes < 0:
            raise ValidationException("grace_minutes phải >= 0")
        self.config_repo.set_schedule(start_time, end_time, grace_minutes)

    # ── ATTENDANCE STATUS CALC ───────────────────────────────────────
    def compute_checkin_status(self, now: datetime) -> str:
        """Trả về 'Đúng giờ' hoặc 'Đi muộn' dựa trên lịch làm việc hiện tại."""
        cfg = self.get_schedule()
        start_h, start_m = map(int, cfg["start_time"].split(":"))
        grace = int(cfg.get("grace_minutes", 0))

        total_minutes = start_h * 60 + start_m + grace
        deadline_h, deadline_m = divmod(total_minutes, 60)
        deadline = now.replace(hour=deadline_h % 24, minute=deadline_m, second=0, microsecond=0)

        return "Đúng giờ" if now <= deadline else "Đi muộn"
