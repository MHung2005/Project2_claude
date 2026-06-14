"""
backend/app/api/employee.py

Controller — chức năng của Nhân viên (Employee):
  - POST /employee/checkin        (Face + GPS)
  - POST /employee/checkout       (Face + GPS)
  - POST /employee/register-face  (đăng ký / cập nhật khuôn mặt)
  - GET  /employee/profile         (hồ sơ cá nhân)
  - GET  /employee/stats/monthly   (thống kê theo tháng)
  - GET  /employee/attendance      (lịch sử chấm công cá nhân)
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, Query

from ..core.response import success_response
from ..core.security import get_current_employee
from ..services.employee_service import EmployeeService

employee_router = APIRouter(prefix="/employee", tags=["Employee"])
employee_service = EmployeeService()


# ── CHECK-IN ─────────────────────────────────────────────────────────────
@employee_router.post("/checkin")
async def checkin(
    file: UploadFile = File(...),
    lat:  float | None = Form(None),
    lng:  float | None = Form(None),
    current_employee: dict = Depends(get_current_employee),
):
    user_id = current_employee["user_id"]
    contents = await file.read()
    data = employee_service.checkin(user_id, contents, lat, lng)
    return success_response(f"Điểm danh thành công — {data['checkin_status']}", data)


# ── CHECK-OUT ────────────────────────────────────────────────────────────
@employee_router.post("/checkout")
async def checkout(
    file: UploadFile = File(...),
    lat:  float | None = Form(None),
    lng:  float | None = Form(None),
    current_employee: dict = Depends(get_current_employee),
):
    user_id = current_employee["user_id"]
    contents = await file.read()
    data = employee_service.checkout(user_id, contents, lat, lng)
    return success_response("Check-out thành công", data)


# ── REGISTER / UPDATE FACE ───────────────────────────────────────────────
@employee_router.post("/register-face")
async def register_face(
    file: UploadFile = File(...),
    current_employee: dict = Depends(get_current_employee),
):
    user_id = current_employee["user_id"]
    contents = await file.read()
    employee_service.register_face(user_id, contents)
    return success_response("Đã cập nhật khuôn mặt, chờ quản lý phê duyệt")


# ── PROFILE ──────────────────────────────────────────────────────────────
@employee_router.get("/profile")
def get_profile(current_employee: dict = Depends(get_current_employee)):
    data = employee_service.get_profile(current_employee["user_id"])
    return success_response("OK", data)


# ── MONTHLY STATS ────────────────────────────────────────────────────────
@employee_router.get("/stats/monthly")
def get_monthly_stats(
    year:  int = Query(default=None),
    month: int = Query(default=None),
    current_employee: dict = Depends(get_current_employee),
):
    from datetime import datetime
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    data = employee_service.get_monthly_stats(current_employee["user_id"], year, month)
    return success_response("OK", data)


# ── PERSONAL ATTENDANCE LOG ──────────────────────────────────────────────
@employee_router.get("/attendance")
def get_personal_attendance(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date:   str = Query(..., description="YYYY-MM-DD"),
    current_employee: dict = Depends(get_current_employee),
):
    data = employee_service.get_attendance_log(current_employee["user_id"], start_date, end_date)
    return success_response("OK", data)
