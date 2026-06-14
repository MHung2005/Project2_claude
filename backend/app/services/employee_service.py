"""
backend/app/services/employee_service.py

Business logic cho các chức năng của Nhân viên (Employee):
  - Chấm công vào / ra (Face Recognition + GPS)
  - Đăng ký / cập nhật khuôn mặt
  - Xem hồ sơ cá nhân
  - Xem thống kê chấm công cá nhân (theo ngày/tháng)
"""

from datetime import datetime
from calendar import monthrange

import numpy as np
import cv2

from ..core.config import settings
from ..core.response import (
    NotFoundException, ValidationException, UnauthorizedException,
    ForbiddenException, ConflictException,
)
from ..repositories.employee_repository import EmployeeRepository
from ..repositories.attendance_repository import AttendanceRepository
from .ai.embeddings import FaceEmbeddingService
from .gps_service import is_within_radius
from .config_service import ConfigService

PERSONAL_FIELDS = {"user_id", "name", "department", "position",
                   "email", "phone", "biometric_status", "last_attendance"}


class EmployeeService:
    def __init__(self):
        self.employee_repo = EmployeeRepository()
        self.attendance_repo = AttendanceRepository()
        self.config_service = ConfigService()
        self.face_embed = FaceEmbeddingService()

    # ── HELPERS ──────────────────────────────────────────────────────
    @staticmethod
    def _decode_image(contents: bytes):
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValidationException("Ảnh không hợp lệ")
        return img

    def _extract_face_vector(self, contents: bytes, on_fail_message: str):
        img = self._decode_image(contents)
        vector = self.face_embed.embedding_img(img)
        if vector is None:
            raise ValidationException(on_fail_message)
        return vector

    def _check_gps(self, lat: float | None, lng: float | None, required: bool = False) -> bool:
        """Trả về gps_ok (bool). Raise nếu vị trí ngoài bán kính cho phép."""
        if lat is None or lng is None:
            if required:
                raise ForbiddenException("Cần cung cấp vị trí GPS để chấm công")
            return False

        loc = self.config_service.config_repo.get_location()
        if loc and not is_within_radius(lat, lng, loc["lat"], loc["lng"], loc["radius"]):
            raise ForbiddenException("Bạn không trong phạm vi cho phép điểm danh")
        return True

    # ── CHECK-IN ─────────────────────────────────────────────────────
    def checkin(self, user_id: str, file_contents: bytes,
                 lat: float | None, lng: float | None) -> dict:
        vector = self._extract_face_vector(
            file_contents,
            "Không nhận diện được khuôn mặt. Vui lòng đảm bảo khuôn mặt rõ ràng, đủ ánh sáng."
        )

        match = self.employee_repo.search_by_vector(vector)
        if match is None or match["score"] < settings.FACE_MATCH_THRESHOLD:
            raise UnauthorizedException("Khuôn mặt không khớp với hồ sơ đã đăng ký")
        if match["user_id"] != user_id:
            raise ForbiddenException("Khuôn mặt không khớp tài khoản đang đăng nhập")

        emp_data = self.employee_repo.get_raw(user_id)
        bio_status = emp_data.get(b"biometric_status", b"approved").decode()
        if bio_status == "pending":
            raise ForbiddenException("Khuôn mặt chưa được duyệt bởi quản lý")
        if bio_status == "rejected":
            raise ForbiddenException("Khuôn mặt bị từ chối, vui lòng đăng ký lại")

        gps_ok = self._check_gps(lat, lng, required=False)

        today = datetime.now().strftime("%Y-%m-%d")
        if self.attendance_repo.exists_for_date(user_id, today):
            raise ConflictException("Bạn đã điểm danh hôm nay rồi")

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        status = self.config_service.compute_checkin_status(now)

        self.attendance_repo.save_checkin(
            user_id=user_id, name=match["name"], department=match["department"],
            position=match["position"], timestamp=timestamp, status=status,
            lat=lat, lng=lng, gps_ok=gps_ok,
        )
        self.employee_repo.set_last_attendance(user_id, today)

        return {
            "name":           match["name"],
            "department":     match["department"],
            "position":       match["position"],
            "timestamp":      timestamp,
            "checkin_status": status,
        }

    # ── CHECK-OUT ────────────────────────────────────────────────────
    def checkout(self, user_id: str, file_contents: bytes,
                  lat: float | None, lng: float | None) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")

        if not self.attendance_repo.exists_for_date(user_id, today):
            raise ValidationException("Bạn chưa điểm danh hôm nay")
        if self.attendance_repo.has_checked_out(user_id, today):
            raise ConflictException("Bạn đã check-out hôm nay rồi")

        vector = self._extract_face_vector(file_contents, "Không nhận diện được khuôn mặt")

        match = self.employee_repo.search_by_vector(vector)
        if (match is None or match["score"] < settings.FACE_MATCH_THRESHOLD
                or match["user_id"] != user_id):
            raise UnauthorizedException("Xác thực khuôn mặt thất bại")

        self._check_gps(lat, lng, required=False)

        checkout_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.attendance_repo.save_checkout(user_id, today, checkout_time, lat=lat, lng=lng)

        return {"checkout_time": checkout_time}

    # ── FACE REGISTRATION ────────────────────────────────────────────
    def register_face(self, user_id: str, file_contents: bytes) -> None:
        if not self.employee_repo.exists(user_id):
            raise NotFoundException("Không tìm thấy hồ sơ nhân viên")

        vector = self._extract_face_vector(
            file_contents,
            "Không nhận diện được khuôn mặt. Đảm bảo khuôn mặt rõ ràng, đủ ánh sáng, nhìn thẳng."
        )
        self.employee_repo.update_face_vector(user_id, vector)

    # ── PROFILE ──────────────────────────────────────────────────────
    def get_profile(self, user_id: str) -> dict:
        data = self.employee_repo.get_raw(user_id)
        if not data:
            raise NotFoundException("Không tìm thấy hồ sơ")

        decoded = {}
        for k, v in data.items():
            key = k.decode() if isinstance(k, bytes) else k
            if key in PERSONAL_FIELDS:
                decoded[key] = v.decode() if isinstance(v, bytes) else v
        return decoded

    # ── MONTHLY STATS ────────────────────────────────────────────────
    def get_monthly_stats(self, user_id: str, year: int, month: int) -> dict:
        if not (1 <= month <= 12):
            raise ValidationException("Tháng không hợp lệ (1–12)")

        total_days = monthrange(year, month)[1]
        today = datetime.now().date()

        records = []
        on_time = 0
        late = 0

        for d in range(1, total_days + 1):
            day_date = datetime(year, month, d).date()
            if day_date > today:
                break

            date_str = day_date.strftime("%Y-%m-%d")
            record = self.attendance_repo.get_record(user_id, date_str)
            if record:
                status = record.get("status", "Đúng giờ")
                if status == "Đi muộn":
                    late += 1
                else:
                    on_time += 1
                records.append({
                    "date":          date_str,
                    "timestamp":     record.get("timestamp", ""),
                    "checkout_time": record.get("checkout_time", ""),
                    "status":        status,
                    "gps_ok":        record.get("gps_ok", "false"),
                })
            else:
                records.append({"date": date_str, "status": "Vắng mặt"})

        present = on_time + late
        days_elapsed = today.day if (year, month) == (today.year, today.month) else total_days
        absent = max(0, min(days_elapsed, total_days) - present)

        return {
            "year":       year,
            "month":      month,
            "total_days": total_days,
            "present":    present,
            "on_time":    on_time,
            "late":       late,
            "absent":     absent,
            "records":    records,
        }

    # ── PERSONAL ATTENDANCE LOG ──────────────────────────────────────
    def get_attendance_log(self, user_id: str, start_date: str, end_date: str) -> dict:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise ValidationException("Định dạng ngày không hợp lệ (cần YYYY-MM-DD)")
        if start > end:
            raise ValidationException("start_date phải <= end_date")

        records = []
        from datetime import timedelta
        day = start
        while day <= end:
            date_str = day.strftime("%Y-%m-%d")
            record = self.attendance_repo.get_record(user_id, date_str)
            if record:
                records.append({
                    "date":          date_str,
                    "timestamp":     record.get("timestamp", ""),
                    "checkout_time": record.get("checkout_time", ""),
                    "status":        record.get("status", "Đúng giờ"),
                    "gps_ok":        record.get("gps_ok", "false"),
                    "lat":           record.get("lat", ""),
                    "lng":           record.get("lng", ""),
                })
            day += timedelta(days=1)

        return {
            "user_id":    user_id,
            "start_date": start_date,
            "end_date":   end_date,
            "total":      len(records),
            "records":    records,
        }
