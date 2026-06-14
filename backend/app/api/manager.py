"""
backend/app/api/manager.py

Controller — chức năng của Quản lý (Manager):
  - Employee CRUD            : /manager/employees
  - Bulk import               : /manager/employees/bulk-import
  - Biometric approval        : /manager/employees/pending, /approve
  - Attendance records         : /manager/attendance
  - Analytics                 : /manager/analytics/daily, /stats, /stats/weekly, /stats/range
  - Location config            : /manager/location
  - Schedule config            : /manager/schedule
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, Query

from ..core.response import success_response
from ..core.security import get_current_manager
from ..schemas.employee_schema import UpdateEmployeeRequest, ApproveBiometricRequest
from ..schemas.config_schema import LocationConfigRequest, ScheduleConfigRequest
from ..services.manager_service import ManagerService
from ..services.config_service import ConfigService

manager_router = APIRouter(prefix="/manager", tags=["Manager"])
manager_service = ManagerService()
config_service = ConfigService()


# ─────────────────────────────────────────────────────────────────────────
# EMPLOYEE CRUD
# ─────────────────────────────────────────────────────────────────────────
@manager_router.post("/employees")
async def create_employee(
    user_id:    str = Form(...),
    name:       str = Form(...),
    department: str = Form(...),
    position:   str = Form(...),
    file: UploadFile = File(...),
    current_manager: dict = Depends(get_current_manager),
):
    contents = await file.read()
    manager_service.create_employee(user_id, name, department, position, contents)
    return success_response(f"Đã đăng ký khuôn mặt cho {name}")


@manager_router.get("/employees")
def list_employees(
    search: str = Query(default="", description="Tìm kiếm theo tên, phòng ban, chức vụ"),
    current_manager: dict = Depends(get_current_manager),
):
    data = manager_service.list_employees(search)
    return success_response("OK", data)


@manager_router.delete("/employees/{user_id}")
def delete_employee(user_id: str, current_manager: dict = Depends(get_current_manager)):
    manager_service.delete_employee(user_id)
    return success_response(f"Đã xóa nhân viên {user_id}")


@manager_router.put("/employees/{user_id}")
def update_employee(
    user_id: str,
    body: UpdateEmployeeRequest,
    current_manager: dict = Depends(get_current_manager),
):
    manager_service.update_employee(user_id, body.name, body.department, body.position)
    return success_response("Đã cập nhật thông tin")


# ─────────────────────────────────────────────────────────────────────────
# BULK IMPORT via Excel / CSV
# ─────────────────────────────────────────────────────────────────────────
@manager_router.post("/employees/bulk-import")
async def bulk_import_employees(
    file: UploadFile = File(...),
    current_manager: dict = Depends(get_current_manager),
):
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    contents = await file.read()

    data = manager_service.bulk_import_employees(contents, ext)
    return success_response("Import hoàn tất", data)


# ─────────────────────────────────────────────────────────────────────────
# BIOMETRIC APPROVAL
# ─────────────────────────────────────────────────────────────────────────
@manager_router.get("/employees/pending")
def get_pending(current_manager: dict = Depends(get_current_manager)):
    data = manager_service.get_pending_employees()
    return success_response("OK", data)


@manager_router.put("/employees/{user_id}/approve")
def approve_employee(
    user_id: str,
    body: ApproveBiometricRequest,
    current_manager: dict = Depends(get_current_manager),
):
    manager_service.approve_biometric(user_id, body.status)
    return success_response("Đã cập nhật trạng thái xác thực khuôn mặt")


# ─────────────────────────────────────────────────────────────────────────
# ATTENDANCE RECORDS
# ─────────────────────────────────────────────────────────────────────────
@manager_router.get("/attendance")
def get_attendance(
    date: str = None,
    current_manager: dict = Depends(get_current_manager),
):
    data = manager_service.get_attendance(date)
    return success_response("OK", data)


# ─────────────────────────────────────────────────────────────────────────
# ANALYTICS — DAILY
# ─────────────────────────────────────────────────────────────────────────
@manager_router.get("/analytics/daily")
def get_daily_analytics(
    date: str = Query(default=None, description="YYYY-MM-DD, mặc định hôm nay"),
    search: str = Query(default="", description="Tìm kiếm tên / phòng ban"),
    current_manager: dict = Depends(get_current_manager),
):
    data = manager_service.get_daily_analytics(date, search)
    return success_response("OK", data)


# ─────────────────────────────────────────────────────────────────────────
# LEGACY STATS ENDPOINTS (kept for backward compat)
# ─────────────────────────────────────────────────────────────────────────
@manager_router.get("/stats")
def get_stats(current_manager: dict = Depends(get_current_manager)):
    data = manager_service.get_stats_summary()
    return success_response("OK", data)


@manager_router.get("/stats/weekly")
def get_weekly(current_manager: dict = Depends(get_current_manager)):
    data = manager_service.get_weekly_checkins()
    return success_response("OK", {"data": data})


@manager_router.get("/stats/range")
def get_checkins_range(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date:   str = Query(..., description="YYYY-MM-DD"),
    current_manager: dict = Depends(get_current_manager),
):
    data = manager_service.get_checkins_range(start_date, end_date)
    return success_response("OK", {"data": data})


# ─────────────────────────────────────────────────────────────────────────
# LOCATION CONFIG
# ─────────────────────────────────────────────────────────────────────────
@manager_router.put("/location")
def set_location(body: LocationConfigRequest, current_manager: dict = Depends(get_current_manager)):
    config_service.set_location(body.lat, body.lng, body.radius)
    return success_response("Đã cập nhật vị trí điểm danh")


@manager_router.get("/location")
def get_location(current_manager: dict = Depends(get_current_manager)):
    data = config_service.get_location()
    return success_response("OK", data)


# ─────────────────────────────────────────────────────────────────────────
# SCHEDULE CONFIG
# ─────────────────────────────────────────────────────────────────────────
@manager_router.get("/schedule")
def get_schedule(current_manager: dict = Depends(get_current_manager)):
    data = config_service.get_schedule()
    return success_response("OK", data)


@manager_router.put("/schedule")
def set_schedule(body: ScheduleConfigRequest, current_manager: dict = Depends(get_current_manager)):
    config_service.set_schedule(body.start_time, body.end_time, body.grace_minutes)
    return success_response("Đã cập nhật lịch làm việc")
