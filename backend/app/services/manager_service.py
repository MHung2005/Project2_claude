"""
backend/app/services/manager_service.py  (3NF Refactor)

Thay đổi quan trọng:

1. create_employee():
   - Tách thành 2 bước: create employee record + save face vector
   - employee_repo.create_employee() chỉ nhận thông tin nhân sự
   - employee_repo.save_face_vector() lưu riêng tại face:{user_id}

2. bulk_import_employees():
   - employee_repo.create_employee() không nhận username/password
   - employee_repo.attach_account() lưu xác thực tại account:{user_id}

3. get_daily_analytics():
   - attendance record chỉ có FK + event data
   - JOIN với employee để lấy name/department/position khi build response
   - Đây là pattern "JOIN at read time" — chuẩn 3NF
"""

import io
import secrets
import string
from datetime import datetime

import numpy as np
import cv2

from ..core.response import NotFoundException, ValidationException
from ..core.security import hash_password
from ..repositories.employee_repository import EmployeeRepository
from ..repositories.attendance_repository import AttendanceRepository
from .ai.embeddings import FaceEmbeddingService

# ── Column mapping cho bulk import ──────────────────────────────────────
COLUMN_MAP = {
    "user_id": "user_id", "mã nv": "user_id", "id": "user_id", "employee_id": "user_id",
    "name": "name", "họ tên": "name", "tên": "name", "full_name": "name",
    "department": "department", "phòng ban": "department", "phòng": "department",
    "position": "position", "chức vụ": "position", "vị trí": "position",
    "phone": "phone", "số điện thoại": "phone", "điện thoại": "phone", "sdt": "phone",
    "email": "email",
    "username": "username", "tên đăng nhập": "username",
    "password": "password", "mật khẩu": "password",
}

PASSWORD_LENGTH   = 10
PASSWORD_ALPHABET = string.ascii_letters + string.digits


def _generate_password(length: int = PASSWORD_LENGTH) -> str:
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


