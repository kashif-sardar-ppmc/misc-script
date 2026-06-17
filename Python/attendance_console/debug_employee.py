# debug_employee.py
# Run: python debug_employee.py
#
# Edit these two values:
TARGET_ATTENDANCE_ID = "72"   # <-- the card/attendance ID of the affected employee
TARGET_DATE = "2026-04-16"

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from attendance_sync_service import (
    get_hikvision_events_range,
    load_emp_map,
)

LOCAL_TZ = ZoneInfo("Asia/Karachi")

print(f"\n{'='*55}")
print(f"  DEBUG: attendance_id={TARGET_ATTENDANCE_ID}  date={TARGET_DATE}")
print(f"{'='*55}\n")

# ── STAGE 1: Fetch raw events ─────────────────────────────
print("[STAGE 1] Fetching raw events from devices...")
raw = get_hikvision_events_range(TARGET_DATE, TARGET_DATE)
print(f"  Total raw events fetched: {len(raw)}")

# ── STAGE 2: Find this employee in raw events ─────────────
print(f"\n[STAGE 2] Searching raw events for attendance_id={TARGET_ATTENDANCE_ID}...")
matches = []
for ev in raw:
    emp_id = str(ev.get("employeeNoString") or ev.get("employeeNo") or "").strip()
    if emp_id == TARGET_ATTENDANCE_ID:
        matches.append(ev)

if not matches:
    print("  ❌ NOT FOUND in raw events.")
    print("     Possible causes:")
    print("     - Device was offline on that date")
    print("     - Employee punched on a device not in DEVICE_URLS")
    print("     - The attendance_id field name differs (check keys below)")
    if raw:
        print(f"\n     Sample event keys: {list(raw[0].keys())}")
        print(f"     Sample event: {json.dumps(raw[0], indent=4)}")
else:
    print(f"  ✔ Found {len(matches)} punch(es) for this employee:")
    for ev in matches:
        print(f"     time={ev.get('time')}  raw={json.dumps(ev)}")

# ── STAGE 3: Check emp_map ────────────────────────────────
print(f"\n[STAGE 3] Checking emp_map lookup...")
emp_map = load_emp_map()
emp_no = emp_map.get(TARGET_ATTENDANCE_ID)
if emp_no is None:
    print(f"  ❌ attendance_id '{TARGET_ATTENDANCE_ID}' NOT in employee table.")
    print(f"     Total mapped IDs: {len(emp_map)}")
    print(f"     Sample mapped IDs: {list(emp_map.keys())[:10]}")
else:
    print(f"  ✔ Maps to emp_no={emp_no}")

# ── STAGE 4: Timestamp parse ──────────────────────────────
print(f"\n[STAGE 4] Parsing timestamps...")
for ev in matches:
    time_str = ev.get("time", "")
    try:
        dt_raw = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        if dt_raw.tzinfo is None:
            dt_local = dt_raw.replace(tzinfo=LOCAL_TZ)
        else:
            dt_local = dt_raw.astimezone(LOCAL_TZ)
        print(f"  ✔ Raw: {time_str!r}")
        print(f"     → Local: {dt_local}  date={dt_local.date()}  time={dt_local.time()}")
        if str(dt_local.date()) != TARGET_DATE:
            print(f"  ⚠  DATE MISMATCH — punch lands on {dt_local.date()}, not {TARGET_DATE}!")
    except Exception as e:
        print(f"  ❌ PARSE FAILED for {time_str!r}: {e}")

# ── STAGE 5: Check DB ─────────────────────────────────────
print(f"\n[STAGE 5] Checking DB for existing row...")
from db import get_db_cursor
with get_db_cursor() as cur:
    cur.execute("""
        SELECT id, attendance_id, emp_no, date, check_in, check_out, on_leave
        FROM employee_attendance
        WHERE emp_no = %s AND date = %s
    """, (emp_no, TARGET_DATE))
    row = cur.fetchone()

if row:
    print(f"  ✔ Row EXISTS in DB: {row}")
else:
    print(f"  ❌ No row found in DB for emp_no={emp_no}, date={TARGET_DATE}")

print(f"\n{'='*55}\n")