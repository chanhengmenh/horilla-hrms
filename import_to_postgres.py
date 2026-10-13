"""
PostgreSQL Importer for Horilla HRMS (horillahr_dbs)
Imports all 50 employees from samples/employee.csv into PostgreSQL with:
- Admin superuser (admin / admin123)
- Company: Horilla HRMS Cambodia
- Shifts, Shift Schedules, Work Types, Employee Types with Company Junctions
- HorillaUser login credentials (PBKDF2 SHA256 hashed password matching phone)
- Departments, Job Positions, Job Roles with Company Junctions
- Employee records (Khmer names, ID card, Cambodia marital status & dependent rules in additional_info)
- EmployeeWorkInformation with manager hierarchy
- Payroll Settings (Exchange Rate: 4,046.0 KHR/USD)
- Filing Status ('Cambodia Tax') & 5 Tax Brackets (0%, 5%, 10%, 15%, 20%)
- Active Employment Contracts
- Leave Types (Annual Leave 18d, Sick Leave 6d, Unpaid Leave) and AvailableLeave balances
- Attendance Overtime (June 2026) and Attendance records for working days
"""

import base64
import csv
import hashlib
import json
import os
from datetime import date, datetime, timedelta
import psycopg2

CSV_PATH = "samples/employee.csv"
PG_CONFIG = {
    "dbname": "horillahr_dbs",
    "user": "postgres",
    "password": "abc123",
    "host": "localhost",
    "port": 5432,
}


def make_django_password(raw_password):
    """Generate a standard Django PBKDF2 SHA256 password hash."""
    salt = base64.b64encode(os.urandom(12)).decode("ascii")
    iterations = 720000
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", raw_password.encode("utf-8"), salt.encode("ascii"), iterations
    )
    hash_b64 = base64.b64encode(hash_bytes).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt}${hash_b64}"


