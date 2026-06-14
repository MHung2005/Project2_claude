"""
backend/app/schemas/config_schema.py
"""

from pydantic import BaseModel


class LocationConfigRequest(BaseModel):
    lat:    float
    lng:    float
    radius: float = 200


class ScheduleConfigRequest(BaseModel):
    start_time:    str  # "HH:MM"
    end_time:      str  # "HH:MM"
    grace_minutes: int = 0
