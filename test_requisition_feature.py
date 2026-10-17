"""
test_requisition_feature.py

Comprehensive test suite verifying all 5 core system requirements:
1. Four Departments Only: Technical Department, Admin-HR Department, Finance Department, Sales Department.
2. Employee Western Renaming: All 54 employees renamed to fictional Western names.
3. Staff Requisition RBAC Enforcement:
   - [HR] and [ADMIN] have full access to Request and Review.
   - Only CEO (is_ceo) has authority to Approve (can_approve_requisition).
   - Regular staff cannot request or review.
4. Employment Period Optional for Contract and Intern requisitions.
5. Job Description (JD) document is strictly mandatory for hard print and review.
6. PDF Ticket generation (RMO-HRA-QF-001) and Talent Audit / Summary Report exports.
"""

import os
import sys
import django
from datetime import date, timedelta
from io import BytesIO

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.contrib.auth.models import Group, Permission
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone

from horilla_auth.models import HorillaUser
from employee.models import Employee, EmployeeWorkInformation
from base.models import Company, Department, JobPosition, JobRole
from recruitment.models import StaffRequisition
from recruitment.accessibility import (
    is_ceo,
    can_request_requisition,
    can_review_requisition,
    can_approve_requisition,
    is_executive_or_hod,
)
from recruitment.forms import StaffRequisitionForm
from recruitment.views.requisition import (
    staff_requisition_create,
    staff_requisition_status_update,
    staff_requisition_pdf,
)
from report.engine import ReportFilters
from report.registry import run_report, get_report
from report.export import export_pdf, export_xlsx


def attach_request_middleware(request):
    """Attach session and messages storage to a RequestFactory request."""
    session_middleware = SessionMiddleware(lambda req: None)
    session_middleware.process_request(request)
    request.session.save()
    setattr(request, '_messages', FallbackStorage(request))
    return request


