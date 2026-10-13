"""
Populate Leaves, Overtime, Holidays, and NBC Exchange Rates in PostgreSQL (horillahr_dbs)
and synchronize samples/employee.csv and employee.csv.
"""

import csv
import json
from datetime import date, datetime, timedelta
import psycopg2

CSV_PATH = "samples/employee.csv"
ROOT_CSV_PATH = "employee.csv"
PG_CONFIG = {
    "dbname": "horillahr_dbs",
    "user": "postgres",
    "password": "abc123",
    "host": "localhost",
    "port": 5432,
}

EXCHANGE_RATE = 4046.0
DEPENDENT_RELIEF_KHR = 150000.0


def calculate_cambodia_tax_khr(taxable_base_khr):
    if taxable_base_khr <= 1500000:
        return 0.0, "0%"
    elif taxable_base_khr <= 2000000:
        return round(taxable_base_khr * 0.05 - 75000, 2), "5%"
    elif taxable_base_khr <= 8500000:
        return round(taxable_base_khr * 0.10 - 175000, 2), "10%"
    elif taxable_base_khr <= 12500000:
        return round(taxable_base_khr * 0.15 - 600000, 2), "15%"
    else:
        return round(taxable_base_khr * 0.20 - 1225000, 2), "20%"


def run():
    now = datetime.now()
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    try:
        # 1. Company ID
        cur.execute("SELECT id FROM base_company WHERE company ILIKE '%Horilla%' LIMIT 1")
        company_id = cur.fetchone()[0]

        # 2. Leave Types
        cur.execute("SELECT id FROM leave_leavetype WHERE name = 'Annual Leave' AND company_id_id = %s LIMIT 1", (company_id,))
        al_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM leave_leavetype WHERE name = 'Sick Leave' AND company_id_id = %s LIMIT 1", (company_id,))
        sl_id = cur.fetchone()[0]

        # 3. Insert 2026 Cambodian Public Holidays into base_holidays
        holidays_2026 = [
            (date(2026, 1, 1), date(2026, 1, 1), "New Year"),
            (date(2026, 1, 7), date(2026, 1, 7), "Victory Day"),
            (date(2026, 3, 8), date(2026, 3, 8), "Women's Day"),
            (date(2026, 4, 14), date(2026, 4, 16), "Khmer New Year"),
            (date(2026, 5, 1), date(2026, 5, 1), "Labour & Visak Day"),
            (date(2026, 5, 5), date(2026, 5, 5), "Royal Plowing"),
            (date(2026, 5, 14), date(2026, 5, 14), "King's Birthday"),
            (date(2026, 6, 18), date(2026, 6, 18), "Queen Mother Bday"),
            (date(2026, 9, 24), date(2026, 9, 24), "Constitutional Day"),
            (date(2026, 10, 10), date(2026, 10, 12), "Pchum Ben Festival"),
            (date(2026, 10, 15), date(2026, 10, 15), "King Father Day"),
            (date(2026, 10, 29), date(2026, 10, 29), "Coronation Day"),
            (date(2026, 11, 9), date(2026, 11, 9), "Independence Day"),
            (date(2026, 11, 23), date(2026, 11, 25), "Water Festival"),
            (date(2026, 12, 29), date(2026, 12, 29), "Peace Day"),
        ]

        for s_date, e_date, h_name in holidays_2026:
            cur.execute("SELECT id FROM base_holidays WHERE name = %s AND company_id_id = %s LIMIT 1", (h_name, company_id))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO base_holidays (
                        created_at, is_active, name, start_date, end_date, recurring,
                        company_id_id, assigning_type, is_specific
                    ) VALUES (%s, true, %s, %s, %s, false, %s, 'company', false)
                """,
                    (now, h_name, s_date, e_date, company_id),
                )

        # Mark June 18th holiday in attendance records
        cur.execute("UPDATE attendance_attendance SET is_holiday = true WHERE attendance_date = '2026-06-18'")
        print("Configured Cambodia Public Holidays in base_holidays and updated attendance records.")

        # 4. Insert NBC Exchange Rate for June 2026
        cur.execute("SELECT id FROM payroll_nbcexchangerate WHERE effective_date = '2026-06-15' AND company_id_id = %s LIMIT 1", (company_id,))
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO payroll_nbcexchangerate (
                    created_at, is_active, requested_date, effective_date, rate, source, company_id_id
                ) VALUES (%s, true, '2026-06-15', '2026-06-15', 4046.0, 'NBC', %s)
            """,
                (now, company_id),
            )
            print("Configured NBC Exchange Rate (4,046.0 KHR/USD) in payroll_nbcexchangerate.")

        # 5. Overtime Allocation (15 employees)
        # badge_id -> ot_hours (8h to 24h)
        ot_allocation = {
            "EMP003": 12.0,
            "EMP006": 16.0,
            "EMP008": 8.0,
            "EMP011": 20.0,
            "EMP014": 10.0,
            "EMP017": 14.0,
            "EMP021": 24.0,
            "EMP025": 16.0,
            "EMP029": 10.0,
            "EMP032": 18.0,
            "EMP036": 12.0,
            "EMP039": 8.0,
            "EMP042": 22.0,
            "EMP045": 14.0,
            "EMP048": 16.0,
        }

        # 6. Leaves Allocation (10 employees)
        # (badge_id, leave_type, start_date, end_date, days, status, reason)
        leave_records = [
            ("EMP004", al_id, date(2026, 6, 8), date(2026, 6, 9), 2.0, "approved", "Family trip"),
            ("EMP007", al_id, date(2026, 6, 12), date(2026, 6, 12), 1.0, "approved", "Personal matters"),
            ("EMP012", al_id, date(2026, 6, 22), date(2026, 6, 23), 2.0, "approved", "Annual vacation"),
            ("EMP018", al_id, date(2026, 6, 5), date(2026, 6, 5), 1.0, "approved", "Personal errand"),
            ("EMP024", al_id, date(2026, 6, 19), date(2026, 6, 19), 1.0, "approved", "Long weekend"),
            ("EMP030", al_id, date(2026, 6, 26), date(2026, 6, 26), 1.0, "approved", "Personal appointment"),
            ("EMP015", sl_id, date(2026, 6, 10), date(2026, 6, 10), 1.0, "approved", "Fever and doctor visit"),
            ("EMP022", sl_id, date(2026, 6, 16), date(2026, 6, 16), 1.0, "approved", "Flu recovery"),
            ("EMP035", sl_id, date(2026, 6, 25), date(2026, 6, 25), 1.0, "approved", "Dental procedure"),
            ("EMP040", al_id, date(2026, 7, 1), date(2026, 7, 3), 3.0, "requested", "Upcoming family holiday"),
        ]

        # Insert Leave Requests
        for badge, lt_id, s_d, e_d, days, status, desc in leave_records:
            cur.execute("SELECT id FROM employee_employee WHERE badge_id = %s LIMIT 1", (badge,))
            emp_id = cur.fetchone()[0]

            cur.execute("SELECT id FROM leave_leaverequest WHERE employee_id_id = %s AND start_date = %s LIMIT 1", (emp_id, s_d))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO leave_leaverequest (
                        created_at, is_active, start_date, start_date_breakdown, end_date,
                        end_date_breakdown, requested_days, leave_clashes_count, description,
                        status, requested_date, approved_available_days, approved_carryforward_days,
                        reject_reason, employee_id_id, leave_type_id_id
                    ) VALUES (
                        %s, true, %s, 'full_day', %s,
                        'full_day', %s, 0, %s,
                        %s, %s, %s, 0.0,
                        '', %s, %s
                    )
                """,
                    (now, s_d, e_d, days, desc, status, s_d - timedelta(days=2), days if status == "approved" else 0.0, emp_id, lt_id),
                )

                # If approved, deduct available leave balance
                if status == "approved":
                    cur.execute(
                        """
                        UPDATE leave_availableleave
                        SET available_days = GREATEST(0.0, available_days - %s)
                        WHERE employee_id_id = %s AND leave_type_id_id = %s
                    """,
                        (days, emp_id, lt_id),
                    )

                    # In attendance, mark leave day
                    cur_d = s_d
                    while cur_d <= e_d:
                        cur.execute(
                            """
                            UPDATE attendance_attendance SET
                                attendance_clock_in = NULL,
                                attendance_clock_out = NULL,
                                attendance_worked_hour = '00:00:00',
                                at_work_second = 0
                            WHERE employee_id_id = %s AND attendance_date = %s
                        """,
                            (emp_id, cur_d.isoformat()),
                        )
                        cur_d += timedelta(days=1)

        print(f"Configured 10 Leave Requests (Annual & Sick Leaves) in leave_leaverequest and updated balances.")

        # 7. Apply Overtime to Attendance & AttendanceOvertime
        for badge, ot_h in ot_allocation.items():
            cur.execute("SELECT id FROM employee_employee WHERE badge_id = %s LIMIT 1", (badge,))
            emp_id = cur.fetchone()[0]

            # Distribute OT across Tuesdays and Thursdays of June 2026 (2h per evening)
            cur.execute(
                """
                SELECT attendance_date FROM attendance_attendance
                WHERE employee_id_id = %s AND attendance_date >= '2026-06-01' AND attendance_date <= '2026-06-30'
                  AND EXTRACT(DOW FROM attendance_date) IN (2, 4) -- Tue, Thu
                  AND attendance_date != '2026-06-18' -- Not public holiday
                ORDER BY attendance_date
            """,
                (emp_id,),
            )
            ot_dates = [r[0] for r in cur.fetchall()]

            days_needed = int(ot_h // 2)
            rem_h = ot_h % 2
            selected_dates = ot_dates[:days_needed]

            for d in selected_dates:
                cur.execute(
                    """
                    UPDATE attendance_attendance SET
                        attendance_clock_out = '19:00:00',
                        attendance_worked_hour = '10:00:00',
                        attendance_overtime = '02:00:00',
                        at_work_second = 36000,
                        overtime_second = 7200,
                        approved_overtime_second = 7200,
                        attendance_overtime_approve = true
                    WHERE employee_id_id = %s AND attendance_date = %s
                """,
                    (emp_id, d),
                )

            if rem_h > 0 and len(ot_dates) > days_needed:
                last_d = ot_dates[days_needed]
                rem_sec = int(rem_h * 3600)
                cur.execute(
                    """
                    UPDATE attendance_attendance SET
                        attendance_clock_out = '18:00:00',
                        attendance_worked_hour = '09:00:00',
                        attendance_overtime = '01:00:00',
                        at_work_second = 32400,
                        overtime_second = %s,
                        approved_overtime_second = %s,
                        attendance_overtime_approve = true
                    WHERE employee_id_id = %s AND attendance_date = %s
                """,
                    (rem_sec, rem_sec, emp_id, last_d),
                )

            # Insert / Update attendance_attendanceovertime for June 2026
            total_ot_sec = int(ot_h * 3600)
            ot_str = f"{int(ot_h):02d}:00:00"
            worked_sec = 22 * 8 * 3600 + total_ot_sec
            worked_h_str = f"{176 + int(ot_h)}:00:00"

            cur.execute("SELECT id FROM attendance_attendanceovertime WHERE employee_id_id = %s AND month = 'june' AND year = '2026' LIMIT 1", (emp_id,))
            otr = cur.fetchone()
            if otr:
                cur.execute(
                    """
                    UPDATE attendance_attendanceovertime SET
                        overtime = %s, overtime_second = %s, worked_hours = %s, hour_account_second = %s
                    WHERE id = %s
                """,
                    (ot_str, total_ot_sec, worked_h_str, worked_sec, otr[0]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO attendance_attendanceovertime (
                        created_at, is_active, month, month_sequence, worked_hours, pending_hours,
                        overtime, hour_account_second, hour_pending_second, overtime_second,
                        employee_id_id, year
                    ) VALUES (
                        %s, true, 'june', 6, %s, '00:00',
                        %s, %s, 0, %s,
                        %s, '2026'
                    )
                """,
                    (now, worked_h_str, ot_str, worked_sec, total_ot_sec, emp_id),
                )

        print(f"Configured Overtime for {len(ot_allocation)} employees in attendance and monthly overtime tables.")

        # 8. Re-read and synchronize CSV files with OT and recalculated Cambodia Payroll
        with open(CSV_PATH, mode="r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        updated_rows = []
        for row in reader:
            badge = row["Badge ID"].strip()
            basic_salary = float(row["Basic Salary"])
            salary_hour = round(basic_salary / 176.0, 2)
            ot_h = ot_allocation.get(badge, 0.0)
            ot_pay = round(ot_h * salary_hour * 1.5, 2)
            other_allow = float(row.get("Other Allowances USD") or 0.0)
            gross_usd = round(basic_salary + ot_pay + other_allow, 2)
            gross_khr = round(gross_usd * EXCHANGE_RATE, 2)

            nssf_pension_khr = min(round(gross_khr * 0.02, 2), 24000.0)
            nssf_pension_usd = round(nssf_pension_khr / EXCHANGE_RATE, 2)

            taxable_net_pension_khr = gross_khr - nssf_pension_khr
            dep_relief_khr = float(row["Dependent Relief KHR"])
            taxable_after_relief_khr = max(0.0, taxable_net_pension_khr - dep_relief_khr)

            tax_khr, bracket_rate = calculate_cambodia_tax_khr(taxable_after_relief_khr)
            tax_usd = round(tax_khr / EXCHANGE_RATE, 2)
            net_usd = round(gross_usd - nssf_pension_usd - tax_usd, 2)

            row["Salary Hour"] = f"{salary_hour:.2f}"
            row["OT Hours"] = f"{ot_h:.1f}"
            row["OT Pay USD"] = f"{ot_pay:.2f}"
            row["Gross Pay USD"] = f"{gross_usd:.2f}"
            row["Gross Pay KHR"] = f"{gross_khr:.2f}"
            row["NSSF Pension KHR"] = f"{nssf_pension_khr:.2f}"
            row["NSSF Pension USD"] = f"{nssf_pension_usd:.2f}"
            row["Taxable Pay Net of Pension KHR"] = f"{taxable_net_pension_khr:.2f}"
            row["Taxable Base After Relief KHR"] = f"{taxable_after_relief_khr:.2f}"
            row["Tax Bracket Rate"] = bracket_rate
            row["Salary Tax KHR"] = f"{tax_khr:.2f}"
            row["Salary Tax USD"] = f"{tax_usd:.2f}"
            row["Net Pay USD"] = f"{net_usd:.2f}"

            # Update additional_info JSON in PostgreSQL
            cur.execute("SELECT id, additional_info FROM employee_employee WHERE badge_id = %s LIMIT 1", (badge,))
            emp_res = cur.fetchone()
            if emp_res:
                emp_id = emp_res[0]
                info = emp_res[1] or {}
                info["ot_hours"] = f"{ot_h:.1f}"
                info["ot_pay_usd"] = f"{ot_pay:.2f}"
                info["gross_pay_usd"] = f"{gross_usd:.2f}"
                info["gross_pay_khr"] = f"{gross_khr:.2f}"
                info["salary_tax_usd"] = f"{tax_usd:.2f}"
                info["salary_tax_khr"] = f"{tax_khr:.2f}"
                info["net_pay_usd"] = f"{net_usd:.2f}"
                cur.execute(
                    "UPDATE employee_employee SET additional_info = %s WHERE id = %s",
                    (json.dumps(info, ensure_ascii=False), emp_id),
                )

            # Update employee_employeeworkinformation salary_hour
            cur.execute(
                "UPDATE employee_employeeworkinformation SET salary_hour = %s WHERE employee_id_id = (SELECT id FROM employee_employee WHERE badge_id = %s LIMIT 1)",
                (int(salary_hour), badge),
            )

            updated_rows.append(row)

        fieldnames = reader[0].keys()

        with open(CSV_PATH, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)

        with open(ROOT_CSV_PATH, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)

        print(f"Synchronized {len(updated_rows)} employee records in {CSV_PATH} and {ROOT_CSV_PATH} with updated OT and Cambodia payroll.")

        conn.commit()
        print("\nAll database updates and CSV synchronizations successfully committed!")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run()
