import json
from datetime import datetime, timedelta, date
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

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
def normalize_attendance_id(attendance_id):
    if attendance_id is None:
        return None

    attendance_id = str(attendance_id).strip()
    return attendance_id or None


def normalize_attendance_ids(attendance_id):
    if attendance_id is None:
        return None

    if isinstance(attendance_id, (list, tuple, set)):
        ids = [normalize_attendance_id(value) for value in attendance_id]
    else:
        ids = [
            normalize_attendance_id(value)
            for value in str(attendance_id).replace("\n", ",").split(",")
        ]

    ids = [value for value in ids if value]
    return ids or None


def filter_raw_events_by_attendance_id(raw_events, attendance_id):
    attendance_ids = normalize_attendance_ids(attendance_id)
    if not attendance_ids:
        return raw_events

    attendance_id_set = set(attendance_ids)
    return [
        ev for ev in raw_events
        if str(ev.get("employeeNoString") or ev.get("employeeNo") or "").strip() in attendance_id_set
    ]


def fetch_from_single_device(
    device_url,
    start_date: str,
    end_date: str,
    attendance_id: Optional[str] = None,
    use_device_filter: bool = True,
):
    all_raw_events = []
    position = 0
    max_results = 30
    headers = {"Content-Type": "application/json"}
    attendance_id = normalize_attendance_id(attendance_id)

    start_time = f"{start_date}T00:00:00+05:00"
    end_time = f"{end_date}T23:59:59+05:00"

    while True:
        event_condition = {
            "searchID": "attendance-selected" if attendance_id else "attendance-all",
            "searchResultPosition": position,
            "maxResults": max_results,
            "major": 5,
            "minor": 0,
            "startTime": start_time,
            "endTime": end_time,
        }

        if attendance_id and use_device_filter:
            event_condition["employeeNoString"] = attendance_id

        payload = {
            "AcsEventCond": event_condition
        }

        r = requests.post(
            device_url,
            data=json.dumps(payload),
            headers=headers,
            auth=HTTPDigestAuth(HIK_USERNAME, HIK_PASSWORD),
            timeout=20,
            verify=False,
        )
        r.raise_for_status()

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
def get_hikvision_events_range(start_date: str, end_date: str, attendance_id: Optional[str] = None):
    attendance_ids = normalize_attendance_ids(attendance_id)
    device_filter_id = attendance_ids[0] if attendance_ids and len(attendance_ids) == 1 else None
    scope_text = f" for attendance ID(s) {', '.join(attendance_ids)}" if attendance_ids else ""
    if scope_text:
        print(f"[INFO] Employee scope:{scope_text}")
    print(f"[INFO] Fetching device data: {start_date} → {end_date}")

    events = []
    with ThreadPoolExecutor(max_workers=min(8, len(DEVICE_URLS))) as executor:
        futures = {
            executor.submit(fetch_from_single_device, url, start_date, end_date, device_filter_id): url
            for url in DEVICE_URLS
        }

        for future in as_completed(futures):
            try:
                res = future.result()
            except Exception as exc:
                if not device_filter_id:
                    raise

                url = futures[future]
                print(
                    "[WARN] Device-side employee filter failed for "
                    f"{url}. Retrying full fetch and filtering locally. Error: {exc}"
                )
                res = fetch_from_single_device(
                    url,
                    start_date,
                    end_date,
                    attendance_id=device_filter_id,
                    use_device_filter=False,
                )
            if isinstance(res, list):
                events.extend(res)

    events = filter_raw_events_by_attendance_id(events, attendance_ids)
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
def prepare_attendance_rows(raw_events, emp_map, attendance_id: Optional[str] = None):
    """
    Returns list of tuples:
    (attendance_id, emp_no, date, check_in, check_out)
    """
    punches = defaultdict(list)
    attendance_ids = normalize_attendance_ids(attendance_id)
    attendance_id_set = set(attendance_ids) if attendance_ids else None

    for ev in raw_events:
        emp_id = ev.get("employeeNoString") or ev.get("employeeNo")
        time_str = ev.get("time")

        if not emp_id or not time_str:
            continue

        emp_id_str = str(emp_id).strip()
        if attendance_id_set and emp_id_str not in attendance_id_set:
            continue

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
def daily_sync_yesterday(attendance_id: Optional[str] = None):
    today = date.today()
    yesterday = today - timedelta(days=1)

    start = yesterday.strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    print(f"[INFO] Daily sync started for {start} → {end}")

    attendance_ids = normalize_attendance_ids(attendance_id)
    if attendance_ids:
        print(f"[INFO] Daily sync attendance ID(s): {', '.join(attendance_ids)}")

    raw = get_hikvision_events_range(start, end, attendance_id=attendance_ids)
    emp_map = load_emp_map()
    rows = prepare_attendance_rows(raw, emp_map, attendance_id=attendance_ids)
    upserted = upsert_attendance_rows(rows)

    print(f"[INFO] Daily sync completed. Rows upserted: {upserted}")
    return upserted

# =========================================================
# 8) SYNC LAST N DAYS (0 = TODAY)
# =========================================================
def sync_last_n_days(n: int, attendance_id: Optional[str] = None):
    if n < 0:
        raise ValueError("Days cannot be negative")

    today = date.today()
    start = today - timedelta(days=n)

    start_str = start.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")

    print(f"[INFO] Syncing last {n} days: {start_str} → {end_str}")

    attendance_ids = normalize_attendance_ids(attendance_id)
    if attendance_ids:
        print(f"[INFO] Sync attendance ID(s): {', '.join(attendance_ids)}")

    raw = get_hikvision_events_range(start_str, end_str, attendance_id=attendance_ids)
    emp_map = load_emp_map()
    rows = prepare_attendance_rows(raw, emp_map, attendance_id=attendance_ids)
    upserted = upsert_attendance_rows(rows)

    print(f"[INFO] Sync completed. Rows upserted: {upserted}")
    return upserted


# =========================================================
# 9) SYNC CUSTOM DATE RANGE
# =========================================================
def sync_date_range(start_date: str, end_date: str, attendance_id: Optional[str] = None):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD")

    if start > end:
        raise ValueError("Start date cannot be after end date")

    print(f"[INFO] Syncing range: {start_date} → {end_date}")

    attendance_ids = normalize_attendance_ids(attendance_id)
    if attendance_ids:
        print(f"[INFO] Sync attendance ID(s): {', '.join(attendance_ids)}")

    raw = get_hikvision_events_range(start_date, end_date, attendance_id=attendance_ids)
    emp_map = load_emp_map()
    rows = prepare_attendance_rows(raw, emp_map, attendance_id=attendance_ids)
    upserted = upsert_attendance_rows(rows)

    print(f"[INFO] Sync completed. Rows upserted: {upserted}")
    return upserted
