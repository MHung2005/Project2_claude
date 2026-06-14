"""
backend/app/services/employee_service.py

Business logic cho các chức năng của Nhân viên (Employee):
  - Chấm công vào / ra (Face Recognition + GPS) — chỉ so khớp vector của chính user
  - Đăng ký / cập nhật khuôn mặt (tự động approved, không cần duyệt)
  - Đổi mật khẩu
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
from ..core.security import verify_password, hash_password
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
        if lat is None or lng is None:
            if required:
                raise ForbiddenException("Cần cung cấp vị trí GPS để chấm công")
            return False
        loc = self.config_service.config_repo.get_location()
        if loc and not is_within_radius(lat, lng, loc["lat"], loc["lng"], loc["radius"]):
            raise ForbiddenException("Bạn không trong phạm vi cho phép điểm danh")
        return True

    def _verify_face_against_user(self, query_vector: np.ndarray, user_id: str) -> None:
        """
        So khớp vector khuôn mặt CHỈ với vector đã đăng ký của chính user_id đó.
        Raise UnauthorizedException nếu không khớp hoặc chưa đăng ký.
        """
        stored_vector = self.employee_repo.get_face_vector(user_id)
        if stored_vector is None:
            raise ForbiddenException(
                "Bạn chưa đăng ký khuôn mặt. Vui lòng đăng ký trước khi điểm danh."
            )
        similarity = self.employee_repo.cosine_similarity(query_vector, stored_vector)
        if similarity < settings.FACE_MATCH_THRESHOLD:
            raise UnauthorizedException(
                f"Khuôn mặt không khớp (độ tương đồng: {similarity:.2f}). "
                "Vui lòng thử lại với điều kiện ánh sáng tốt hơn."
            )

    # ── CHANGE PASSWORD ──────────────────────────────────────────────
    def change_password(self, user_id: str, old_password: str, new_password: str) -> None:
        data = self.employee_repo.get_raw(user_id)
        if not data:
            raise NotFoundException("Không tìm thấy hồ sơ nhân viên")

        stored_hash = data.get(b"password", b"").decode()
        if not stored_hash or not verify_password(old_password, stored_hash):
            raise UnauthorizedException("Mật khẩu hiện tại không đúng")

        if len(new_password) < 6:
            raise ValidationException("Mật khẩu mới phải có ít nhất 6 ký tự")

        self.employee_repo.update_password(user_id, hash_password(new_password))

    # ── CHECK-IN ─────────────────────────────────────────────────────
    def checkin(self, user_id: str, file_contents: bytes,
                lat: float | None, lng: float | None) -> dict:
        # 1. Trích xuất vector từ ảnh chụp
        query_vector = self._extract_face_vector(
            file_contents,
            "Không nhận diện được khuôn mặt. Vui lòng đảm bảo khuôn mặt rõ ràng, đủ ánh sáng."
        )

        # 2. Chỉ so khớp với vector của chính user này (không tìm kiếm toàn bộ DB)
        self._verify_face_against_user(query_vector, user_id)

        # 3. Kiểm tra GPS
        gps_ok = self._check_gps(lat, lng, required=False)

        # 4. Kiểm tra đã điểm danh chưa
        today = datetime.now().strftime("%Y-%m-%d")
        if self.attendance_repo.exists_for_date(user_id, today):
            raise ConflictException("Bạn đã điểm danh hôm nay rồi")

        # 5. Lấy thông tin nhân viên để lưu bản ghi
        raw = self.employee_repo.get_raw(user_id)
        if not raw:
            raise NotFoundException("Không tìm thấy hồ sơ nhân viên")
        name       = raw.get(b"name", b"").decode()
        department = raw.get(b"department", b"").decode()
        position   = raw.get(b"position", b"").decode()

        # 6. Tính trạng thái & lưu
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        status = self.config_service.compute_checkin_status(now)

        self.attendance_repo.save_checkin(
            user_id=user_id, name=name, department=department,
            position=position, timestamp=timestamp, status=status,
            lat=lat, lng=lng, gps_ok=gps_ok,
        )
        self.employee_repo.set_last_attendance(user_id, today)

        return {
            "name":           name,
            "department":     department,
            "position":       position,
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

        # So khớp chỉ với vector của chính user
        query_vector = self._extract_face_vector(file_contents, "Không nhận diện được khuôn mặt")
        self._verify_face_against_user(query_vector, user_id)

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
        # update_face_vector tự set biometric_status = "approved"
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
            end   = datetime.strptime(end_date,   "%Y-%m-%d")
        except ValueError:
            raise ValidationException("Định dạng ngày không hợp lệ (cần YYYY-MM-DD)")
        if start > end:
            raise ValidationException("start_date phải <= end_date")

        from datetime import timedelta
        records = []
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