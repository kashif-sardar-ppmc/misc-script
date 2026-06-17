# test_find_bad_row.py
from datetime import date
from attendance_sync_service import get_hikvision_events_range, load_emp_map, prepare_attendance_rows
from db import get_db_cursor

START = "2026-04-16"
END   = "2026-04-16"

sql = """
INSERT INTO employee_attendance
    (attendance_id, emp_no, date, check_in, check_out, on_leave, comments)
VALUES
    (%s, %s, %s, %s, %s, FALSE, NULL)
ON CONFLICT (emp_no, date)
DO UPDATE SET
    attendance_id = EXCLUDED.attendance_id,
    check_in  = LEAST(employee_attendance.check_in,  EXCLUDED.check_in),
    check_out = GREATEST(
        COALESCE(employee_attendance.check_out, EXCLUDED.check_out),
        COALESCE(EXCLUDED.check_out, employee_attendance.check_out)
    ),
    on_leave = employee_attendance.on_leave,
    comments = employee_attendance.comments
"""

raw     = get_hikvision_events_range(START, END)
emp_map = load_emp_map()
rows    = prepare_attendance_rows(raw, emp_map)

print(f"\nTotal rows to upsert: {len(rows)}\n")

failed  = []
success = 0

for row in rows:
    try:
        with get_db_cursor() as cur:
            cur.execute(sql, row)
        success += 1
    except Exception as e:
        failed.append((row, str(e)))
        print(f"❌ FAILED row: attendance_id={row[0]}  emp_no={row[1]}  date={row[2]}")
        print(f"   Error: {e}\n")

print(f"\n✔ Success: {success}")
print(f"❌ Failed:  {len(failed)}")