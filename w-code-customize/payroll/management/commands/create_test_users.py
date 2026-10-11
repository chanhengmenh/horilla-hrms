"""
create_test_users - seed demo users / employees for payroll testing.

Creates (idempotently - safe to run multiple times):

  - the base structures needed by payroll (company, department, job
    position, employee type, work type, shift)
  - the Cambodia tax configuration: FilingStatus "Resident" with tax
    brackets covering the 0% - 20% Cambodia rates, plus the USD -> KHR
    exchange rate used by the tax calculator
  - six test users / employees covering EVERY marital status
    (single, married, married-spouse-dependent, divorced), every tax
    bracket (0% / 5% / 10% / 15% / 20%) and two employees with an
    Overtime (OT) allowance fed by approved attendance overtime

Usage:
    python manage.py create_test_users

All created logins use the password  Test@1234
"""

import datetime
import math

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from base.models import (
    Company,
    Department,
    EmployeeShift,
    EmployeeShiftDay,
    EmployeeType,
    JobPosition,
    WorkType,
)
from employee.models import Employee, EmployeeBankDetails, EmployeeWorkInformation
from payroll.models.models import Allowance, Contract, FilingStatus
from payroll.models.tax_models import PayrollSettings, TaxBracket

PASSWORD = "Test@1234"

# Cambodia salary-tax brackets (monthly, in KHR). The flat deduction that is
# applied with each rate lives in payroll/methods/tax_calc.py.
TAX_BRACKETS_KHR = [
    (0.0, 1_300_000.0, 0.0),
    (1_300_001.0, 2_000_000.0, 5.0),
    (2_000_001.0, 8_500_000.0, 10.0),
    (8_500_001.0, 125_000_000.0, 15.0),
    (125_000_001.0, None, 20.0),  # None -> top bracket (open ended)
]

DEFAULT_USD_TO_KHR_RATE = 4100.0

# username, first, last, gender, marital status, children, monthly wage (USD)
TEST_EMPLOYEES = [
    # single, no dependents -> lowest bracket (0%)
    ("test.sok", "Sok", "Dara", "male", "single", 0, 250.0),
    # divorced -> still 0 dependents
    ("test.chan", "Chan", "Vanna", "female", "divorced", 0, 400.0),
    # married, both working -> spouse NOT a dependent, 1 child
    ("test.sophea", "Pich", "Sophea", "female", "married", 1, 700.0),
    # married, spouse is a dependent + 2 children -> 3 dependents
    ("test.rithy", "Chen", "Rithy", "male", "married_spouse_dependent", 2, 2500.0),
    # married, spouse is a dependent + 2 children, works overtime
    ("test.kanha", "Khem", "Kanha", "female", "married_spouse_dependent", 2, 1800.0),
    # single, very high salary -> top bracket (20%)
    ("test.vireak", "Vuthy", "Vireak", "male", "single", 0, 35000.0),
]

# Employees (by index in TEST_EMPLOYEES) that receive the OT allowance
OT_EMPLOYEE_INDEXES = [4, 5]  # test.kanha, test.vireak
OT_HOURLY_RATE = 6.0  # USD per approved overtime hour


