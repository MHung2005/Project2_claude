"""
backend/app/services/employee_service.py  (3NF Refactor)

Thay đổi quan trọng so với phiên bản cũ:

1. checkin() / checkout():
   - Không truyền name/department/position vào save_checkin()
   - Sau khi lưu, JOIN với employee repo để trả về response
   - attendance_repo.save_checkin() chỉ nhận: user_id, checkin_time, status, lat, lng, gps_ok

2. register_face():
   - Gọi employee_repo.save_face_vector() thay vì update_face_vector()
   - Không cần cập nhật biometric_status (được tính tự động từ key existence)

3. get_profile():
   - Đọc từ employee_repo.get_employee() — trả về biometric_status tính toán
   - KHÔNG đọc password/username từ employee hash (chúng không còn ở đó)

4. get_monthly_stats() / get_attendance_log():
   - Record từ attendance chỉ có event fields
   - JOIN employee để lấy name nếu cần (hiện tại không cần vì endpoint trả về cho chính user)

5. change_password():
   - Đọc/ghi từ account:{user_id} thay vì employee:{user_id}
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


class EmployeeService:
    def __init__(self):
        self.employee_repo  = EmployeeRepository()
        self.attendance_repo = AttendanceRepository()
        self.config_service  = ConfigService()
        self.face_embed      = FaceEmbeddingService()

    # ── HELPERS ──────────────────────────────────────────────────────

    @staticmethod
    def _decode_image(contents: bytes):
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValidationException("Ảnh không hợp lệ")
        return img

    def _extract_face_vector(self, contents: bytes, on_fail_message: str) -> np.ndarray:
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
        So khớp vector với face:{user_id}.
        FaceVector đã tách thành entity riêng → đọc từ employee_repo.get_face_vector().
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

    def _get_employee_or_404(self, user_id: str) -> dict:
        emp = self.employee_repo.get_employee(user_id)
        if not emp:
            raise NotFoundException("Không tìm thấy hồ sơ nhân viên")
        return emp

    # ── CHANGE PASSWORD ──────────────────────────────────────────────

    def change_password(self, user_id: str, old_password: str, new_password: str) -> None:
        """
        ĐỌC từ account:{user_id} (entity Account tách biệt),
        KHÔNG đọc từ employee:{user_id} như phiên bản cũ.
        """
        account = self.employee_repo.get_account_by_userid(user_id)
        if not account:
            raise NotFoundException("Không tìm thấy tài khoản")

        stored_hash = account.get("password_hash", "")
        if not stored_hash or not verify_password(old_password, stored_hash):
            raise UnauthorizedException("Mật khẩu hiện tại không đúng")

        if len(new_password) < 6:
            raise ValidationException("Mật khẩu mới phải có ít nhất 6 ký tự")

        self.employee_repo.update_password(user_id, hash_password(new_password))

    # ── CHECK-IN ─────────────────────────────────────────────────────

    def checkin(self, user_id: str, file_contents: bytes,
                lat: float | None, lng: float | None) -> dict:
        # 1. Nhận diện khuôn mặt — đọc từ face:{user_id}
        query_vector = self._extract_face_vector(
            file_contents,
            "Không nhận diện được khuôn mặt. Đảm bảo khuôn mặt rõ ràng, đủ ánh sáng."
        )
        self._verify_face_against_user(query_vector, user_id)

        # 2. Kiểm tra GPS
        gps_ok = self._check_gps(lat, lng, required=False)

        # 3. Kiểm tra chưa điểm danh hôm nay
        today = datetime.now().strftime("%Y-%m-%d")
        if self.attendance_repo.exists_for_date(user_id, today):
            raise ConflictException("Bạn đã điểm danh hôm nay rồi")

        # 4. Lấy thông tin nhân sự để trả về response (JOIN — không lưu vào checkin record)
        emp = self._get_employee_or_404(user_id)

        # 5. Lưu checkin — CHỈ lưu user_id (FK) + event data, KHÔNG copy name/dept/pos
        now = datetime.now()
        checkin_time = now.strftime("%Y-%m-%d %H:%M:%S")
        status = self.config_service.compute_checkin_status(now)

        self.attendance_repo.save_checkin(
            user_id=user_id,
            checkin_time=checkin_time,
            checkin_status=status,
            lat=lat,
            lng=lng,
            gps_ok=gps_ok,
        )

        # 6. Trả về response bằng cách JOIN employee data (không lưu lại vào DB)
        return {
            "name":           emp["name"],
            "department":     emp["department"],
            "position":       emp["position"],
            "timestamp":      checkin_time,
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

        query_vector = self._extract_face_vector(file_contents, "Không nhận diện được khuôn mặt")
        self._verify_face_against_user(query_vector, user_id)
        self._check_gps(lat, lng, required=False)

        checkout_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.attendance_repo.save_checkout(user_id, today, checkout_time, lat=lat, lng=lng)

        return {"checkout_time": checkout_time}

    # ── FACE REGISTRATION ────────────────────────────────────────────

    def register_face(self, user_id: str, file_contents: bytes) -> None:
        """
        Lưu face vector tại face:{user_id} — entity riêng biệt.
        biometric_status không cần cập nhật thủ công:
        → được tính tự động khi đọc employee (exists face:{user_id}).
        """
        if not self.employee_repo.exists(user_id):
            raise NotFoundException("Không tìm thấy hồ sơ nhân viên")

        vector = self._extract_face_vector(
            file_contents,
            "Không nhận diện được khuôn mặt. Đảm bảo khuôn mặt rõ ràng, đủ ánh sáng, nhìn thẳng."
        )
        # Lưu vào face:{user_id} — KHÔNG đụng đến employee hash
        self.employee_repo.save_face_vector(user_id, vector)

    # ── PROFILE ──────────────────────────────────────────────────────

    def get_profile(self, user_id: str) -> dict:
        """
        Đọc employee:{user_id} cho thông tin nhân sự.
        biometric_status được tính từ sự tồn tại của face:{user_id}.
        last_attendance được tính từ attendance records (không lưu trong employee).
        """
        emp = self._get_employee_or_404(user_id)

        # Tính last_attendance từ Attendance (derived attribute — không lưu trong employee)
        last_attendance = self._compute_last_attendance(user_id)
        emp["last_attendance"] = last_attendance

        return emp

    def _compute_last_attendance(self, user_id: str) -> str:
        """
        Tính last_attendance bằng cách scan 30 ngày gần nhất.
        Đây là derived attribute — không lưu trong employee hash (tránh vi phạm 3NF).
        """
        today = datetime.now()
        for i in range(30):
            date_str = (today.replace(hour=0, minute=0, second=0)
                        .__class__(today.year, today.month, today.day)
                        .__class__.fromordinal(today.toordinal() - i)
                        .strftime("%Y-%m-%d"))
            if self.attendance_repo.exists_for_date(user_id, date_str):
                return date_str
        return ""

    # ── MONTHLY STATS ────────────────────────────────────────────────

    def get_monthly_stats(self, user_id: str, year: int, month: int) -> dict:
        if not (1 <= month <= 12):
            raise ValidationException("Tháng không hợp lệ (1–12)")

        total_days = monthrange(year, month)[1]
        today = datetime.now().date()
        records = []
        on_time = late = 0

        for d in range(1, total_days + 1):
            day_date = datetime(year, month, d).date()
            if day_date > today:
                break
            date_str = day_date.strftime("%Y-%m-%d")
            rec = self.attendance_repo.get_record(user_id, date_str)
            if rec:
                # attendance record chỉ có event fields — không có name/dept (đúng 3NF)
                status = rec.get("checkin_status", "Đúng giờ")
                if status == "Đi muộn":
                    late += 1
                else:
                    on_time += 1
                records.append({
                    "date":          date_str,
                    "timestamp":     rec.get("checkin_time", ""),
                    "checkout_time": rec.get("checkout_time", ""),
                    "status":        status,
                    "gps_ok":        rec.get("checkin_gps_ok", "false"),
                })
            else:
                records.append({"date": date_str, "status": "Vắng mặt"})

        present = on_time + late
        days_elapsed = today.day if (year, month) == (today.year, today.month) else total_days
        absent = max(0, min(days_elapsed, total_days) - present)

        return {
            "year": year, "month": month, "total_days": total_days,
            "present": present, "on_time": on_time, "late": late,
            "absent": absent, "records": records,
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
            rec = self.attendance_repo.get_record(user_id, date_str)
            if rec:
                records.append({
                    "date":          date_str,
                    "timestamp":     rec.get("checkin_time", ""),
                    "checkout_time": rec.get("checkout_time", ""),
                    "status":        rec.get("checkin_status", "Đúng giờ"),
                    "gps_ok":        rec.get("checkin_gps_ok", "false"),
                    "lat":           rec.get("checkin_lat", ""),
                    "lng":           rec.get("checkin_lng", ""),
                })
            day += timedelta(days=1)

        return {
            "user_id":    user_id,
            "start_date": start_date,
            "end_date":   end_date,
            "total":      len(records),
            "records":    records,
        }