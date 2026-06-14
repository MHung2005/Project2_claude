"""
backend/app/services/gps_service.py

Tính toán khoảng cách GPS (Haversine formula) — dùng để kiểm tra
nhân viên có đang trong bán kính cho phép chấm công hay không.
"""

from math import radians, sin, cos, sqrt, atan2

EARTH_RADIUS_M = 6_371_000  # mét


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Trả về khoảng cách (mét) giữa 2 toạ độ GPS."""
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lng2 - lng1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return EARTH_RADIUS_M * 2 * atan2(sqrt(a), sqrt(1 - a))


def is_within_radius(user_lat: float, user_lng: float,
                      center_lat: float, center_lng: float,
                      radius_m: float) -> bool:
    return haversine(user_lat, user_lng, center_lat, center_lng) <= radius_m