def run_pg_import():
    if not os.path.isfile(CSV_PATH):
        raise FileNotFoundError(f"Cannot find CSV at {CSV_PATH}")

    now = datetime.now()

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    try:
        # 0. Admin Superuser
        cur.execute("SELECT id FROM horilla_auth_horillauser WHERE username = 'admin' LIMIT 1")
        admin_row = cur.fetchone()
        if not admin_row:
            admin_pw = make_django_password("admin123")
            cur.execute(
                """
                INSERT INTO horilla_auth_horillauser (
                    password, is_superuser, username, first_name, last_name, email,
                    is_staff, is_active, date_joined, is_new_employee
                ) VALUES (%s, true, 'admin', 'Admin', 'User', 'admin@horilla.com', true, true, %s, false)
                RETURNING id
            """,
                (admin_pw, now),
            )
            admin_id = cur.fetchone()[0]
            print(f"Created superuser 'admin' (password: admin123, ID: {admin_id})")
        else:
            admin_id = admin_row[0]
            print(f"Using existing superuser 'admin' (ID: {admin_id})")

        # 1. Company
        cur.execute("SELECT id FROM base_company WHERE company ILIKE '%Horilla%' LIMIT 1")
        row = cur.fetchone()
        if row:
            company_id = row[0]
            print(f"Using existing company ID: {company_id}")
        else:
            cur.execute(
                """
                INSERT INTO base_company (
                    created_at, is_active, company, hq, address, country, state, city, zip
                ) VALUES (
                    %s, true, 'Horilla HRMS Cambodia', true, 'Norodom Blvd, Phnom Penh', 'Cambodia', 'Phnom Penh', 'Phnom Penh', '12000'
                ) RETURNING id
            """,
                (now,),
            )
            company_id = cur.fetchone()[0]
            print(f"Created company 'Horilla HRMS Cambodia' with ID: {company_id}")

        # 2. Shift Days & Shifts
        cur.execute("SELECT id, day FROM base_employeeshiftday")
        day_ids = {r[1].lower(): r[0] for r in cur.fetchall()}
        for did in day_ids.values():
            cur.execute(
                "SELECT 1 FROM base_employeeshiftday_company_id WHERE employeeshiftday_id = %s AND company_id = %s",
                (did, company_id),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO base_employeeshiftday_company_id (employeeshiftday_id, company_id) VALUES (%s, %s)",
                    (did, company_id),
                )

        def get_or_create_shift(name):
            cur.execute("SELECT id FROM base_employeeshift WHERE employee_shift = %s LIMIT 1", (name,))
            r = cur.fetchone()
            if r:
                s_id = r[0]
            else:
                cur.execute(
                    """
                    INSERT INTO base_employeeshift (created_at, is_active, employee_shift, weekly_full_time, full_time)
                    VALUES (%s, true, %s, '40:00', '08:00')
                    RETURNING id
                """,
                    (now, name),
                )
                s_id = cur.fetchone()[0]

            cur.execute(
                "SELECT 1 FROM base_employeeshift_company_id WHERE employeeshift_id = %s AND company_id = %s",
                (s_id, company_id),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO base_employeeshift_company_id (employeeshift_id, company_id) VALUES (%s, %s)",
                    (s_id, company_id),
                )

            # Schedules for Monday to Friday
            for dname in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
                did = day_ids[dname]
                cur.execute(
                    "SELECT id FROM base_employeeshiftschedule WHERE shift_id_id = %s AND day_id = %s LIMIT 1",
                    (s_id, did),
                )
                sched_r = cur.fetchone()
                if sched_r:
                    sched_id = sched_r[0]
                else:
                    cur.execute(
                        """
                        INSERT INTO base_employeeshiftschedule (
                            created_at, is_active, minimum_working_hour, start_time, end_time,
                            is_night_shift, is_auto_punch_out_enabled, day_id, shift_id_id
                        ) VALUES (
                            %s, true, '08:00', '08:00:00', '17:00:00', false, false, %s, %s
                        ) RETURNING id
                    """,
                        (now, did, s_id),
                    )
                    sched_id = cur.fetchone()[0]

                cur.execute(
                    "SELECT 1 FROM base_employeeshiftschedule_company_id WHERE employeeshiftschedule_id = %s AND company_id = %s",
                    (sched_id, company_id),
                )
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO base_employeeshiftschedule_company_id (employeeshiftschedule_id, company_id) VALUES (%s, %s)",
                        (sched_id, company_id),
                    )

            return s_id

        reg_shift_id = get_or_create_shift("Regular Shift")
        morning_shift_id = get_or_create_shift("Morning Shift")

        # 3. Work Type & Employee Types
        def get_or_create_worktype(name):
            cur.execute("SELECT id FROM base_worktype WHERE work_type = %s LIMIT 1", (name,))
            r = cur.fetchone()
            if r:
                wt_id = r[0]
            else:
                cur.execute(
                    "INSERT INTO base_worktype (created_at, is_active, work_type) VALUES (%s, true, %s) RETURNING id",
                    (now, name),
                )
                wt_id = cur.fetchone()[0]
            cur.execute(
                "SELECT 1 FROM base_worktype_company_id WHERE worktype_id = %s AND company_id = %s",
                (wt_id, company_id),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO base_worktype_company_id (worktype_id, company_id) VALUES (%s, %s)",
                    (wt_id, company_id),
                )
            return wt_id

        ft_worktype_id = get_or_create_worktype("Full Time")

        def get_or_create_emptype(name):
            cur.execute("SELECT id FROM base_employeetype WHERE employee_type = %s LIMIT 1", (name,))
            r = cur.fetchone()
            if r:
                et_id = r[0]
            else:
                cur.execute(
                    "INSERT INTO base_employeetype (created_at, is_active, employee_type) VALUES (%s, true, %s) RETURNING id",
                    (now, name),
                )
                et_id = cur.fetchone()[0]
            cur.execute(
                "SELECT 1 FROM base_employeetype_company_id WHERE employeetype_id = %s AND company_id = %s",
                (et_id, company_id),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO base_employeetype_company_id (employeetype_id, company_id) VALUES (%s, %s)",
                    (et_id, company_id),
                )
            return et_id

        perm_type_id = get_or_create_emptype("Permanent")
        prob_type_id = get_or_create_emptype("Probation")

        # 4. Payroll Settings (USD -> KHR Exchange Rate = 4,046.0)
        cur.execute("SELECT id FROM payroll_payrollsettings WHERE company_id_id = %s LIMIT 1", (company_id,))
        r = cur.fetchone()
        if r:
            cur.execute(
                "UPDATE payroll_payrollsettings SET currency_symbol = '$', position = 'prefix', usd_to_khr_rate = 4046.0 WHERE id = %s",
                (r[0],),
            )
        else:
            cur.execute(
                """
                INSERT INTO payroll_payrollsettings (created_at, is_active, currency_symbol, position, company_id_id, usd_to_khr_rate)
                VALUES (%s, true, '$', 'prefix', %s, 4046.0)
            """,
                (now, company_id),
            )
        print("Configured Payroll Settings with USD -> KHR Exchange Rate: 4,046.0")

        # 5. Filing Status & Tax Brackets
        cur.execute("SELECT id FROM payroll_filingstatus WHERE filing_status = 'Cambodia Tax' LIMIT 1")
        r = cur.fetchone()
        if r:
            filing_status_id = r[0]
        else:
            cur.execute(
                """
                INSERT INTO payroll_filingstatus (created_at, is_active, filing_status, based_on, use_py, description, company_id_id)
                VALUES (%s, true, 'Cambodia Tax', 'taxable_gross_pay', false, 'Standard Cambodia Salary Tax (GDT Rules)', %s)
                RETURNING id
            """,
                (now, company_id),
            )
            filing_status_id = cur.fetchone()[0]

        # Insert 5 Brackets if not present
        cur.execute("SELECT COUNT(*) FROM payroll_taxbracket WHERE filing_status_id_id = %s", (filing_status_id,))
        if cur.fetchone()[0] == 0:
            brackets = [
                (0.0, 1500000.0, 0.0, 0.0),
                (1500001.0, 2000000.0, 5.0, 75000.0),
                (2000001.0, 8500000.0, 10.0, 175000.0),
                (8500001.0, 12500000.0, 15.0, 600000.0),
                (12500001.0, 1e15, 20.0, 1225000.0),
            ]
            for lo, hi, rate, ded in brackets:
                cur.execute(
                    """
                    INSERT INTO payroll_taxbracket (created_at, is_active, min_income, max_income, tax_rate, deduction, filing_status_id_id)
                    VALUES (%s, true, %s, %s, %s, %s, %s)
                """,
                    (now, lo, hi, rate, ded, filing_status_id),
                )
            print("Configured 5 Cambodia Tax Brackets (0%, 5%, 10%, 15%, 20%) in PostgreSQL")

        # 6. Leave Types
        def get_or_create_leavetype(name, payment, total_days, carryforward):
            cur.execute("SELECT id FROM leave_leavetype WHERE name = %s AND company_id_id = %s LIMIT 1", (name, company_id))
            r = cur.fetchone()
            if r:
                return r[0]
            cur.execute(
                """
                INSERT INTO leave_leavetype (
                    created_at, is_active, name, payment, count, period_in, limit_leave,
                    total_days, reset, is_encashable, reset_based, reset_month, reset_day,
                    carryforward_type, carryforward_max, exclude_company_leave, exclude_holiday,
                    is_compensatory_leave, company_id_id, payment_percentage, payment_type
                ) VALUES (
                    %s, true, %s, %s, %s, 'year', true,
                    %s, true, true, 'yearly', '1', '1',
                    %s, 6.0, 'yes', 'yes',
                    false, %s, 100.0, %s
                )
                RETURNING id
            """,
                (now, name, payment, total_days, total_days, carryforward, company_id, payment),
            )
            return cur.fetchone()[0]

        al_id = get_or_create_leavetype("Annual Leave", "paid", 18.0, "carryforward")
        sl_id = get_or_create_leavetype("Sick Leave", "paid", 6.0, "no carryforward")
        upl_id = get_or_create_leavetype("Unpaid Leave", "unpaid", 0.0, "no carryforward")
        print("Configured Leave Types: Annual Leave (18d), Sick Leave (6d), Unpaid Leave")

        # 7. Departments, Job Positions, Job Roles
        dept_cache = {}
        pos_cache = {}
        role_cache = {}

        def get_dept_id(dname):
            if dname in dept_cache:
                return dept_cache[dname]
            cur.execute("SELECT id FROM base_department WHERE department = %s LIMIT 1", (dname,))
            r = cur.fetchone()
            if r:
                dept_id = r[0]
            else:
                cur.execute(
                    "INSERT INTO base_department (created_at, is_active, department) VALUES (%s, true, %s) RETURNING id",
                    (now, dname),
                )
                dept_id = cur.fetchone()[0]
            cur.execute(
                "SELECT 1 FROM base_department_company_id WHERE department_id = %s AND company_id = %s",
                (dept_id, company_id),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO base_department_company_id (department_id, company_id) VALUES (%s, %s)",
                    (dept_id, company_id),
                )
            dept_cache[dname] = dept_id
            return dept_id

        def get_pos_id(pname, dept_id):
            key = (pname, dept_id)
            if key in pos_cache:
                return pos_cache[key]
            cur.execute("SELECT id FROM base_jobposition WHERE job_position = %s AND department_id_id = %s LIMIT 1", (pname, dept_id))
            r = cur.fetchone()
            if r:
                pos_id = r[0]
            else:
                cur.execute(
                    "INSERT INTO base_jobposition (created_at, is_active, job_position, department_id_id) VALUES (%s, true, %s, %s) RETURNING id",
                    (now, pname, dept_id),
                )
                pos_id = cur.fetchone()[0]
            cur.execute(
                "SELECT 1 FROM base_jobposition_company_id WHERE jobposition_id = %s AND company_id = %s",
                (pos_id, company_id),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO base_jobposition_company_id (jobposition_id, company_id) VALUES (%s, %s)",
                    (pos_id, company_id),
                )
            pos_cache[key] = pos_id
            return pos_id

        def get_role_id(rname, pos_id):
            key = (rname, pos_id)
            if key in role_cache:
                return role_cache[key]
            cur.execute("SELECT id FROM base_jobrole WHERE job_role = %s AND job_position_id_id = %s LIMIT 1", (rname, pos_id))
            r = cur.fetchone()
            if r:
                role_id = r[0]
            else:
                cur.execute(
                    "INSERT INTO base_jobrole (created_at, is_active, job_role, job_position_id_id) VALUES (%s, true, %s, %s) RETURNING id",
                    (now, rname, pos_id),
                )
                role_id = cur.fetchone()[0]
            cur.execute(
                "SELECT 1 FROM base_jobrole_company_id WHERE jobrole_id = %s AND company_id = %s",
                (role_id, company_id),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO base_jobrole_company_id (jobrole_id, company_id) VALUES (%s, %s)",
                    (role_id, company_id),
                )
            role_cache[key] = role_id
            return role_id

        # Ensure Admin user has an active Employee profile (required by Horilla login)
        cur.execute("SELECT id FROM employee_employee WHERE employee_user_id_id = %s LIMIT 1", (admin_id,))
        if not cur.fetchone():
            admin_dept_id = get_dept_id("Executive Management")
            admin_pos_id = get_pos_id("System Administrator", admin_dept_id)
            admin_role_id = get_role_id("Administrator", admin_pos_id)
            cur.execute(
                """
                INSERT INTO employee_employee (
                    badge_id, employee_first_name, employee_last_name, email, phone,
                    gender, dob, address, country, state, city, marital_status, children,
                    is_active, is_from_onboarding, is_directly_converted, employee_user_id_id
                ) VALUES (
                    'ADMIN01', 'Admin', 'User', 'admin@horilla.com', '+855 23 888 999',
                    'male', '1990-01-01', 'Norodom Blvd, Phnom Penh', 'Cambodia', 'Phnom Penh', 'Phnom Penh',
                    'single', 0, true, false, false, %s
                ) RETURNING id
            """,
                (admin_id,),
            )
            admin_emp_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO employee_employeeworkinformation (
                    email, date_joining, company_id_id, department_id_id, employee_id_id,
                    employee_type_id_id, job_position_id_id, job_role_id_id,
                    shift_id_id, work_type_id_id, location
                ) VALUES (
                    'admin@horilla.com', '2020-01-01', %s, %s, %s, %s, %s, %s, %s, %s, 'Phnom Penh Head Office'
                )
            """,
                (company_id, admin_dept_id, admin_emp_id, perm_type_id, admin_pos_id, admin_role_id, reg_shift_id, ft_worktype_id),
            )

        # 8. Read CSV and insert records
        with open(CSV_PATH, mode="r", encoding="utf-8") as f:
            records = list(csv.DictReader(f))

        emp_map = {}  # full_name -> emp_id
        emp_work_info_data = []

        for row in records:
            badge_id = row["Badge ID"].strip()
            fname = row["First Name"].strip()
            lname = row["Last Name"].strip()
            full_name = f"{fname} {lname}".strip()
            email = row["Email"].strip().lower()
            phone = row["Phone"].strip()
            gender = row.get("Gender", "male").strip().lower()
            dob = row.get("Date Birth", row.get("Date of Birth", "")).strip() or None
            join_date = row.get("Date Joining", "2022-01-01").strip()
            end_date = row.get("Contract End Date", "").strip() or None
            marital = row.get("Marital Status", "single").strip()
            children = int(row.get("Children") or 0)
            wage = float(row.get("Basic Salary") or 0.0)
            salary_hour = float(row.get("Salary Hour") or 0.0)
            ot_hours = float(row.get("OT Hours") or 0.0)

            # User
            cur.execute("SELECT id FROM horilla_auth_horillauser WHERE username = %s LIMIT 1", (email,))
            ur = cur.fetchone()
            if ur:
                user_id = ur[0]
            else:
                hashed_pw = make_django_password(phone)
                cur.execute(
                    """
                    INSERT INTO horilla_auth_horillauser (
                        password, is_superuser, username, first_name, last_name, email,
                        is_staff, is_active, date_joined, is_new_employee
                    ) VALUES (%s, false, %s, %s, %s, %s, false, true, %s, false)
                    RETURNING id
                """,
                    (hashed_pw, email, fname, lname, email, now),
                )
                user_id = cur.fetchone()[0]

            # Additional Info JSON
            add_info = json.dumps({
                "first_name_khmer": row.get("First Name in Khmer", ""),
                "last_name_khmer": row.get("Last Name in Khmer", ""),
                "full_name_khmer": row.get("Full Name in Khmer", ""),
                "id_card": row.get("ID Card", ""),
                "total_tax_dependents": row.get("Total Tax Dependents", ""),
                "dependent_relief_khr": row.get("Dependent Relief KHR", ""),
                "salary_tax_usd": row.get("Salary Tax USD", ""),
                "net_pay_usd": row.get("Net Pay USD", ""),
            }, ensure_ascii=False)

            # Employee
            cur.execute("SELECT id FROM employee_employee WHERE badge_id = %s LIMIT 1", (badge_id,))
            er = cur.fetchone()
            if er:
                emp_id = er[0]
                cur.execute(
                    """
                    UPDATE employee_employee SET
                        employee_first_name = %s, employee_last_name = %s, email = %s, phone = %s,
                        gender = %s, dob = %s, address = %s, country = %s, state = 'Phnom Penh', city = 'Phnom Penh',
                        marital_status = %s, children = %s, additional_info = %s, is_active = true, employee_user_id_id = %s
                    WHERE id = %s
                """,
                    (fname, lname, email, phone, gender, dob, row.get("Address", "Phnom Penh"),
                     row.get("Nationality", "Cambodian"), marital, children, add_info, user_id, emp_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO employee_employee (
                        badge_id, employee_first_name, employee_last_name, email, phone,
                        gender, dob, address, country, state, city, marital_status, children,
                        additional_info, is_active, is_from_onboarding, is_directly_converted,
                        employee_user_id_id
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, 'Phnom Penh', 'Phnom Penh', %s, %s,
                        %s, true, false, false,
                        %s
                    )
                    RETURNING id
                """,
                    (badge_id, fname, lname, email, phone, gender, dob, row.get("Address", "Phnom Penh"),
                     row.get("Nationality", "Cambodian"), marital, children, add_info, user_id),
                )
                emp_id = cur.fetchone()[0]

            emp_map[full_name] = emp_id

            # Org linkage
            dept_id = get_dept_id(row.get("Department", "General"))
            pos_id = get_pos_id(row.get("Job Position", "Staff"), dept_id)
            role_id = get_role_id(row.get("Job Role", "Officer"), pos_id)
            shift_id = morning_shift_id if "Morning" in row.get("Shift", "") else reg_shift_id
            emp_type_id = prob_type_id if row.get("Employee Type") == "Probation" else perm_type_id

            emp_work_info_data.append({
                "emp_id": emp_id,
                "email": email,
                "dept_id": dept_id,
                "pos_id": pos_id,
                "role_id": role_id,
                "shift_id": shift_id,
                "emp_type_id": emp_type_id,
                "manager_name": row.get("Reporting Manager", "").strip(),
                "location": row.get("Location", "Phnom Penh Head Office"),
                "join_date": join_date,
                "end_date": end_date,
                "wage": wage,
                "salary_hour": salary_hour,
                "fname": fname,
                "lname": lname,
                "ot_hours": ot_hours,
            })

        # 9. Second Pass: Work Info, Contracts, Leaves, OT
        for item in emp_work_info_data:
            emp_id = item["emp_id"]
            mgr_id = emp_map.get(item["manager_name"])

            # Work Info
            cur.execute("SELECT id FROM employee_employeeworkinformation WHERE employee_id_id = %s LIMIT 1", (emp_id,))
            wir = cur.fetchone()
            if wir:
                cur.execute(
                    """
                    UPDATE employee_employeeworkinformation SET
                        email = %s, date_joining = %s, contract_end_date = %s, basic_salary = %s, salary_hour = %s,
                        company_id_id = %s, department_id_id = %s, employee_type_id_id = %s, job_position_id_id = %s,
                        job_role_id_id = %s, reporting_manager_id_id = %s, shift_id_id = %s, work_type_id_id = %s,
                        location = %s
                    WHERE id = %s
                """,
                    (item["email"], item["join_date"], item["end_date"], int(item["wage"]), int(item["salary_hour"]),
                     company_id, item["dept_id"], item["emp_type_id"], item["pos_id"], item["role_id"],
                     mgr_id, item["shift_id"], ft_worktype_id, item["location"], wir[0]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO employee_employeeworkinformation (
                        email, date_joining, contract_end_date, basic_salary, salary_hour,
                        company_id_id, department_id_id, employee_id_id, employee_type_id_id,
                        job_position_id_id, job_role_id_id, reporting_manager_id_id,
                        shift_id_id, work_type_id_id, location
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s
                    )
                """,
                    (item["email"], item["join_date"], item["end_date"], int(item["wage"]), int(item["salary_hour"]),
                     company_id, item["dept_id"], emp_id, item["emp_type_id"], item["pos_id"], item["role_id"],
                     mgr_id, item["shift_id"], ft_worktype_id, item["location"]),
                )

            # Contract
            contract_title = f"{item['fname']} {item['lname']}'s Contract"
            cur.execute("SELECT id FROM payroll_contract WHERE employee_id_id = %s LIMIT 1", (emp_id,))
            cr = cur.fetchone()
            if cr:
                cur.execute(
                    """
                    UPDATE payroll_contract SET
                        contract_name = %s, contract_start_date = %s, contract_end_date = %s, wage = %s,
                        wage_type = 'monthly', pay_frequency = 'monthly', contract_status = 'active',
                        filing_status_id = %s, department_id = %s, job_position_id = %s, job_role_id = %s,
                        work_type_id = %s, shift_id = %s
                    WHERE id = %s
                """,
                    (contract_title, item["join_date"], item["end_date"], item["wage"],
                     filing_status_id, item["dept_id"], item["pos_id"], item["role_id"],
                     ft_worktype_id, item["shift_id"], cr[0]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO payroll_contract (
                        created_at, is_active, contract_name, contract_start_date, contract_end_date,
                        wage_type, pay_frequency, wage, contract_status, notice_period_in_days,
                        deduct_leave_from_basic_pay, calculate_daily_leave_amount,
                        department_id, employee_id_id, job_position_id, job_role_id,
                        shift_id, work_type_id, filing_status_id
                    ) VALUES (
                        %s, true, %s, %s, %s,
                        'monthly', 'monthly', %s, 'active', 30,
                        false, false,
                        %s, %s, %s, %s,
                        %s, %s, %s
                    )
                """,
                    (now, contract_title, item["join_date"], item["end_date"], item["wage"],
                     item["dept_id"], emp_id, item["pos_id"], item["role_id"],
                     item["shift_id"], ft_worktype_id, filing_status_id),
                )

            # Available Leaves (Annual Leave 18d, Sick Leave 6d)
            for lt_id, days in [(al_id, 18.0), (sl_id, 6.0)]:
                cur.execute("SELECT id FROM leave_availableleave WHERE employee_id_id = %s AND leave_type_id_id = %s LIMIT 1", (emp_id, lt_id))
                alr = cur.fetchone()
                if alr:
                    cur.execute(
                        "UPDATE leave_availableleave SET available_days = %s, total_leave_days = %s WHERE id = %s",
                        (days, days, alr[0]),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO leave_availableleave (
                            created_at, is_active, available_days, carryforward_days, total_leave_days,
                            assigned_date, employee_id_id, leave_type_id_id
                        ) VALUES (%s, true, %s, 0.0, %s, '2026-01-01', %s, %s)
                    """,
                        (now, days, days, emp_id, lt_id),
                    )

            # Attendance Overtime (June 2026)
            ot_h = item["ot_hours"]
            if ot_h > 0:
                ot_sec = int(ot_h * 3600)
                ot_str = f"{int(ot_h):02d}:00:00"
                cur.execute("SELECT id FROM attendance_attendanceovertime WHERE employee_id_id = %s AND month = 'june' AND year = '2026' LIMIT 1", (emp_id,))
                otr = cur.fetchone()
                if otr:
                    cur.execute(
                        "UPDATE attendance_attendanceovertime SET overtime = %s, overtime_second = %s WHERE id = %s",
                        (ot_str, ot_sec, otr[0]),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO attendance_attendanceovertime (
                            created_at, is_active, month, month_sequence, worked_hours, pending_hours,
                            overtime, hour_account_second, hour_pending_second, overtime_second,
                            employee_id_id, year
                        ) VALUES (
                            %s, true, 'june', 6, '240:00:00', '00:00',
                            %s, 864000, 0, %s,
                            %s, '2026'
                        )
                    """,
                        (now, ot_str, ot_sec, emp_id),
                    )

            # Attendance Records for June 2026 (Working days Monday-Friday, 22 days)
            cur.execute("SELECT COUNT(*) FROM attendance_attendance WHERE employee_id_id = %s AND attendance_date >= '2026-06-01' AND attendance_date <= '2026-06-30'", (emp_id,))
            if cur.fetchone()[0] == 0:
                start_dt = date(2026, 6, 1)
                end_dt = date(2026, 6, 30)
                curr_date = start_dt
                while curr_date <= end_dt:
                    if curr_date.weekday() < 5:  # Mon to Fri
                        day_name = curr_date.strftime("%A").lower()
                        sday_id = day_ids.get(day_name)
                        cur.execute(
                            """
                            INSERT INTO attendance_attendance (
                                created_at, is_active, attendance_date, attendance_clock_in_date,
                                attendance_clock_in, attendance_clock_out_date, attendance_clock_out,
                                attendance_worked_hour, minimum_hour, attendance_overtime,
                                attendance_overtime_approve, attendance_validated, at_work_second,
                                overtime_second, approved_overtime_second, is_validate_request,
                                is_bulk_request, is_validate_request_approved, is_holiday,
                                attendance_day_id, employee_id_id, shift_id_id, work_type_id_id
                            ) VALUES (
                                %s, true, %s, %s,
                                '08:00:00', %s, '17:00:00',
                                '08:00:00', '08:00:00', '00:00',
                                false, true, 28800,
                                0, 0, false,
                                false, true, false,
                                %s, %s, %s, %s
                            )
                        """,
                            (now, curr_date.isoformat(), curr_date.isoformat(), curr_date.isoformat(),
                             sday_id, emp_id, item["shift_id"], ft_worktype_id),
                        )
                    curr_date += timedelta(days=1)

        conn.commit()
        print(f"\n==================================================================")
        print(f"SUCCESS: Successfully imported all {len(records)} employees into PostgreSQL horillahr_dbs!")
        print(f"==================================================================")
        print("- 1 Admin Superuser ('admin' / 'admin123')")
        print(f"- {len(records)} HorillaUser login credentials (email / phone number)")
        print(f"- {len(records)} Employee records (Khmer names, ID cards, Cambodia tax status & dependents)")
        print(f"- {len(records)} EmployeeWorkInformation records with manager hierarchy")
        print(f"- {len(records)} Active Employment Contracts linked to 'Cambodia Tax' filing status")
        print("- 5 Cambodia Tax Brackets (0%, 5%, 10%, 15%, 20%) configured")
        print("- Exchange rate set to 4,046.0 KHR/USD in PayrollSettings")
        print(f"- Leave balances allocated: Annual Leave (18 days) and Sick Leave (6 days) for all employees")
        print("- 1,100 Attendance records and June 2026 Overtime records created")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run_pg_import()