class Command(BaseCommand):
    help = "Create test users / employees (all marital statuses, 0-20% tax, OT)"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding payroll test data..."))

        company = self._ensure_company()
        dept, job_position, emp_type, work_type, shift = self._ensure_structure(company)
        filing_status = self._ensure_tax_config()

        employees = []
        for index, (username, first, last, gender, marital, children, wage) in enumerate(
            TEST_EMPLOYEES, start=1
        ):
            employee = self._ensure_employee(
                company,
                dept,
                job_position,
                emp_type,
                work_type,
                shift,
                index,
                username,
                first,
                last,
                gender,
                marital,
                children,
                wage,
            )
            self._ensure_bank_details(employee, index)
            self._ensure_contract(employee, wage, filing_status)
            employees.append(employee)

        ot_employees = [employees[i] for i in OT_EMPLOYEE_INDEXES]
        ot_allowance = self._ensure_ot_allowance(ot_employees)
        self._ensure_overtime_attendance(ot_employees, shift, work_type)

        self.stdout.write(self.style.SUCCESS("\nDone. Test logins:"))
        self.stdout.write(self.style.SUCCESS(f"  password for all users: {PASSWORD}"))
        self.stdout.write("")
        self._print_summary(employees, ot_allowance, filing_status)

    # ------------------------------------------------------------------
    # base structure
    # ------------------------------------------------------------------

    def _ensure_company(self):
        company = Company.objects.filter(hq=True).first() or Company.objects.first()
        if company is None:
            company = Company(
                company="Horilla Demo",
                hq=True,
                address="Preah Norodom Blvd",
                country="Cambodia",
                state="Phnom Penh",
                city="Phnom Penh",
                zip="12000",
            )
            company.save()
            self.stdout.write("  created company: Horilla Demo")
        return company

    def _ensure_structure(self, company):
        department = Department.objects.filter(department="Engineering").first()
        if department is None:
            department = Department(department="Engineering")
            department.save()
            department.company_id.add(company)

        job_position = JobPosition.objects.filter(
            job_position="Software Engineer", department_id=department
        ).first()
        if job_position is None:
            job_position = JobPosition(
                job_position="Software Engineer", department_id=department
            )
            job_position.save()
            job_position.company_id.add(company)

        employee_type = EmployeeType.objects.filter(employee_type="Full Time").first()
        if employee_type is None:
            employee_type = EmployeeType(employee_type="Full Time")
            employee_type.save()
            employee_type.company_id.add(company)

        work_type = WorkType.objects.filter(work_type="Regular Work").first()
        if work_type is None:
            work_type = WorkType(work_type="Regular Work")
            work_type.save()
            work_type.company_id.add(company)

        shift = EmployeeShift.objects.filter(employee_shift="Standard Shift").first()
        if shift is None:
            shift = EmployeeShift(employee_shift="Standard Shift")
            shift.save()
            shift.company_id.add(company)
            # attach the 7 shift days if they exist (created by migrations)
            shift.days.set(EmployeeShiftDay.objects.all())

        return department, job_position, employee_type, work_type, shift

    # ------------------------------------------------------------------
    # tax configuration
    # ------------------------------------------------------------------

    def _ensure_tax_config(self):
        # Reuse a filing status that already has tax brackets (typically
        # "Cambodia Tax" created by HR from the UI) - never duplicate or
        # override HR-managed bracket data.
        filing_status = (
            FilingStatus.objects.filter(taxbracket__isnull=False).distinct().first()
        )
        if filing_status is not None:
            self.stdout.write(
                f"  using existing filing status '{filing_status.filing_status}'"
                " with its tax brackets"
            )
        else:
            filing_status = FilingStatus.objects.create(
                filing_status="Resident",
                based_on="taxable_gross_pay",
                description="Cambodia resident monthly salary tax (0% - 20%)",
            )
            for min_income, max_income, rate in TAX_BRACKETS_KHR:
                TaxBracket.objects.create(
                    filing_status_id=filing_status,
                    min_income=min_income,
                    max_income=max_income if max_income is not None else math.inf,
                    tax_rate=rate,
                    deduction=0.0,
                )
            self.stdout.write("  created Cambodia tax brackets (0% - 20%)")

        settings_row = PayrollSettings.objects.first()
        if settings_row is None:
            PayrollSettings.objects.create(
                usd_to_khr_rate=DEFAULT_USD_TO_KHR_RATE, currency_symbol="$"
            )
            self.stdout.write(
                f"  created payroll settings (1 USD = {DEFAULT_USD_TO_KHR_RATE} KHR)"
            )
        elif settings_row.usd_to_khr_rate is None:
            settings_row.usd_to_khr_rate = DEFAULT_USD_TO_KHR_RATE
            settings_row.save()
            self.stdout.write(
                f"  set exchange rate to {DEFAULT_USD_TO_KHR_RATE} KHR per USD"
            )
        return filing_status

    # ------------------------------------------------------------------
    # users / employees
    # ------------------------------------------------------------------

    def _ensure_employee(
        self,
        company,
        department,
        job_position,
        employee_type,
        work_type,
        shift,
        index,
        username,
        first,
        last,
        gender,
        marital,
        children,
        wage,
    ):
        user_model = get_user_model()
        user = user_model.objects.filter(username=username).first()
        if user is None:
            user = user_model(
                username=username,
                email=f"{username}@example.com",
                first_name=first,
                last_name=last,
            )
            user.set_password(PASSWORD)
            user.save()
            self.stdout.write(f"  created user: {username} ({PASSWORD})")

        employee = Employee.objects.filter(employee_user_id=user).first()
        if employee is None:
            employee = Employee(
                employee_user_id=user,
                badge_id=f"T{index:03d}",
                employee_first_name=first,
                employee_last_name=last,
                email=f"{username}@example.com",
                phone=f"+8559012345{index:02d}",
                gender=gender,
                marital_status=marital,
                children=children,
                dob=datetime.date(1995, 3, 15),
                country="Cambodia",
                state="Phnom Penh",
                city="Phnom Penh",
            )
            employee.save()

        work_info = EmployeeWorkInformation.objects.filter(employee_id=employee).first()
        if work_info is None:
            work_info = EmployeeWorkInformation(
                employee_id=employee,
                company_id=company,
                department_id=department,
                job_position_id=job_position,
                employee_type_id=employee_type,
                work_type_id=work_type,
                shift_id=shift,
                date_joining=datetime.date.today().replace(day=1),
                # NOTE: the EmployeeWorkInformation post_save signal
                # (payroll/signals.py) auto-creates an active contract with
                # wage = basic_salary, so keep the two in sync.
                basic_salary=int(wage),
                location="Phnom Penh HQ",
            )
            work_info.save()
        elif work_info.basic_salary != int(wage):
            work_info.basic_salary = int(wage)
            work_info.save()
        return employee

    def _ensure_bank_details(self, employee, index):
        if EmployeeBankDetails.objects.filter(employee_id=employee).exists():
            return
        EmployeeBankDetails(
            employee_id=employee,
            bank_name="ACLEDA Bank",
            account_number=f"0000-11-22-33-{index:04d}",
            branch="Phnom Penh Main",
        ).save()

    def _ensure_contract(self, employee, wage, filing_status):
        """
        Create (or update) the employee's active contract.

        NOTE: the EmployeeWorkInformation post_save signal already created an
        active contract with wage = work_info.basic_salary, so an existing
        contract is updated here instead of being skipped.
        """
        contract = employee.contract_set.filter(contract_status="active").first()
        if contract is None:
            Contract(
                contract_name=f"{employee.employee_first_name} - monthly contract",
                employee_id=employee,
                contract_start_date=datetime.date.today().replace(day=1),
                wage_type="monthly",
                pay_frequency="monthly",
                wage=wage,
                filing_status=filing_status,
                contract_status="active",
                department=employee.employee_work_info.department_id,
                job_position=employee.employee_work_info.job_position_id,
                shift=employee.employee_work_info.shift_id,
                work_type=employee.employee_work_info.work_type_id,
            ).save()
            return
        updated = False
        if contract.wage != wage:
            contract.wage = wage
            updated = True
        if contract.filing_status_id != filing_status:
            contract.filing_status = filing_status
            updated = True
        if updated:
            contract.save()

    # ------------------------------------------------------------------
    # overtime
    # ------------------------------------------------------------------

    def _ensure_ot_allowance(self, ot_employees):
        allowance = Allowance.objects.filter(
            title="Overtime Allowance", based_on="overtime"
        ).first()
        if allowance is None:
            allowance = Allowance(
                title="Overtime Allowance",
                is_taxable=True,
                is_fixed=False,
                based_on="overtime",
                amount_per_one_hr=OT_HOURLY_RATE,
            )
            allowance.save()
        allowance.specific_employees.set(ot_employees)
        return allowance

    def _ensure_overtime_attendance(self, ot_employees, shift, work_type):
        try:
            from attendance.models import Attendance
        except Exception:
            self.stdout.write(
                self.style.WARNING(
                    "  attendance app not installed - skipping overtime records"
                )
            )
            return

        today = datetime.date.today()
        # Approved overtime on the last few completed days of the previous
        # month, so it lands inside the usual payslip generation period.
        first_of_month = today.replace(day=1)
        last_of_prev_month = first_of_month - datetime.timedelta(days=1)
        ot_dates = [
            last_of_prev_month - datetime.timedelta(days=offset) for offset in (0, 1, 2, 3)
        ]

        for employee in ot_employees:
            created = 0
            for date in ot_dates:
                exists = Attendance.objects.filter(
                    employee_id=employee, attendance_date=date
                ).exists()
                if exists:
                    continue
                Attendance(
                    employee_id=employee,
                    attendance_date=date,
                    shift_id=shift,
                    work_type_id=work_type,
                    attendance_clock_in_date=date,
                    attendance_clock_in=datetime.time(8, 0),
                    attendance_clock_out_date=date,
                    attendance_clock_out=datetime.time(19, 0),
                    attendance_worked_hour="11:00",
                    minimum_hour="08:00",
                    attendance_overtime="03:00",
                    attendance_overtime_approve=True,
                    attendance_validated=True,
                    at_work_second=11 * 3600,
                    overtime_second=3 * 3600,
                    approved_overtime_second=3 * 3600,
                ).save()
                created += 1
            if created:
                self.stdout.write(
                    f"  {created} approved OT attendance day(s) for "
                    f"{employee.employee_first_name} ({OT_HOURLY_RATE}/h x 3h "
                    f"= {OT_HOURLY_RATE * 3} per day)"
                )

    # ------------------------------------------------------------------
    # summary
    # ------------------------------------------------------------------

    def _print_summary(self, employees, ot_allowance, filing_status):
        settings_row = PayrollSettings.objects.first()
        rate = settings_row.usd_to_khr_rate if settings_row else DEFAULT_USD_TO_KHR_RATE

        header = (
            f"{'Login':<14}{'Employee':<24}{'Marital status':<30}"
            f"{'Dep.':<6}{'Wage':>10}  Expected tax"
        )
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for employee in employees:
            user = employee.employee_user_id
            contract = employee.contract_set.filter(contract_status="active").first()
            wage = contract.wage if contract else 0
            dependents = employee.get_tax_dependent_count()
            expected_rate = self._expected_tax_rate(
                wage, dependents, rate, filing_status
            )
            marital = employee.get_marital_status_display()
            full_name = f"{employee.employee_first_name} {employee.employee_last_name}"
            self.stdout.write(
                f"{user.username:<14}{full_name:<24}{marital:<30}"
                f"{dependents:<6}{wage:>10.2f}  {expected_rate}"
            )
        names = ", ".join(e.employee_first_name for e in ot_allowance.specific_employees.all())
        self.stdout.write(
            self.style.NOTICE(
                f"\nOT: '{ot_allowance.title}' at {ot_allowance.amount_per_one_hr} "
                f"per approved overtime hour, assigned to: {names}"
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                "Next: log in as admin, open Payroll > Payslips > Generate for the "
                "previous month to see tax + OT on the payslips."
            )
        )

    def _expected_tax_rate(self, wage_usd, dependents, usd_to_khr_rate, filing_status):
        """
        Rough preview of the tax bracket the employee falls into (KHR,
        mirrors payroll/methods/tax_calc.py). Uses the brackets actually
        stored in the database for the given filing status.
        """
        if not usd_to_khr_rate:
            return "no exchange rate"
        income_khr = wage_usd * usd_to_khr_rate
        pension = income_khr * 0.02 if income_khr < 1_200_000.0 else 24_000.0
        taxable = max(income_khr - pension - dependents * 150_000.0, 0.0)
        brackets = TaxBracket.objects.filter(filing_status_id=filing_status).order_by(
            "min_income"
        )
        for bracket in brackets:
            if bracket.min_income <= taxable <= (bracket.max_income or math.inf):
                return f"{bracket.tax_rate:g}% bracket"
        return "0% bracket"
