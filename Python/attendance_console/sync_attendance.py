# sync_attendance.py
import argparse

from attendance_sync_service import (
    full_import_till_yesterday,
    daily_sync_yesterday,
    sync_last_n_days,
    sync_date_range,
)


def daily_menu():
    while True:
        print("\n==============================")
        print(" ATTENDANCE DAILY SYNC ")
        print("==============================\n")

        print("1) Last N days")
        print("2) Custom date range")
        print("3) Yesterday only")
        print("0) Exit / Back\n")

        choice = input("Enter choice: ").strip().lower()

        # ---------------------------------
        # EXIT / BACK
        # ---------------------------------
        if choice == "0":
            print("↩ Returning to main menu...\n")
            return

        # ---------------------------------
        # LAST N DAYS
        # ---------------------------------
        elif choice == "1":
            while True:
                print("\nEnter number of days (N)")
                print("Examples:")
                print("  0 → today only")
                print("  1 → yesterday + today")
                print("  3 → last 3 days")
                print("  b → back\n")

                val = input("Enter N: ").strip().lower()

                if val == "b":
                    break

                try:
                    n = int(val)
                    sync_last_n_days(n)
                    return
                except Exception as e:
                    print(f"[ERROR] {e}")

        # ---------------------------------
        # DATE RANGE
        # ---------------------------------
        elif choice == "2":
            while True:
                print("\nEnter date range (YYYY-MM-DD)")
                print("Example:")
                print("  Start: 2025-01-01")
                print("  End:   2025-01-10")
                print("  b → back\n")

                start = input("Start date: ").strip().lower()
                if start == "b":
                    break

                end = input("End date: ").strip().lower()
                if end == "b":
                    break

                try:
                    sync_date_range(start, end)
                    return
                except Exception as e:
                    print(f"[ERROR] {e}")

        # ---------------------------------
        # YESTERDAY ONLY
        # ---------------------------------
        elif choice == "3":
            daily_sync_yesterday()
            return

        else:
            print("❌ Invalid choice. Try again.")


def main():
    parser = argparse.ArgumentParser(description="Attendance Sync Console")

    parser.add_argument(
        "--full",
        action="store_true",
        help="Run one-time full import (truncate + reload till yesterday)",
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="Run interactive daily sync",
    )

    args = parser.parse_args()

    if args.full and args.daily:
        print("❌ Choose only ONE: --full OR --daily")
        return

    if not args.full and not args.daily:
        print("❌ You must specify --full or --daily")
        return

    print("======================================")
    print(" Attendance Sync Started")
    print("======================================")

    if args.full:
        print("Mode: FULL IMPORT")
        rows = full_import_till_yesterday()
        print(f"✔ FULL import completed. Rows inserted: {rows}")

    elif args.daily:
        daily_menu()

    print("======================================")
    print(" Attendance Sync Finished")
    print("======================================")

if __name__ == "__main__":
    main()