class ManagerService:
    def __init__(self):
        self.employee_repo   = EmployeeRepository()
        self.attendance_repo = AttendanceRepository()
        self.face_embed      = FaceEmbeddingService()

    # ── HELPERS ──────────────────────────────────────────────────────

    @staticmethod
    def _decode_image(contents: bytes):
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValidationException("Ảnh không hợp lệ")
        return img

    # ── EMPLOYEE CRUD ────────────────────────────────────────────────

    def create_employee(self, user_id: str, name: str, department: str,
                         position: str, file_contents: bytes) -> None:
        """
        Tách thành 2 thao tác ghi riêng biệt:
          1. employee:{user_id}  — thông tin nhân sự
          2. face:{user_id}      — vector sinh trắc học
        """
        img = self._decode_image(file_contents)
        vector = self.face_embed.embedding_img(img)
        if vector is None:
            raise ValidationException(
                "Không thể nhận diện khuôn mặt. Đảm bảo khuôn mặt rõ ràng, "
                "đủ ánh sáng và nhìn thẳng vào camera."
            )
        # [Entity 1] Lưu thông tin nhân sự
        self.employee_repo.create_employee(user_id, {
            "name": name, "department": department, "position": position,
        })
        # [Entity 3] Lưu face vector riêng biệt
        self.employee_repo.save_face_vector(user_id, vector)

    def list_employees(self, search: str = "") -> dict:
        employees = self.employee_repo.get_all()
        if search:
            q = search.lower()
            employees = [
                e for e in employees
                if q in e.get("name", "").lower()
                or q in e.get("department", "").lower()
                or q in e.get("position", "").lower()
                or q in e.get("user_id", "").lower()
            ]
        return {"total": len(employees), "employees": employees}

    def delete_employee(self, user_id: str) -> None:
        """Cascade delete: employee + account + face."""
        if not self.employee_repo.delete_employee(user_id):
            raise NotFoundException("Không tìm thấy nhân viên")

    def update_employee(self, user_id: str, name: str, department: str, position: str) -> None:
        if not self.employee_repo.update_employee(user_id, name, department, position):
            raise NotFoundException("Không tìm thấy nhân viên")

    # ── BULK IMPORT ───────────────────────────────────────────────────

    def bulk_import_employees(self, contents: bytes, ext: str) -> dict:
        if ext not in ("xlsx", "xls", "csv"):
            raise ValidationException("Chỉ hỗ trợ file .xlsx, .xls hoặc .csv")

        try:
            rows = self._parse_spreadsheet(contents, ext)
        except Exception as e:
            raise ValidationException(f"Không thể đọc file: {e}")

        if not rows:
            raise ValidationException("File không có dữ liệu hợp lệ")

        for row in rows:
            username = row.get("username", "").strip() or row.get("user_id", "").strip()
            row["username"] = username
            plain_pw = (row.get("password") or "").strip() or _generate_password()
            row["generated_password"] = plain_pw
            row["hashed_password"]    = hash_password(plain_pw)

        created, skipped, errors = [], [], []
        for emp in rows:
            user_id = emp.get("user_id", "").strip()
            name    = emp.get("name", "").strip()
            if not user_id or not name:
                errors.append({"row": emp, "reason": "Thiếu user_id hoặc tên"})
                continue
            if self.employee_repo.exists(user_id):
                skipped.append(user_id)
                continue
            try:
                # [Entity 1] Tạo hồ sơ nhân sự
                self.employee_repo.create_employee(user_id, emp)

                # [Entity 2] Tạo tài khoản xác thực — tách biệt
                username  = emp.get("username", "").strip()
                hashed_pw = emp.get("hashed_password", "")
                if username and hashed_pw:
                    self.employee_repo.attach_account(user_id, username, hashed_pw)

                created.append({
                    "user_id":  user_id,
                    "name":     name,
                    "username": username,
                    "password": emp.get("generated_password", ""),
                    "department": emp.get("department", ""),
                })
            except Exception as e:
                errors.append({"row": emp, "reason": str(e)})

        preview = [
            {k: v for k, v in row.items() if k != "hashed_password"}
            for row in rows[:10]
        ]

        return {
            "total_rows":    len(rows),
            "created_count": len(created),
            "skipped_count": len(skipped),
            "error_count":   len(errors),
            "created":       created,
            "skipped":       skipped,
            "errors":        errors,
            "preview":       preview,
        }

    @staticmethod
    def _parse_spreadsheet(contents: bytes, ext: str) -> list[dict]:
        if ext in ("xlsx", "xls"):
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)
        else:
            import csv
            text = contents.decode("utf-8-sig", errors="replace")
            reader = csv.reader(io.StringIO(text))
            rows_iter = iter(reader)

        header_raw = next(rows_iter, None)
        if header_raw is None:
            return []

        header        = [str(h).strip().lower() if h is not None else "" for h in header_raw]
        mapped_header = [COLUMN_MAP.get(col, col) for col in header]

        records = []
        for row in rows_iter:
            if all(v is None or str(v).strip() == "" for v in row):
                continue
            record = {}
            for col_name, val in zip(mapped_header, row):
                if col_name:
                    record[col_name] = str(val).strip() if val is not None else ""
            records.append(record)
        return records

    # ── ATTENDANCE / ANALYTICS ───────────────────────────────────────

    def get_attendance(self, date: str | None = None) -> dict:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        # attendance records chỉ có FK + event data
        raw_records = self.attendance_repo.get_by_date(date)
        # JOIN với employee để lấy thông tin nhân sự
        enriched = self._enrich_attendance_records(raw_records)
        return {"date": date, "total": len(enriched), "records": enriched}

    def get_daily_analytics(self, date: str | None = None, search: str = "") -> dict:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        all_employees = self.employee_repo.get_all()
        total         = len(all_employees)
        checkin_map   = self.attendance_repo.get_map_by_date(date)

        present = len(checkin_map)
        on_time = sum(1 for r in checkin_map.values() if r.get("checkin_status") == "Đúng giờ")
        late    = sum(1 for r in checkin_map.values() if r.get("checkin_status") == "Đi muộn")
        absent  = max(0, total - present)

        records = []
        for emp in all_employees:
            uid = emp["user_id"]
            if uid in checkin_map:
                r = checkin_map[uid]
                # JOIN: ghép thông tin nhân sự (từ employee entity) với event data (từ attendance entity)
                records.append({
                    **emp,                                          # name, dept, pos (từ employee)
                    "checkin_time":  r.get("checkin_time", ""),    # event fields (từ attendance)
                    "checkout_time": r.get("checkout_time", ""),
                    "status":        r.get("checkin_status", "Đúng giờ"),
                    "gps_ok":        r.get("checkin_gps_ok", "false"),
                })
            else:
                records.append({
                    **emp,
                    "checkin_time":  "",
                    "checkout_time": "",
                    "status":        "Vắng mặt",
                    "gps_ok":        "false",
                })

        if search:
            q = search.lower()
            records = [
                r for r in records
                if q in r.get("name", "").lower() or q in r.get("department", "").lower()
            ]

        return {
            "date":            date,
            "total_employees": total,
            "present":         present,
            "on_time":         on_time,
            "late":            late,
            "absent":          absent,
            "records":         records,
        }

    def get_stats_summary(self) -> dict:
        today    = datetime.now().strftime("%Y-%m-%d")
        analytics = self.get_daily_analytics(today)
        total    = analytics["total_employees"]
        return {
            "today":   analytics["present"],
            "total":   total,
            "absent":  analytics["absent"],
            "late":    analytics["late"],
            "on_time": analytics["on_time"],
            "rate":    round((analytics["present"] / total * 100) if total > 0 else 0),
        }

    def get_weekly_checkins(self) -> list[dict]:
        return self.attendance_repo.get_weekly()

    def get_checkins_range(self, start_date: str, end_date: str) -> list[dict]:
        return self.attendance_repo.count_by_range(start_date, end_date)

    # ── PRIVATE JOIN HELPER ──────────────────────────────────────────

    def _enrich_attendance_records(self, raw_records: list[dict]) -> list[dict]:
        """
        JOIN attendance records với employee data.
        Pattern này thay thế việc lưu name/dept/pos trực tiếp trong checkin hash.
        """
        enriched = []
        for rec in raw_records:
            uid = rec.get("user_id", "")
            emp = self.employee_repo.get_employee(uid) if uid else {}
            enriched.append({
                # Thông tin nhân sự từ employee entity
                "user_id":    uid,
                "name":       (emp or {}).get("name", ""),
                "department": (emp or {}).get("department", ""),
                "position":   (emp or {}).get("position", ""),
                # Event data từ attendance entity
                "checkin_time":  rec.get("checkin_time", ""),
                "checkout_time": rec.get("checkout_time", ""),
                "status":        rec.get("checkin_status", ""),
                "gps_ok":        rec.get("checkin_gps_ok", "false"),
            })
        return enriched