# test_upsert_debug.py
import psycopg2
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

row = (72, 1037, '2026-04-16', '09:03:42', '16:07:06', False, None)

sql = """
INSERT INTO employee_attendance
    (attendance_id, emp_no, date, check_in, check_out, on_leave, comments)
VALUES
    (%s, %s, %s, %s, %s, %s, %s)
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

try:
    cur.execute(sql, row)
    print(f"rowcount = {cur.rowcount}")
    conn.commit()
    print("✔ Committed successfully")
except Exception as e:
    conn.rollback()
    print(f"❌ Exception: {type(e).__name__}: {e}")
finally:
    cur.close()
    conn.close()