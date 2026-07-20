# Attendance Sync Console

A command-line tool to sync attendance data from biometric devices into PPMC Synergy.

---

## Requirements

- Python installed and added to PATH
- This repo cloned anywhere on your machine

---

## How to Run

**Step 1** — Open PowerShell and go to **wherever you cloned this repo**:

```powershell
cd "C:\path\to\attendance_console"
```

> Example: `cd "D:\PPMC\Projects\attendance_console"` or wherever you cloned it.

**Step 2** — Run the script with a mode flag:

```powershell
# For daily sync (interactive menu)
python sync_attendance.py --daily

# For full import (one-time use only)
python sync_attendance.py --full
```

---

## Daily Sync Menu

When you run `--daily`, choose the employee scope first:

```
==============================
 ATTENDANCE EMPLOYEE SCOPE
==============================

1) All employee
2) Specific ID(s)
0) Exit / Back

Enter choice:
```

Then choose the date range:

```
==============================
 ATTENDANCE DAILY SYNC
==============================

1) Last N days
2) Custom date range
3) Yesterday only
0) Exit / Back

Enter choice:
```

| Choice | What it does |
|--------|--------------|
| `1` | Asks how many days back to sync (e.g. `3` = last 3 days) |
| `2` | Asks for a start date and end date (format: `YYYY-MM-DD`) |
| `3` | Syncs yesterday's data only — use this for daily routine |
| `0` | Exit |

### Daily Routine (Every Day)

```
Enter choice: 1
Enter choice: 3
```

That's it. Script will sync yesterday and finish automatically.

---

## Choice 1 — Last N Days (Examples)

```
Enter N: 0   → today only
Enter N: 1   → yesterday + today
Enter N: 3   → last 3 days
Enter N: b   → go back to menu
```

## Choice 2 — Custom Date Range

```
Start date: 2026-01-01
End date:   2026-01-31
```

---

## Specific Attendance ID(s)

Choose `2) Specific ID(s)` in the employee scope menu, enter one ID or multiple comma-separated IDs, then choose any date option:

```
Enter choice: 2
Enter attendance ID(s), comma separated (or b to back): 1234, 5678, 9012
Enter choice: 2
Start date: 2026-01-01
End date:   2026-01-31
```

## Full Import (One-Time Only)

```powershell
python sync_attendance.py --full
```

> ⚠️ This truncates and reloads ALL data till yesterday. Do not run this daily.

---

## Notes

- You cannot use `--full` and `--daily` together
- Date format is always `YYYY-MM-DD`
- Type `b` anywhere to go back to the previous menu