def run_tests():
    print("=" * 70)
    print("STARTING HORILLA HRMS SYSTEM REQUIREMENTS & RBAC AUDIT TEST SUITE")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. SETUP TEST ENTITIES & RETRIEVE FIXTURES
    # -------------------------------------------------------------
    company = Company.objects.first()
    assert company is not None, "Company record must exist in database!"

    # -------------------------------------------------------------
    # TEST 1: COMPANY STRUCTURE CONSOLIDATION (4 DEPARTMENTS ONLY)
    # -------------------------------------------------------------
    print("\n--- TEST 1: COMPANY STRUCTURE (4 DEPARTMENTS ONLY) ---")
    all_depts = list(Department.objects.values_list("department", flat=True))
    print(f"Active departments in DB ({len(all_depts)}): {all_depts}")
    expected_depts = {
        "Technical Department",
        "Admin-HR Department",
        "Finance Department",
        "Sales Department",
    }
    assert set(all_depts) == expected_depts, (
        f"Departments must strictly be {expected_depts}, found {set(all_depts)}"
    )
    assert len(all_depts) == 4, f"Exactly 4 departments must exist, found {len(all_depts)}"
    print(">> [PASS] Company structure strictly consolidated to 4 standard departments!")

    tech_dept = Department.objects.get(department="Technical Department")
    admin_hr_dept = Department.objects.get(department="Admin-HR Department")
    finance_dept = Department.objects.get(department="Finance Department")
    sales_dept = Department.objects.get(department="Sales Department")

    # -------------------------------------------------------------
    # TEST 2: EMPLOYEE WESTERN FICTIONAL RENAMING AUDIT
    # -------------------------------------------------------------
    print("\n--- TEST 2: EMPLOYEE WESTERN FICTIONAL RENAMING AUDIT ---")
    employees = list(Employee.objects.all())
    print(f"Total employees in system: {len(employees)}")
    assert len(employees) >= 50, f"Expected full employee roster, found {len(employees)}"

    # Check key fixtures
    ceo_emp = Employee.objects.filter(badge_id="EMP001").first()
    assert ceo_emp is not None, "Badge EMP001 (CEO) must exist!"
    assert ceo_emp.get_full_name() == "Eleanor Sterling", f"EMP001 must be Eleanor Sterling, found {ceo_emp.get_full_name()}"

    admin_emp = Employee.objects.filter(badge_id="ADMIN01").first()
    assert admin_emp is not None, "Badge ADMIN01 (Admin) must exist!"
    assert admin_emp.get_full_name() == "Arthur Pendelton", f"ADMIN01 must be Arthur Pendelton, found {admin_emp.get_full_name()}"

    cto_emp = Employee.objects.filter(badge_id="EXEC01").first()
    assert cto_emp is not None, "Badge EXEC01 (CTO) must exist!"
    assert cto_emp.get_full_name() == "Ethan Vance", f"EXEC01 must be Ethan Vance, found {cto_emp.get_full_name()}"

    hr_emp = Employee.objects.filter(badge_id="HROFF01").first()
    assert hr_emp is not None, "Badge HROFF01 (HR Officer) must exist!"
    assert hr_emp.get_full_name() == "Mason Brooks", f"HROFF01 must be Mason Brooks, found {hr_emp.get_full_name()}"

    hod_emp = Employee.objects.filter(badge_id="HOD01").first()
    assert hod_emp is not None, "Badge HOD01 (Sales Head) must exist!"
    assert hod_emp.get_full_name() == "Liam O'Connor", f"HOD01 must be Liam O'Connor, found {hod_emp.get_full_name()}"

    # Verify absence of legacy Cambodian strings
    for emp in employees:
        full = emp.get_full_name()
        for forbidden in ["Sophea", "Sreymom", "Sarvorneat", "Dara", "Sok", "Pich", "Thida"]:
            assert forbidden.lower() not in full.lower(), f"Employee {emp.badge_id} ({full}) contains legacy name fragment '{forbidden}'"
    print(">> [PASS] All employees successfully verified as synthetic Western fictional names!")

    # Retrieve user accounts
    ceo_user = ceo_emp.employee_user_id
    admin_user = admin_emp.employee_user_id
    cto_user = cto_emp.employee_user_id
    hr_user = hr_emp.employee_user_id
    hod_user = hod_emp.employee_user_id
    regular_emp = Employee.objects.filter(badge_id="EMP020").first()  # Abigail Clark
    regular_user = regular_emp.employee_user_id

    # -------------------------------------------------------------
    # TEST 3: STAFF REQUISITION RBAC PERMISSION ENFORCEMENT
    # -------------------------------------------------------------
    print("\n--- TEST 3: RBAC PERMISSION ENFORCEMENT ---")
    print(f"CEO ({ceo_user.username}): is_ceo={is_ceo(ceo_user)}, can_req={can_request_requisition(ceo_user)}, can_rev={can_review_requisition(ceo_user)}, can_appr={can_approve_requisition(ceo_user)}")
    print(f"HR ({hr_user.username}): is_ceo={is_ceo(hr_user)}, can_req={can_request_requisition(hr_user)}, can_rev={can_review_requisition(hr_user)}, can_appr={can_approve_requisition(hr_user)}")
    print(f"Admin ({admin_user.username}): is_ceo={is_ceo(admin_user)}, can_req={can_request_requisition(admin_user)}, can_rev={can_review_requisition(admin_user)}, can_appr={can_approve_requisition(admin_user)}")
    print(f"CTO ({cto_user.username}): is_ceo={is_ceo(cto_user)}, can_req={can_request_requisition(cto_user)}, can_rev={can_review_requisition(cto_user)}, can_appr={can_approve_requisition(cto_user)}")
    print(f"Regular ({regular_user.username}): is_ceo={is_ceo(regular_user)}, can_req={can_request_requisition(regular_user)}, can_rev={can_review_requisition(regular_user)}, can_appr={can_approve_requisition(regular_user)}")

    # 3.1 CEO Permissions
    assert is_ceo(ceo_user) is True, "CEO user must be recognized as CEO!"
    assert can_request_requisition(ceo_user) is True, "CEO must be allowed to request headcount!"
    assert can_approve_requisition(ceo_user) is True, "CEO must be allowed to approve headcount!"

    # 3.2 HR Permissions: Full access to Request and Review, CANNOT Approve
    assert is_ceo(hr_user) is False, "HR user must NOT be recognized as CEO!"
    assert can_request_requisition(hr_user) is True, "HR must have full access to request staff requisition!"
    assert can_review_requisition(hr_user) is True, "HR must have full access to review staff requisition!"
    assert can_approve_requisition(hr_user) is False, "HR must NOT be allowed to approve staff requisition!"

    # 3.3 Admin Permissions: Full access to Request and Review, CANNOT Approve
    assert is_ceo(admin_user) is False, "Admin user must NOT be recognized as CEO!"
    assert can_request_requisition(admin_user) is True, "Admin must have full access to request staff requisition!"
    assert can_review_requisition(admin_user) is True, "Admin must have full access to review staff requisition!"
    assert can_approve_requisition(admin_user) is False, "Admin must NOT be allowed to approve staff requisition!"

    # 3.4 CTO / Department Head Permissions: Can request, CANNOT approve
    assert can_request_requisition(cto_user) is True, "CTO must be allowed to request headcount!"
    assert can_approve_requisition(cto_user) is False, "CTO must NOT be allowed to approve headcount!"
    assert can_request_requisition(hod_user) is True, "Sales Head must be allowed to request headcount!"
    assert can_approve_requisition(hod_user) is False, "Sales Head must NOT be allowed to approve headcount!"

    # 3.5 Regular Unprivileged Staff: Blocked from Requesting and Reviewing
    assert can_request_requisition(regular_user) is False, "Regular employee must NOT be allowed to request headcount!"
    assert can_review_requisition(regular_user) is False, "Regular employee must NOT be allowed to review headcount!"
    assert can_approve_requisition(regular_user) is False, "Regular employee must NOT be allowed to approve headcount!"

    print(">> [PASS] RBAC strictly enforces Request & Review for HR/Admin, and restricts Approve exclusively to CEO!")

    # -------------------------------------------------------------
    # TEST 4: FORM VALIDATION (MANDATORY JD & OPTIONAL CONTRACT/INTERN PERIOD)
    # -------------------------------------------------------------
    print("\n--- TEST 4: FORM VALIDATION (MANDATORY JD & OPTIONAL PERIODS) ---")

    # 4.1 Submitting without JD document MUST FAIL validation
    dummy_jd_file = SimpleUploadedFile(
        "Job_Description_Test.docx",
        b"Sample Job Description content for hard print verification.",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    data_without_jd = {
        "position_title": "[TEST] Contract Network Engineer",
        "department_id": tech_dept.id,
        "location": "Phnom Penh Main Office",
        "function": "IT Infrastructure",
        "headcount": 1,
        "employment_type": "contract",
        "contract_term": "full_time",
        "working_days_hours": "Mon-Fri 8am-5pm",
        "justification": "Network hardware installation project",
    }
    form_no_jd = StaffRequisitionForm(data=data_without_jd, files={})
    assert form_no_jd.is_valid() is False, "Form submitted without JD document must fail validation!"
    assert "job_description_file" in form_no_jd.errors, "Form must have error on 'job_description_file'!"
    print(">> [PASS] Requisition rejected when JD document is missing (Mandatory for hard print)!")

    # 4.2 Submitting Contract Requisition with JD document but WITHOUT period_from/period_to MUST SUCCEED
    dummy_jd_file.seek(0)
    data_contract_no_period = {
        "position_title": "[TEST] Contract Network Engineer",
        "department_id": tech_dept.id,
        "location": "Phnom Penh Main Office",
        "function": "IT Infrastructure",
        "headcount": 1,
        "employment_type": "contract",
        "contract_term": "full_time",
        "period_from": "",  # Optional
        "period_to": "",    # Optional
        "working_days_hours": "Mon-Fri 8am-5pm",
        "justification": "Network hardware installation project",
    }
    form_contract = StaffRequisitionForm(
        data=data_contract_no_period,
        files={"job_description_file": dummy_jd_file}
    )
    assert form_contract.is_valid() is True, f"Contract requisition without dates should be valid! Errors: {form_contract.errors}"
    print(">> [PASS] Contract requisition without employment period successfully validated (Period is Optional)!")

    # 4.3 Submitting Intern Requisition with JD document but WITHOUT period_from/period_to MUST SUCCEED
    dummy_jd_file.seek(0)
    data_intern_no_period = {
        "position_title": "[TEST] Summer Software Intern",
        "department_id": tech_dept.id,
        "location": "Phnom Penh Main Office",
        "function": "Software Development",
        "headcount": 2,
        "employment_type": "intern",
        "contract_term": "full_time",
        "period_from": "",  # Optional
        "period_to": "",    # Optional
        "working_days_hours": "Mon-Fri 8:30am-5pm",
        "justification": "Assisting frontend UI improvements",
    }
    form_intern = StaffRequisitionForm(
        data=data_intern_no_period,
        files={"job_description_file": dummy_jd_file}
    )
    assert form_intern.is_valid() is True, f"Intern requisition without dates should be valid! Errors: {form_intern.errors}"
    print(">> [PASS] Intern requisition without employment period successfully validated (Period is Optional)!")

    # -------------------------------------------------------------
    # TEST 5: REQUISITION WORKFLOW & APPROVAL ENFORCEMENT
    # -------------------------------------------------------------
    print("\n--- TEST 5: REQUISITION WORKFLOW & APPROVAL RBAC ENFORCEMENT ---")
    # Clean previous test entries
    StaffRequisition.objects.filter(position_title__startswith="[TEST]").delete()

    # Step 5.1: HR Officer originates headcount request
    test_req = StaffRequisition.objects.create(
        position_title="[TEST] Finance Analyst Specialist",
        department_id=finance_dept,
        location="Main Financial Office",
        function="Financial Planning & Analysis",
        company_id=company,
        headcount=1,
        requested_by=hr_emp,
        manager_position="HR Officer",
        manager_email=hr_emp.email,
        employment_type="contract",
        contract_term="full_time",
        period_from=None,  # Optional
        period_to=None,    # Optional
        working_days_hours="Mon - Fri, 8:00 AM - 5:00 PM (40 hrs/wk)",
        justification="Year-end audit and compliance reconciliation.",
        position_requirements="CPA/ACCA qualified, 3+ years enterprise audit experience.",
        job_description_file="Job_Description_Finance_Analyst.pdf",
        status="submitted",
        requested_date=date(2026, 10, 16),
    )
    print(f"HR Created Requisition: {test_req.requisition_code} - {test_req.position_title} (Status: {test_req.status})")
    assert test_req.status == "submitted", "Initial status must be submitted"
    assert test_req.requisition_code.startswith("REQ-"), "Requisition code must be generated automatically"

    # Step 5.2: Admin reviews the requisition
    factory = RequestFactory()
    review_request = factory.post(
        f"/recruitment/staff-requisition-status/{test_req.id}/",
        data={"action": "hr_review", "remarks": "Reviewed and verified against Q4 budget."}
    )
    review_request.user = admin_user
    attach_request_middleware(review_request)

    staff_requisition_status_update(review_request, pk=test_req.id)
    test_req.refresh_from_db()
    assert test_req.status == "reviewed_hr", f"Status should be reviewed_hr, got {test_req.status}"
    assert test_req.hr_reviewer == admin_emp, "HR reviewer should be recorded"
    print(f">> [PASS] Admin successfully reviewed requisition: Status = {test_req.status}")

    # Step 5.3: Security Test - HR Officer attempts to execute ceo_approve
    hr_approve_request = factory.post(
        f"/recruitment/staff-requisition-status/{test_req.id}/",
        data={"action": "ceo_approve", "remarks": "HR attempting unauthorized CEO approval."}
    )
    hr_approve_request.user = hr_user
    attach_request_middleware(hr_approve_request)

    staff_requisition_status_update(hr_approve_request, pk=test_req.id)
    test_req.refresh_from_db()
    assert test_req.status == "reviewed_hr", f"HR must NOT be able to approve! Status was changed to {test_req.status}"
    print(">> [PASS] HR Officer blocked from approving staff requisition (Status remains reviewed_hr)!")

    # Step 5.4: Security Test - Admin attempts to execute ceo_approve
    admin_approve_request = factory.post(
        f"/recruitment/staff-requisition-status/{test_req.id}/",
        data={"action": "ceo_approve", "remarks": "Admin attempting unauthorized CEO approval."}
    )
    admin_approve_request.user = admin_user
    attach_request_middleware(admin_approve_request)

    staff_requisition_status_update(admin_approve_request, pk=test_req.id)
    test_req.refresh_from_db()
    assert test_req.status == "reviewed_hr", f"Admin must NOT be able to approve! Status was changed to {test_req.status}"
    print(">> [PASS] Admin blocked from approving staff requisition (Status remains reviewed_hr)!")

    # Step 5.5: CEO executes ceo_approve
    ceo_approve_request = factory.post(
        f"/recruitment/staff-requisition-status/{test_req.id}/",
        data={"action": "ceo_approve", "remarks": "Approved by Eleanor Sterling (CEO)."}
    )
    ceo_approve_request.user = ceo_user
    attach_request_middleware(ceo_approve_request)

    staff_requisition_status_update(ceo_approve_request, pk=test_req.id)
    test_req.refresh_from_db()
    assert test_req.status == "approved", f"Status should be approved, got {test_req.status}"
    assert test_req.approved_by == ceo_emp, f"Approved by must be CEO, got {test_req.approved_by}"
    assert test_req.approved_by_clean_name == "Eleanor Sterling", f"Clean name should be Eleanor Sterling, got {test_req.approved_by_clean_name}"
    print(f">> [PASS] CEO successfully approved requisition: Status = {test_req.status}, Approver = {test_req.approved_by_clean_name}")

    # -------------------------------------------------------------
    # TEST 6: OFFICIAL PDF TICKET GENERATION (RMO-HRA-QF-001)
    # -------------------------------------------------------------
    print("\n--- TEST 6: OFFICIAL PDF TICKET GENERATION ---")
    pdf_request = factory.get(f"/recruitment/staff-requisition-pdf/{test_req.id}/")
    pdf_request.user = ceo_user
    attach_request_middleware(pdf_request)

    pdf_response = staff_requisition_pdf(pdf_request, pk=test_req.id)
    assert pdf_response.status_code == 200, f"Expected 200, got {pdf_response.status_code}"
    assert pdf_response["Content-Type"] == "application/pdf", "Expected application/pdf"
    assert pdf_response.content.startswith(b"%PDF-"), "Generated response should be valid PDF binary"
    assert len(pdf_response.content) > 5000, f"PDF file size should be substantial (got {len(pdf_response.content)} bytes)"
    print(f">> [PASS] RMO-HRA-QF-001 PDF ticket generated successfully ({len(pdf_response.content):,} bytes)!")

    # -------------------------------------------------------------
    # TEST 7: TALENT AUDIT / SUMMARY REPORT & EXPORTS
    # -------------------------------------------------------------
    print("\n--- TEST 7: TALENT AUDIT REPORT & EXPORTS (REPORTS > TALENT) ---")
    rep_def = get_report("staff-requisition-summary")
    assert rep_def is not None, "Report 'staff-requisition-summary' must be registered in ReportDefinition registry!"
    assert rep_def.domain == "talent", "Report must belong to the 'talent' domain!"

    filters = ReportFilters(from_date=date(2026, 1, 1), to_date=date(2026, 12, 31))
    payload = run_report("staff-requisition-summary", filters)
    assert payload is not None, "Report run returned None"
    assert "kpis" in payload and "table" in payload, "Report payload missing expected keys"
    table_rows = payload["table"]["rows"]
    print(f"Report run completed. Table contains {len(table_rows)} requisitions.")
    assert len(table_rows) >= 1, "Should list at least the approved test requisition"

    # Export Excel
    xlsx_resp = export_xlsx(payload, filename="Staff_Requisitions_Summary.xlsx")
    assert xlsx_resp.status_code == 200, "Excel export should return HTTP 200!"
    print(f"Excel export verified ({len(xlsx_resp.content):,} bytes)")

    # Export PDF
    pdf_resp = export_pdf(payload, filename="Staff_Requisitions_Summary.pdf")
    assert pdf_resp.status_code == 200, "PDF export should return HTTP 200!"
    assert pdf_resp.content.startswith(b"%PDF-"), "Summary PDF should be a valid PDF binary!"
    print(f"PDF export verified ({len(pdf_resp.content):,} bytes)")
    print(">> [PASS] Talent Audit / Summary Report and exports working seamlessly!")

    print("\n" + "=" * 70)
    print("ALL 7 SYSTEM & RBAC VERIFICATION SUITES PASSED FLAWLESSLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
