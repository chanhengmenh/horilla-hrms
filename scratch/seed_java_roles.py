import os
import sys

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
import django
django.setup()

from datetime import date
from recruitment.models import StaffRequisition
from base.models import Department, Company
from employee.models import Employee

dept = Department.objects.filter(is_active=True).first()
emp = Employee.objects.filter(is_active=True).first()
company = Company.objects.filter(is_active=True).first()

roles_to_seed = [
    ("Java Developer", "Software Engineering", "budgeted"),
    ("Java Specialist", "Software Engineering", "budgeted"),
    ("Java Junior", "Software Engineering", "budgeted"),
    ("Java Senior", "Software Engineering", "budgeted"),
]

for role_title, func, category in roles_to_seed:
    req = StaffRequisition.objects.filter(position_title__iexact=role_title, is_active=True).first()
    if not req:
        req = StaffRequisition.objects.create(
            position_title=role_title,
            department_id=dept,
            location="Phnom Penh HQ",
            function=func,
            company_id=company,
            headcount=1,
            requested_by=emp,
            manager_position="Engineering Director",
            manager_email=getattr(emp, "email", "manager@company.com"),
            employment_type="permanent",
            permanent_category=category,
            target_onboarding_date=date(2026, 11, 1),
            justification=f"Immediate headcount requirement for {role_title} to support core platform expansion.",
            position_requirements=f"Proficiency in Java, Spring Boot, microservices architecture, and SQL database operations.",
            status="submitted",
            is_active=True,
        )
        print(f"[CREATED] {role_title} -> {req.requisition_code} (ID: {req.id})")
    else:
        print(f"[EXISTS] {role_title} -> {req.requisition_code} (ID: {req.id})")
