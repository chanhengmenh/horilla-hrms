"""
Management command to import employees from samples/employee.csv into the actual database,
configuring:
- Users (HorillaUser)
- Company, Departments, Job Positions, Job Roles, Work Types, Shifts, Employee Types
- Employee profiles with Cambodia dependent logic (marital_status, children) and Khmer script names
- EmployeeWorkInformation with manager hierarchy
- Contracts with "Cambodia Tax" filing status and monthly wage
- Filing Status, Tax Brackets (0/5/10/15/20%), and USD -> KHR Exchange Rate (4,046.0)
- Leave Types (Annual Leave, Sick Leave, Unpaid Leave) and AvailableLeave balances
- Attendance Overtime (AttendanceOverTime) records
"""

import csv
import math
import os
import re
from datetime import datetime, date

from django.core.management.base import BaseCommand
from django.db import connection, connections, transaction
from django.contrib.auth.models import Permission
from django.conf import settings


def format_ot_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class Command(BaseCommand):
    help = "Imports employees from samples/employee.csv with full payroll, leave, and OT logic."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=os.path.join(settings.BASE_DIR, "samples", "employee.csv"),
            help="Path to employee CSV file",
        )

    def handle(self, *args, **options):
        # 1. Verify or switch DB connection if needed
        try:
            connection.ensure_connection()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Connected to database engine: {connection.settings_dict['ENGINE']} "
                    f"({connection.settings_dict.get('NAME')})"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Default DB connection failed ({e}). Falling back to SQLite TestDB.sqlite3..."
                )
            )
            settings.DATABASES["default"] = {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.path.join(settings.BASE_DIR, "TestDB.sqlite3"),
                "OPTIONS": {"timeout": 30},
            }
            connections.close_all()
            if "default" in connections:
                del connections["default"]
            conn = connections["default"]
            conn.ensure_connection()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Connected to fallback SQLite: {conn.settings_dict['NAME']}"
                )
            )

        # Import models
        from horilla_auth.models import HorillaUser
        from base.models import (
            Company,
            Department,
            JobPosition,
            JobRole,
            WorkType,
            EmployeeShift,
            EmployeeType,
            EmployeeShiftDay,
        )
        from employee.models import Employee, EmployeeWorkInformation
        from payroll.models.models import FilingStatus, Contract
        from payroll.models.tax_models import TaxBracket, PayrollSettings
        from leave.models import LeaveType, AvailableLeave
        from attendance.models import AttendanceOverTime

        csv_path = options["file"]
        if not os.path.isfile(csv_path):
            fallback_csv = os.path.join(settings.BASE_DIR, "employee.csv")
            if os.path.isfile(fallback_csv):
                csv_path = fallback_csv
            else:
                self.stdout.write(self.style.ERROR(f"File not found: {csv_path}"))
                return

        self.stdout.write(f"Reading employee records from: {csv_path}")
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            records = list(reader)

        self.stdout.write(f"Found {len(records)} employee records to import.")

        with transaction.atomic():
            # 2. Company setup
            company_name = "Horilla HRMS Cambodia"
            company = Company.objects.filter(company__icontains="Horilla").first()
            if not company:
                company = Company.objects.create(company=company_name)
                self.stdout.write(self.style.SUCCESS(f"Created company: {company.company}"))
            else:
                self.stdout.write(f"Using existing company: {company.company}")

            # 3. Shifts & Shift Days
            shift_days = [
                "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
            ]
            for sd in shift_days:
                EmployeeShiftDay.objects.get_or_create(day=sd)

            reg_shift, _ = EmployeeShift.objects.get_or_create(
                employee_shift="Regular Shift",
                defaults={"company_id": company},
            )
            morning_shift, _ = EmployeeShift.objects.get_or_create(
                employee_shift="Morning Shift",
                defaults={"company_id": company},
            )

            # 4. Work Type & Employee Type
            ft_work_type, _ = WorkType.objects.get_or_create(
                work_type="Full Time",
                defaults={"company_id": company},
            )
            perm_type, _ = EmployeeType.objects.get_or_create(
                employee_type="Permanent",
                defaults={"company_id": company},
            )
            prob_type, _ = EmployeeType.objects.get_or_create(
                employee_type="Probation",
                defaults={"company_id": company},
            )

            # 5. Payroll Settings: USD -> KHR Exchange Rate
            payroll_settings = PayrollSettings.objects.filter(company_id=company).first()
            if not payroll_settings:
                payroll_settings = PayrollSettings.objects.create(
                    company_id=company,
                    currency_symbol="$",
                    position="prefix",
                    usd_to_khr_rate=4046.0,
                )
            else:
                payroll_settings.usd_to_khr_rate = 4046.0
                payroll_settings.currency_symbol = "$"
                payroll_settings.save()
            self.stdout.write(self.style.SUCCESS("Configured PayrollSettings with USD -> KHR rate: 4,046.0"))

            # 6. Filing Status & Tax Brackets
            filing_status, _ = FilingStatus.objects.get_or_create(
                filing_status="Cambodia Tax",
                defaults={
                    "based_on": "taxable_gross_pay",
                    "use_py": False,
                    "description": "Standard Cambodian Tax on Salary (GDT Rules)",
                    "company_id": company,
                },
            )
            # Ensure brackets exist
            existing_brackets = TaxBracket.objects.filter(filing_status_id=filing_status)
            if not existing_brackets.exists():
                TaxBracket.objects.create(
                    filing_status_id=filing_status, min_income=0, max_income=1500000, tax_rate=0, deduction=0
                )
                TaxBracket.objects.create(
                    filing_status_id=filing_status, min_income=1500001, max_income=2000000, tax_rate=5, deduction=75000
                )
                TaxBracket.objects.create(
                    filing_status_id=filing_status, min_income=2000001, max_income=8500000, tax_rate=10, deduction=175000
                )
                TaxBracket.objects.create(
                    filing_status_id=filing_status, min_income=8500001, max_income=12500000, tax_rate=15, deduction=600000
                )
                TaxBracket.objects.create(
                    filing_status_id=filing_status, min_income=12500001, max_income=math.inf, tax_rate=20, deduction=1225000
                )
                self.stdout.write(self.style.SUCCESS("Created 5 Cambodia Tax Brackets (0%, 5%, 10%, 15%, 20%)"))
            else:
                self.stdout.write("Cambodia Tax Brackets already exist.")

            # 7. Leave Types
            al_type, _ = LeaveType.objects.get_or_create(
                name="Annual Leave",
                defaults={
                    "payment": "paid",
                    "payment_type": "paid",
                    "total_days": 18.0,
                    "reset_based": "yearly",
                    "carryforward_type": "carryforward",
                    "company_id": company,
                },
            )
            sl_type, _ = LeaveType.objects.get_or_create(
                name="Sick Leave",
                defaults={
                    "payment": "paid",
                    "payment_type": "paid",
                    "total_days": 6.0,
                    "reset_based": "yearly",
                    "carryforward_type": "no carryforward",
                    "company_id": company,
                },
            )
            upl_type, _ = LeaveType.objects.get_or_create(
                name="Unpaid Leave",
                defaults={
                    "payment": "unpaid",
                    "payment_type": "unpaid",
                    "total_days": 0.0,
                    "company_id": company,
                },
            )
            self.stdout.write(self.style.SUCCESS("Verified Leave Types: Annual Leave, Sick Leave, Unpaid Leave"))

            # 8. Permissions for users
            change_ownprofile = Permission.objects.filter(codename="change_ownprofile").first()
            view_ownprofile = Permission.objects.filter(codename="view_ownprofile").first()

            # Track created employees for reporting manager linking
            emp_by_name = {}
            emp_objects = []

            for row in records:
                badge_id = row.get("Badge ID", "").strip()
                first_name = row.get("First Name", "").strip()
                last_name = row.get("Last Name", "").strip()
                email = row.get("Email", "").strip().lower()
                phone = row.get("Phone", "").strip()
                gender = (row.get("Gender") or "male").strip().lower()
                dob_str = row.get("Date Joining", "")
                dob = None
                if row.get("Date of Birth"):
                    try:
                        dob = datetime.strptime(row["Date of Birth"].strip(), "%Y-%m-%d").date()
                    except ValueError:
                        dob = None

                join_date = None
                if row.get("Date Joining"):
                    try:
                        join_date = datetime.strptime(row["Date Joining"].strip(), "%Y-%m-%d").date()
                    except ValueError:
                        join_date = date.today()
                else:
                    join_date = date.today()

                end_date = None
                if row.get("Contract End Date"):
                    try:
                        end_date = datetime.strptime(row["Contract End Date"].strip(), "%Y-%m-%d").date()
                    except ValueError:
                        end_date = None

                marital_status = row.get("Marital Status", "single").strip()
                children = int(row.get("Children") or 0)
                basic_salary = float(row.get("Basic Salary") or 0.0)
                salary_hour = float(row.get("Salary Hour") or 0.0)
                ot_hours = float(row.get("OT Hours") or 0.0)

                # Department, Position, Role
                dept_name = row.get("Department", "General").strip()
                dept, _ = Department.objects.get_or_create(
                    department=dept_name, defaults={"company_id": company}
                )

                pos_name = row.get("Job Position", "Staff").strip()
                job_pos, _ = JobPosition.objects.get_or_create(
                    job_position=pos_name, department_id=dept, defaults={"company_id": company}
                )

                role_name = row.get("Job Role", "Officer").strip()
                job_role, _ = JobRole.objects.get_or_create(
                    job_role=role_name, job_position_id=job_pos, defaults={"company_id": company}
                )

                emp_type_obj = prob_type if row.get("Employee Type") == "Probation" else perm_type
                shift_obj = morning_shift if "Morning" in row.get("Shift", "") else reg_shift

                # User
                user = HorillaUser.objects.filter(username=email).first()
                if not user:
                    user = HorillaUser.objects.create_user(
                        username=email,
                        email=email,
                        password=phone,
                        is_new_employee=False,
                    )
                    if change_ownprofile:
                        user.user_permissions.add(change_ownprofile)
                    if view_ownprofile:
                        user.user_permissions.add(view_ownprofile)
                else:
                    user.email = email
                    user.set_password(phone)
                    user.save()

                # Employee
                additional_info = {
                    "first_name_khmer": row.get("First Name in Khmer", ""),
                    "last_name_khmer": row.get("Last Name in Khmer", ""),
                    "full_name_khmer": row.get("Full Name in Khmer", ""),
                    "id_card": row.get("ID Card", ""),
                    "tax_dependents": row.get("Total Tax Dependents", ""),
                    "dependent_relief_khr": row.get("Dependent Relief KHR", ""),
                    "salary_tax_usd": row.get("Salary Tax USD", ""),
                    "net_pay_usd": row.get("Net Pay USD", ""),
                }

                emp = Employee.objects.entire().filter(badge_id=badge_id).first()
                if not emp:
                    emp = Employee(
                        badge_id=badge_id,
                        employee_user_id=user,
                        employee_first_name=first_name,
                        employee_last_name=last_name,
                        email=email,
                        phone=phone,
                        gender=gender,
                        dob=dob,
                        address=row.get("Address", "Phnom Penh"),
                        country=row.get("Nationality", "Cambodian"),
                        marital_status=marital_status,
                        children=children,
                        additional_info=additional_info,
                        is_active=True,
                    )
                    emp.save()
                else:
                    emp.employee_user_id = user
                    emp.employee_first_name = first_name
                    emp.employee_last_name = last_name
                    emp.email = email
                    emp.phone = phone
                    emp.gender = gender
                    emp.dob = dob
                    emp.address = row.get("Address", "Phnom Penh")
                    emp.country = row.get("Nationality", "Cambodian")
                    emp.marital_status = marital_status
                    emp.children = children
                    emp.additional_info = additional_info
                    emp.is_active = True
                    emp.save()

                full_name = f"{first_name} {last_name}".strip()
                emp_by_name[full_name] = emp
                emp_objects.append((emp, row, dept, job_pos, job_role, shift_obj, emp_type_obj, join_date, end_date, basic_salary, salary_hour, ot_hours))

            # 9. Second Pass: Work Info & Manager Hierarchy
            for emp, row, dept, job_pos, job_role, shift_obj, emp_type_obj, join_date, end_date, basic_salary, salary_hour, ot_hours in emp_objects:
                mgr_name = row.get("Reporting Manager", "").strip()
                mgr_obj = emp_by_name.get(mgr_name)

                work_info = EmployeeWorkInformation.objects.filter(employee_id=emp).first()
                if not work_info:
                    work_info = EmployeeWorkInformation.objects.create(
                        employee_id=emp,
                        email=emp.email,
                        department_id=dept,
                        job_position_id=job_pos,
                        job_role_id=job_role,
                        work_type_id=ft_work_type,
                        shift_id=shift_obj,
                        employee_type_id=emp_type_obj,
                        reporting_manager_id=mgr_obj,
                        company_id=company,
                        location=row.get("Location", "Phnom Penh Head Office"),
                        date_joining=join_date,
                        contract_end_date=end_date,
                        basic_salary=basic_salary,
                        salary_hour=salary_hour,
                    )
                else:
                    work_info.email = emp.email
                    work_info.department_id = dept
                    work_info.job_position_id = job_pos
                    work_info.job_role_id = job_role
                    work_info.work_type_id = ft_work_type
                    work_info.shift_id = shift_obj
                    work_info.employee_type_id = emp_type_obj
                    work_info.reporting_manager_id = mgr_obj
                    work_info.company_id = company
                    work_info.location = row.get("Location", "Phnom Penh Head Office")
                    work_info.date_joining = join_date
                    work_info.contract_end_date = end_date
                    work_info.basic_salary = basic_salary
                    work_info.salary_hour = salary_hour
                    work_info.save()

                # 10. Contracts
                contract = Contract.objects.filter(employee_id=emp).first()
                if not contract:
                    contract = Contract.objects.create(
                        contract_name=f"{emp.employee_first_name} {emp.employee_last_name}'s Contract",
                        employee_id=emp,
                        contract_start_date=join_date,
                        contract_end_date=end_date,
                        wage_type="monthly",
                        pay_frequency="monthly",
                        wage=basic_salary,
                        contract_status="active",
                        filing_status=filing_status,
                        department=dept,
                        job_position=job_pos,
                        job_role=job_role,
                        work_type=ft_work_type,
                        shift=shift_obj,
                        company_id=company,
                    )
                else:
                    contract.wage = basic_salary
                    contract.contract_start_date = join_date
                    contract.contract_end_date = end_date
                    contract.filing_status = filing_status
                    contract.contract_status = "active"
                    contract.department = dept
                    contract.job_position = job_pos
                    contract.job_role = job_role
                    contract.work_type = ft_work_type
                    contract.shift = shift_obj
                    contract.company_id = company
                    contract.save()

                # 11. Available Leaves
                AvailableLeave.objects.update_or_create(
                    employee_id=emp,
                    leave_type_id=al_type,
                    defaults={
                        "total_leave_days": 18.0,
                        "available_days": 18.0,
                        "carryforward_days": 0.0,
                    },
                )
                AvailableLeave.objects.update_or_create(
                    employee_id=emp,
                    leave_type_id=sl_type,
                    defaults={
                        "total_leave_days": 6.0,
                        "available_days": 6.0,
                        "carryforward_days": 0.0,
                    },
                )

                # 12. Attendance Overtime
                if ot_hours > 0:
                    ot_seconds = int(ot_hours * 3600)
                    AttendanceOverTime.objects.update_or_create(
                        employee_id=emp,
                        month="june",
                        year=2026,
                        defaults={
                            "hour_account_second": 30 * 8 * 3600,
                            "worked_hours": "240:00:00",
                            "overtime_second": ot_seconds,
                            "overtime": format_ot_time(ot_seconds),
                        },
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully imported all {len(records)} employees with:\n"
                "- HorillaUser credentials\n"
                "- Employee records (with Cambodia marital status & dependent rules)\n"
                "- EmployeeWorkInformation & manager reporting hierarchy\n"
                "- Active Contracts linked to 'Cambodia Tax' filing status\n"
                "- 5 Cambodia Tax Brackets (0/5/10/15/20%)\n"
                "- Exchange rate set to 4,046.0 KHR/USD\n"
                "- Leave balances (18 days Annual Leave, 6 days Sick Leave)\n"
                "- Overtime records configured in AttendanceOverTime"
            )
        )
