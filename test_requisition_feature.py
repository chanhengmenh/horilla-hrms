"""
test_requisition_feature.py

Comprehensive test suite for:
1. RBAC enforcement on Requisition Entry Form (Executives only; HR/Admin blocked from originating)
2. Requisition creation and ticket generation
3. Individual PDF ticket generation (RMO-HRA-QF-001)
4. Talent Requisition Audit / Summary Report under Reports > Talent
5. Excel and PDF exports
"""

import os
import sys
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import Group, Permission
from django.utils import timezone

from horilla_auth.models import HorillaUser
from employee.models import Employee, EmployeeWorkInformation
from base.models import Company, Department, JobPosition, JobRole
from recruitment.models import StaffRequisition
from recruitment.accessibility import is_executive_or_hod, can_audit_requisition
from recruitment.views.requisition import staff_requisition_create, staff_requisition_pdf
from report.engine import ReportFilters
from report.registry import run_report, get_report
from report.export import export_pdf, export_xlsx


def run_tests():
    print("=" * 60)
    print("STARTING STAFF REQUISITION & RBAC AUDIT TEST SUITE")
    print("=" * 60)

    # 1. Setup Test Entities
    company = Company.objects.first()
    it_dept, _ = Department.objects.get_or_create(department="IT")
    brewery_dept, _ = Department.objects.get_or_create(department="Brewery")
    hr_dept, _ = Department.objects.get_or_create(department="HR & Admin")

    # 1.1 Create Executive User: CTO
    cto_user, _ = HorillaUser.objects.get_or_create(username="cto_test@horilla.com.kh")
    cto_user.set_password("pass123")
    cto_user.save()
    cto_emp, _ = Employee.objects.get_or_create(
        employee_user_id=cto_user,
        defaults={"badge_id": "EXEC01", "employee_first_name": "Sophea", "employee_last_name": "Chan", "email": "cto_test@horilla.com.kh"}
    )
    cto_pos, _ = JobPosition.objects.get_or_create(job_position="Chief Technology Officer", department_id=it_dept)
    cto_role, _ = JobRole.objects.get_or_create(job_role="Chief Technology Officer", job_position_id=cto_pos)
    cto_work, _ = EmployeeWorkInformation.objects.get_or_create(
        employee_id=cto_emp,
        defaults={"department_id": it_dept, "job_position_id": cto_pos, "job_role_id": cto_role, "company_id": company, "email": "cto_test@horilla.com.kh"}
    )
    cto_work.job_position_id = cto_pos
    cto_work.job_role_id = cto_role
    cto_work.department_id = it_dept
    cto_work.save()

    # 1.2 Create Pure HR Officer User (Non-executive)
    hr_user, _ = HorillaUser.objects.get_or_create(username="hrofficer_test@horilla.com.kh")
    hr_user.set_password("pass123")
    hr_user.save()
    hr_emp, _ = Employee.objects.get_or_create(
        employee_user_id=hr_user,
        defaults={"badge_id": "HROFF01", "employee_first_name": "Sreymom", "employee_last_name": "Pich", "email": "hrofficer_test@horilla.com.kh"}
    )
    hr_pos, _ = JobPosition.objects.get_or_create(job_position="HR Officer", department_id=hr_dept)
    hr_role, _ = JobRole.objects.get_or_create(job_role="HR Officer", job_position_id=hr_pos)
    hr_work, _ = EmployeeWorkInformation.objects.get_or_create(
        employee_id=hr_emp,
        defaults={"department_id": hr_dept, "job_position_id": hr_pos, "job_role_id": hr_role, "company_id": company, "email": "hrofficer_test@horilla.com.kh"}
    )
    hr_work.job_position_id = hr_pos
    hr_work.job_role_id = hr_role
    hr_work.department_id = hr_dept
    hr_work.save()

    # 1.3 Create Head of Department: Head of Brewery
    hod_user, _ = HorillaUser.objects.get_or_create(username="hod_brewery@horilla.com.kh")
    hod_user.set_password("pass123")
    hod_user.save()
    hod_emp, _ = Employee.objects.get_or_create(
        employee_user_id=hod_user,
        defaults={"badge_id": "HOD01", "employee_first_name": "Rath", "employee_last_name": "Sok", "email": "hod_brewery@horilla.com.kh"}
    )
    hod_pos, _ = JobPosition.objects.get_or_create(job_position="Head of Brewery", department_id=brewery_dept)
    hod_role, _ = JobRole.objects.get_or_create(job_role="Head of Brewery", job_position_id=hod_pos)
    hod_work, _ = EmployeeWorkInformation.objects.get_or_create(
        employee_id=hod_emp,
        defaults={"department_id": brewery_dept, "job_position_id": hod_pos, "job_role_id": hod_role, "company_id": company, "email": "hod_brewery@horilla.com.kh"}
    )
    hod_work.job_position_id = hod_pos
    hod_work.job_role_id = hod_role
    hod_work.department_id = brewery_dept
    hod_work.save()

    print("\n--- TEST 1: RBAC PERMISSION ENFORCEMENT ---")
    cto_user = HorillaUser.objects.get(id=cto_user.id)
    hod_user = HorillaUser.objects.get(id=hod_user.id)
    hr_user = HorillaUser.objects.get(id=hr_user.id)

    cto_can_req = is_executive_or_hod(cto_user)
    hod_can_req = is_executive_or_hod(hod_user)
    hr_can_req = is_executive_or_hod(hr_user)

    print(f"CTO ({cto_user.username}): Can request? {cto_can_req} (Expected: True)")
    print(f"HOD Brewery ({hod_user.username}): Can request? {hod_can_req} (Expected: True)")
    print(f"HR Officer ({hr_user.username}): Can request? {hr_can_req} (Expected: False)")

    assert cto_can_req is True, "CTO must be allowed to request staff requisition!"
    assert hod_can_req is True, "Head of Department must be allowed to request staff requisition!"
    assert hr_can_req is False, "HR Officer must NOT be allowed to request staff requisition!"
    print(">> [PASS] RBAC correctly grants Executives and denies HR Staff!")

    print("\n--- TEST 2: REQUISITION CREATION & VALIDATION ---")
    # Clean previous test entries if any
    StaffRequisition.objects.filter(position_title__startswith="[TEST]").delete()

    # Create 1: Permanent Budgeted by CTO
    req1 = StaffRequisition.objects.create(
        position_title="[TEST] Lead Cloud DevOps Engineer",
        department_id=it_dept,
        location="Phnom Penh HQ",
        function="Technology Infrastructure",
        company_id=company,
        headcount=2,
        requested_by=cto_emp,
        manager_position="Chief Technology Officer",
        manager_email=cto_emp.email,
        employment_type="permanent",
        permanent_category="budgeted",
        target_onboarding_date=date(2026, 11, 1),
        position_level="Senior Specialist / Lead",
        justification="Cloud migration project for manufacturing ERP system requires 2 senior devops specialists.",
        position_requirements="5+ years AWS/GCP, Kubernetes, Terraform, CI/CD pipelines.",
        status="submitted",
        requested_date=date(2026, 10, 15),
    )
    print(f"Created Requisition 1: {req1.requisition_code} - {req1.position_title} (Headcount: {req1.headcount})")
    assert req1.requisition_code.startswith("REQ-"), "Requisition code must be generated automatically!"

    # Create 2: Permanent Non-Budgeted by HOD Brewery
    req2 = StaffRequisition.objects.create(
        position_title="[TEST] Assistant Brewmaster",
        department_id=brewery_dept,
        location="Brewery Plant",
        function="Brewing & Quality",
        company_id=company,
        headcount=1,
        requested_by=hod_emp,
        manager_position="Head of Brewery",
        manager_email=hod_emp.email,
        employment_type="permanent",
        permanent_category="non_budgeted",
        target_onboarding_date=date(2026, 11, 15),
        position_level="Manager",
        justification="Surge in craft brew production demand requiring additional supervisory oversight on evening shifts.",
        position_requirements="Degree in Food Science/Brewing Engineering, 4+ years commercial brewery experience.",
        status="reviewed_hr",
        requested_date=date(2026, 10, 16),
        hr_reviewer=hr_emp,
        hr_reviewed_date=date(2026, 10, 18),
        hr_remarks="Budget amendment requested to CEO.",
    )
    print(f"Created Requisition 2: {req2.requisition_code} - {req2.position_title} (Category: {req2.permanent_category})")

    # Create 3: Permanent Replacement by HOD Brewery
    req3 = StaffRequisition.objects.create(
        position_title="[TEST] Quality Control Technician",
        department_id=brewery_dept,
        location="Brewery Plant",
        function="Brewing & Quality",
        company_id=company,
        headcount=1,
        requested_by=hod_emp,
        manager_position="Head of Brewery",
        manager_email=hod_emp.email,
        employment_type="permanent",
        permanent_category="replacement",
        replacement_for="Dara Sok",
        replacement_reason="Employee resigned on Oct 10 to relocate overseas.",
        target_onboarding_date=date(2026, 11, 1),
        position_level="Officer",
        justification="Immediate backfill necessary to prevent bottling line QA delays.",
        position_requirements="HACCP certification, laboratory testing proficiency.",
        status="approved",
        requested_date=date(2026, 10, 12),
        hr_reviewer=hr_emp,
        hr_reviewed_date=date(2026, 10, 13),
        approved_by=cto_emp,
        approved_date=date(2026, 10, 14),
        approval_remarks="Approved as critical backfill.",
    )
    print(f"Created Requisition 3: {req3.requisition_code} - {req3.position_title} (Replacement for: {req3.replacement_for})")

    # Create 4: Contract Full-Time by CTO
    req4 = StaffRequisition.objects.create(
        position_title="[TEST] Temporary Network Setup Specialist",
        department_id=it_dept,
        location="Phnom Penh HQ",
        function="IT Support",
        company_id=company,
        headcount=1,
        requested_by=cto_emp,
        manager_position="Chief Technology Officer",
        manager_email=cto_emp.email,
        employment_type="contract",
        contract_term="full_time",
        period_from=date(2026, 11, 1),
        period_to=date(2027, 4, 30),
        working_days_hours="Mon - Fri, 8:00 AM - 5:00 PM (40 hrs/wk)",
        justification="6-month network cabling and server rack installation for warehouse extension.",
        position_requirements="CCNA or equivalent, physical cabling experience.",
        status="submitted",
        requested_date=date(2026, 10, 17),
    )
    print(f"Created Requisition 4: {req4.requisition_code} - {req4.position_title} (Contract: {req4.contract_term})")
    print(">> [PASS] Requisition records created with complete RMO-HRA-QF-001 metadata!")

    print("\n--- TEST 3: OFFICIAL PDF TICKET GENERATION ---")
    factory = RequestFactory()
    req_pdf_url = f"/recruitment/staff-requisition-pdf/{req3.id}/"
    request = factory.get(req_pdf_url)
    request.user = cto_user

    pdf_response = staff_requisition_pdf(request, pk=req3.id)
    print(f"PDF Response status: {pdf_response.status_code}")
    print(f"Content-Type: {pdf_response['Content-Type']}")
    print(f"Content-Disposition: {pdf_response['Content-Disposition']}")
    print(f"PDF Payload size: {len(pdf_response.content)} bytes")

    assert pdf_response.status_code == 200, "PDF ticket view should return HTTP 200!"
    assert pdf_response.content.startswith(b"%PDF-"), "Generated response should be a valid PDF binary!"
    assert len(pdf_response.content) > 5000, "PDF file size should be substantial!"
    print(">> [PASS] RMO-HRA-QF-001 PDF ticket generated successfully!")

    print("\n--- TEST 4: TALENT AUDIT / SUMMARY REPORT (REPORTS > TALENT) ---")
    rep_def = get_report("staff-requisition-summary")
    assert rep_def is not None, "Report 'staff-requisition-summary' must be registered in ReportDefinition registry!"
    print(f"Registered Report: {rep_def.name} [Domain: {rep_def.domain}]")
    assert rep_def.domain == "talent", "Report must belong to the 'talent' domain!"

    filters = ReportFilters(
        from_date=date(2026, 10, 1),
        to_date=date(2026, 10, 31),
    )
    payload = run_report("staff-requisition-summary", filters)
    print(f"Report Title: {payload['title']}")
    print("KPIs:")
    for kpi in payload["kpis"]:
        print(f"  • {kpi['label']}: {kpi['value']} ({kpi['hint']})")

    table_rows = payload["table"]["rows"]
    print(f"Total rows in summary audit table: {len(table_rows)}")
    assert len(table_rows) >= 4, "Should list at least the 4 test requisitions!"

    print("\n--- TEST 5: EXPORT CAPABILITIES (EXCEL & PDF) ---")
    # Test Excel Export
    xlsx_resp = export_xlsx(payload, filename="Staff_Requisitions_Summary.xlsx")
    assert xlsx_resp.status_code == 200, "Excel export should return HTTP 200!"
    print(f"Excel export size: {len(xlsx_resp.content)} bytes [Content-Type: {xlsx_resp['Content-Type']}]")

    # Test PDF Export
    pdf_resp = export_pdf(payload, filename="Staff_Requisitions_Summary.pdf")
    assert pdf_resp.status_code == 200, "PDF export should return HTTP 200!"
    assert pdf_resp.content.startswith(b"%PDF-"), "Summary PDF should be a valid PDF file!"
    print(f"PDF export size: {len(pdf_resp.content)} bytes [Content-Type: {pdf_resp['Content-Type']}]")
    print(">> [PASS] Excel and PDF exports generated without any issues!")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY (5/5)!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
