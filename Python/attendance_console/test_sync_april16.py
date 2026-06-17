# test_sync_april16.py
from attendance_sync_service import sync_date_range

result = sync_date_range("2026-04-16", "2026-04-16")
print(f"\nReturn value: {result}")

# Now check the DB directly
from db import get_db_cursor
with get_db_cursor() as cur:
    cur.execute("""
        SELECT attendance_id, emp_no, date, check_in, check_out
        FROM employee_attendance
        WHERE date = '2026-04-16'
        ORDER BY emp_no
    """)
    rows = cur.fetchall()

print(f"\nRows in DB for 2026-04-16: {len(rows)}")
for r in rows:
    print(f"  att_id={r[0]}  emp_no={r[1]}  date={r[2]}  in={r[3]}  out={r[4]}")