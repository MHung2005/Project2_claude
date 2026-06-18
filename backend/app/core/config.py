"""
backend/app/core/config.py

Cấu hình tập trung — đọc từ biến môi trường, có giá trị mặc định cho dev.
"""

import os


class Settings:
    # SQLite — đường dẫn file CSDL (thay cho REDIS_HOST/REDIS_PORT cũ)
    DB_PATH: str = os.getenv("DB_PATH", "data/facetime.db")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "sk1234")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_HOURS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "8"))

    # Face recognition
    FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.85"))

    # App
    APP_TITLE: str = "FaceTime & GPS Attendance API"
    APP_VERSION: str = "4.0.0"  # bump: migrate Redis -> SQLite


settings = Settings()