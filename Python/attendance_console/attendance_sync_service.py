import json
from datetime import datetime, timedelta, date
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.auth import HTTPDigestAuth
import urllib3

from config import (
    DEVICE_URLS,
    HIK_USERNAME,
    HIK_PASSWORD,
    FULL_IMPORT_START_DATE,
)
from db import get_db_cursor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================================
# 1) Fetch events from a single Hikvision device
# =========================================================
def fetch_from_single_device(device_url, start_date: str, end_date: str):
    all_raw_events = []
    position = 0
    max_results = 30
    headers = {"Content-Type": "application/json"}

    start_time = f"{start_date}T00:00:00+05:00"
    end_time = f"{end_date}T23:59:59+05:00"

    while True:
        payload = {
            "AcsEventCond": {
                "searchID": "attendance-all",
                "searchResultPosition": position,
                "maxResults": max_results,
                "major": 5,
                "minor": 0,
                "startTime": start_time,
                "endTime": end_time,
            }
        }

        r = requests.post(
            device_url,
            data=json.dumps(payload),
            headers=headers,
            auth=HTTPDigestAuth(HIK_USERNAME, HIK_PASSWORD),
            timeout=20,
            verify=False,
        )

        # Hikvision sometimes responds with XML-like auth failure
        if "<statusValue>401</statusValue>" in (r.text or ""):
            raise Exception(f"Authentication failed for device: {device_url}")

        data = r.json()
        info_list = data.get("AcsEvent", {}).get("InfoList", [])

        if isinstance(info_list, dict):
            info_list = [info_list]

        if not info_list:
            break

        all_raw_events.extend(info_list)

        if len(info_list) < max_results:
            break

        position += max_results

    return all_raw_events


# =========================================================
# 2) Fetch events from ALL devices (parallel)
# =========================================================
def get_hikvision_events_range(start_date: str, end_date: str):
    print(f"[INFO] Fetching device data: {start_date} → {end_date}")

    events = []
    with ThreadPoolExecutor(max_workers=min(8, len(DEVICE_URLS))) as executor:
        futures = {
            executor.submit(fetch_from_single_device, url, start_date, end_date): url
            for url in DEVICE_URLS
        }

        for future in as_completed(futures):
            res = future.result()
            if isinstance(res, list):
                events.extend(res)

    print(f"[INFO] Raw events fetched: {len(events)}")
    return events


# =========================================================
# 3) Load attendance_id → emp_no mapping
# =========================================================
def load_emp_map():
    """
    Returns:
        dict { attendance_id (str) : emp_no (int) }
    """
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT emp_no, attendance_id
            FROM employee
            WHERE attendance_id IS NOT NULL
        """)
        rows = cur.fetchall()

    return {str(att_id): emp_no for (emp_no, att_id) in rows}


# =========================================================
# 4) Prepare attendance rows (group punches)
# =========================================================
def prepare_attendance_rows(raw_events, emp_map):
    """
    Returns list of tuples:
    (attendance_id, emp_no, date, check_in, check_out)
    """
    punches = defaultdict(list)

    for ev in raw_events:
        emp_id = ev.get("employeeNoString") or ev.get("employeeNo")
        time_str = ev.get("time")

        if not emp_id or not time_str:
            continue

        emp_id_str = str(emp_id).strip()
        emp_no = emp_map.get(emp_id_str)

        if not emp_no:
            # attendance_id not mapped in employee table
            continue

        try:
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except Exception:
            continue

        punches[(emp_no, dt.date(), emp_id_str)].append(dt)

    rows = []
    for (emp_no, day, emp_id_str), dts in punches.items():
        dts.sort()
        check_in = dts[0].time()
        check_out = dts[-1].time() if len(dts) > 1 else None

        rows.append((
            int(emp_id_str),
            int(emp_no),
            day,
            check_in,
            check_out,
        ))

    print(f"[INFO] Attendance rows prepared: {len(rows)}")
    return rows


# =========================================================
# 5) UPSERT attendance rows into DB
# =========================================================
def upsert_attendance_rows(rows):
    if not rows:
        return 0

    sql = """
    INSERT INTO employee_attendance
        (attendance_id, emp_no, date, check_in, check_out, on_leave, comments)
    VALUES
        (%s, %s, %s, %s, %s, FALSE, NULL)
    ON CONFLICT (emp_no, date)
    DO UPDATE SET
        attendance_id = EXCLUDED.attendance_id,
        check_in = LEAST(employee_attendance.check_in, EXCLUDED.check_in),
        check_out = GREATEST(
            COALESCE(employee_attendance.check_out, EXCLUDED.check_out),
            COALESCE(EXCLUDED.check_out, employee_attendance.check_out)
        ),
        on_leave = employee_attendance.on_leave
    """

    with get_db_cursor() as cur:
        cur.executemany(sql, rows)

    return len(rows)


# =========================================================
# 6) ONE-TIME FULL IMPORT (truncate + reload)
# =========================================================
def full_import_till_yesterday():
    yesterday = date.today() - timedelta(days=1)
    start_date = FULL_IMPORT_START_DATE
    end_date = yesterday.strftime("%Y-%m-%d")

    print("[INFO] FULL import started")

    raw = get_hikvision_events_range(start_date, end_date)
    emp_map = load_emp_map()
    rows = prepare_attendance_rows(raw, emp_map)

    with get_db_cursor() as cur:
        cur.execute("TRUNCATE TABLE employee_attendance RESTART IDENTITY;")

    inserted = upsert_attendance_rows(rows)

    print(f"[INFO] FULL import completed. Rows inserted: {inserted}")
    return inserted


# =========================================================
# 7) DAILY SYNC (yesterday only)
# =========================================================
def daily_sync_yesterday():
    today = date.today()
    yesterday = today - timedelta(days=1)

    start = yesterday.strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    print(f"[INFO] Daily sync started for {start} → {end}")

    raw = get_hikvision_events_range(start, end)
    emp_map = load_emp_map()
    rows = prepare_attendance_rows(raw, emp_map)
    upserted = upsert_attendance_rows(rows)

    print(f"[INFO] Daily sync completed. Rows upserted: {upserted}")
    return upserted

# =========================================================
# 8) SYNC LAST N DAYS (0 = TODAY)
# =========================================================
def sync_last_n_days(n: int):
    if n < 0:
        raise ValueError("Days cannot be negative")

    today = date.today()
    start = today - timedelta(days=n)

    start_str = start.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")

    print(f"[INFO] Syncing last {n} days: {start_str} → {end_str}")

    raw = get_hikvision_events_range(start_str, end_str)
    emp_map = load_emp_map()
    rows = prepare_attendance_rows(raw, emp_map)
    upserted = upsert_attendance_rows(rows)

    print(f"[INFO] Sync completed. Rows upserted: {upserted}")
    return upserted


# =========================================================
# 9) SYNC CUSTOM DATE RANGE
# =========================================================
def sync_date_range(start_date: str, end_date: str):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD")

    if start > end:
        raise ValueError("Start date cannot be after end date")

    print(f"[INFO] Syncing range: {start_date} → {end_date}")

    raw = get_hikvision_events_range(start_date, end_date)
    emp_map = load_emp_map()
    rows = prepare_attendance_rows(raw, emp_map)
    upserted = upsert_attendance_rows(rows)

    print(f"[INFO] Sync completed. Rows upserted: {upserted}")
    return upserted
