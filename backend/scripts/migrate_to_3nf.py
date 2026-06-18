"""
scripts/migrate_to_3nf.py

Script migration dữ liệu từ schema cũ (vi phạm 3NF) sang schema mới (đạt 3NF).

Chạy MỘT LẦN trước khi deploy phiên bản mới:
    python scripts/migrate_to_3nf.py

Thao tác thực hiện:
  1. employee:{id}  → tách password/username/role/vector_embedding/biometric_status
       → account:{id}  (username, password_hash, role)
       → face:{id}     (vector_embedding, registered_at)
       → employee:{id} chỉ giữ: user_id, name, department, position, email, phone

  2. checkin:{date}:{id} → xóa name, department, position (đổi key timestamp → checkin_time)
       → checkin:{date}:{id} chỉ giữ: user_id, checkin_time, checkin_status,
                                        checkin_lat, checkin_lng, checkin_gps_ok,
                                        checkout_time, checkout_lat, checkout_lng

  3. account_index:{username} → tạo mới từ dữ liệu employee cũ
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis
from datetime import datetime


def get_redis_conn():
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return redis.Redis(host=host, port=port, decode_responses=False)


def migrate_employees(r: redis.Redis) -> dict:
    """
    Tách employee hash thành 3 entity riêng biệt.
    """
    stats = {"total": 0, "accounts_created": 0, "faces_migrated": 0, "errors": []}

    for key in r.scan_iter("employee:*"):
        key_str = key.decode()
        data = r.hgetall(key)
        if not data:
            continue

        stats["total"] += 1
        uid = data.get(b"user_id", b"").decode()
        if not uid:
            stats["errors"].append(f"Key {key_str}: thiếu user_id")
            continue

        try:
            # ── Bước 1: Tạo account:{uid} nếu có username/password ──
            username  = data.get(b"username", b"").decode()
            password  = data.get(b"password", b"").decode()
            role      = data.get(b"role", b"employee").decode()

            if username and password:
                r.hset(f"account:{uid}", mapping={
                    "user_id":       uid.encode(),
                    "username":      username.encode(),
                    "password_hash": password.encode(),   # đã hash từ trước
                    "role":          role.encode(),
                })
                # Index ngược
                r.set(f"account_index:{username}", uid.encode())
                stats["accounts_created"] += 1

            # ── Bước 2: Tạo face:{uid} nếu có vector_embedding ──
            vector_bytes = data.get(b"vector_embedding")
            if vector_bytes:
                registered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                r.hset(f"face:{uid}", mapping={
                    "user_id":          uid.encode(),
                    "vector_embedding": vector_bytes,
                    "registered_at":    registered_at.encode(),
                })
                stats["faces_migrated"] += 1

            # ── Bước 3: Xóa các field không thuộc employee entity ──
            fields_to_remove = [
                b"username", b"password", b"role",
                b"vector_embedding", b"biometric_status", b"last_attendance",
            ]
            existing_fields = [f for f in fields_to_remove if f in data]
            if existing_fields:
                r.hdel(key, *existing_fields)

        except Exception as e:
            stats["errors"].append(f"Key {key_str}: {e}")

    return stats


def migrate_checkins(r: redis.Redis) -> dict:
    """
    Xóa name/department/position khỏi checkin records.
    Đổi tên field: timestamp → checkin_time, status → checkin_status,
                   lat → checkin_lat, lng → checkin_lng, gps_ok → checkin_gps_ok.
    """
    stats = {"total": 0, "migrated": 0, "errors": []}

    for key in r.scan_iter("checkin:*"):
        key_str = key.decode()
        data = r.hgetall(key)
        if not data:
            continue

        stats["total"] += 1
        try:
            pipe = r.pipeline()

            # Xóa các field sao chép từ employee (vi phạm 2NF)
            fields_to_remove = [b"name", b"department", b"position"]
            existing_remove = [f for f in fields_to_remove if f in data]
            if existing_remove:
                pipe.hdel(key, *existing_remove)

            # Đổi tên field cho nhất quán với schema mới
            rename_map = {
                b"timestamp": "checkin_time",
                b"status":    "checkin_status",
                b"lat":       "checkin_lat",
                b"lng":       "checkin_lng",
                b"gps_ok":    "checkin_gps_ok",
            }
            new_fields = {}
            old_fields_to_delete = []
            for old_key, new_name in rename_map.items():
                if old_key in data and new_name.encode() not in data:
                    new_fields[new_name] = data[old_key]
                    old_fields_to_delete.append(old_key)

            if new_fields:
                pipe.hset(key, mapping={k.encode(): v for k, v in new_fields.items()})
            if old_fields_to_delete:
                pipe.hdel(key, *old_fields_to_delete)

            pipe.execute()
            stats["migrated"] += 1

        except Exception as e:
            stats["errors"].append(f"Key {key_str}: {e}")

    return stats


def verify_migration(r: redis.Redis) -> dict:
    """
    Kiểm tra kết quả migration:
    - employee hash không còn chứa username/password/vector_embedding
    - checkin hash không còn chứa name/department/position
    - account:{uid} tồn tại cho mỗi employee có username
    """
    report = {
        "employee_violations": [],
        "checkin_violations": [],
        "missing_accounts": [],
    }

    forbidden_in_employee = {b"username", b"password", b"vector_embedding", b"biometric_status"}
    for key in r.scan_iter("employee:*"):
        data = r.hgetall(key)
        violations = [f.decode() for f in data if f in forbidden_in_employee]
        if violations:
            report["employee_violations"].append({
                "key": key.decode(), "fields": violations
            })

    forbidden_in_checkin = {b"name", b"department", b"position"}
    for key in r.scan_iter("checkin:*"):
        data = r.hgetall(key)
        violations = [f.decode() for f in data if f in forbidden_in_checkin]
        if violations:
            report["checkin_violations"].append({
                "key": key.decode(), "fields": violations
            })

    return report


def main():
    print("=" * 60)
    print("  Migration: Schema cũ → Schema 3NF")
    print("=" * 60)

    r = get_redis_conn()
    try:
        r.ping()
        print("✅ Kết nối Redis thành công\n")
    except Exception as e:
        print(f"❌ Không thể kết nối Redis: {e}")
        sys.exit(1)

    print("▶  Bước 1/2: Migrate employee entities...")
    emp_stats = migrate_employees(r)
    print(f"   Tổng: {emp_stats['total']}, "
          f"Accounts tạo: {emp_stats['accounts_created']}, "
          f"Faces migrate: {emp_stats['faces_migrated']}")
    if emp_stats["errors"]:
        print(f"   ⚠️  Lỗi ({len(emp_stats['errors'])}):")
        for err in emp_stats["errors"][:5]:
            print(f"      - {err}")

    print("\n▶  Bước 2/2: Migrate checkin records...")
    ci_stats = migrate_checkins(r)
    print(f"   Tổng: {ci_stats['total']}, Đã migrate: {ci_stats['migrated']}")
    if ci_stats["errors"]:
        print(f"   ⚠️  Lỗi ({len(ci_stats['errors'])}):")
        for err in ci_stats["errors"][:5]:
            print(f"      - {err}")

    print("\n▶  Kiểm tra kết quả...")
    report = verify_migration(r)
    if report["employee_violations"]:
        print(f"   ❌ employee violations: {len(report['employee_violations'])}")
        for v in report["employee_violations"][:3]:
            print(f"      {v['key']}: {v['fields']}")
    else:
        print("   ✅ employee entities: đạt 3NF")

    if report["checkin_violations"]:
        print(f"   ❌ checkin violations: {len(report['checkin_violations'])}")
        for v in report["checkin_violations"][:3]:
            print(f"      {v['key']}: {v['fields']}")
    else:
        print("   ✅ checkin records: đạt 3NF")

    print("\n" + "=" * 60)
    if not report["employee_violations"] and not report["checkin_violations"]:
        print("✅ Migration hoàn tất — Schema đạt chuẩn 3NF")
    else:
        print("⚠️  Migration hoàn tất nhưng còn một số violations — kiểm tra lại")
    print("=" * 60)


if __name__ == "__main__":
    main()