"""
backend/app/schemas/employee_schema.py
"""

from pydantic import BaseModel


class UpdateEmployeeRequest(BaseModel):
    name:       str
    department: str
    position:   str


class ApproveBiometricRequest(BaseModel):
    status: str  # "approved" | "rejected"


class CheckinResponse(BaseModel):
    name:             str
    department:       str
    position:         str
    timestamp:        str
    checkin_status:   str  # "Đúng giờ" | "Đi muộn"


class CheckoutResponse(BaseModel):
    checkout_time: str
