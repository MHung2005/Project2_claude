"""
backend/app/services/config_service.py

Business logic cho cấu hình:
  - Vị trí GPS cho phép chấm công
  - Lịch làm việc (giờ vào / giờ ra)
  - Tính toán trạng thái "Đúng giờ" / "Đi muộn" dựa trên giờ vào ca
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

    def set_schedule(self, start_time: str, end_time: str) -> None:
        for t in (start_time, end_time):
            parts = t.split(":")
            if len(parts) != 2 or not all(p.isdigit() for p in parts):
                raise ValidationException(f"Định dạng giờ không hợp lệ: {t} (cần HH:MM)")
        self.config_repo.set_schedule(start_time, end_time)

    # ── ATTENDANCE STATUS CALC ───────────────────────────────────────
    def compute_checkin_status(self, now: datetime) -> str:
        """Trả về 'Đúng giờ' hoặc 'Đi muộn' dựa trên giờ vào ca."""
        cfg = self.get_schedule()
        start_h, start_m = map(int, cfg["start_time"].split(":"))
        deadline = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        return "Đúng giờ" if now <= deadline else "Đi muộn"