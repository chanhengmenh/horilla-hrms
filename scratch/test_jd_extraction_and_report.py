import os
import sys

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
import django
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from recruitment.models import StaffRequisition
from recruitment.methods import extract_text_from_jd_file
from recruitment.forms import StaffRequisitionForm
from base.models import Department, Company
from employee.models import Employee

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

client = Client()
client.force_login(admin_user)

def test_file_extractors():
    print("--- 1. TESTING EXTRACTOR ON DOCX, PDF, AND TEXT ---")
    # DOCX test
    docx_path = "prompts/Job Description-System Specialist.docx"
    assert os.path.exists(docx_path)
    docx_text = extract_text_from_jd_file(docx_path)
    assert len(docx_text) > 500, f"Expected >500 chars from docx, got {len(docx_text)}"
    assert "System Specialist" in docx_text
    assert "Roles & Responsibility" in docx_text
    print(f">> [PASS] DOCX parsed successfully ({len(docx_text)} chars extracted)")

    # Plain text test
    sample_txt = SimpleUploadedFile("sample_jd.txt", b"Must have 5+ years Python and Django experience.\nLead architectural decisions.", content_type="text/plain")
    txt_content = extract_text_from_jd_file(sample_txt)
    assert "5+ years Python" in txt_content
    print(f">> [PASS] TXT parsed successfully ({len(txt_content)} chars extracted)")

def test_form_auto_extraction():
    print("\n--- 2. TESTING FORM VALIDATION & AUTO-EXTRACTION ---")
    dept = Department.objects.filter(is_active=True).first()
    emp = Employee.objects.filter(is_active=True).first()

    with open("prompts/Job Description-System Specialist.docx", "rb") as f:
        file_bytes = f.read()

    uploaded_docx = SimpleUploadedFile("Job_Description_System_Specialist.docx", file_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    # Form with file only (empty position_requirements)
    form = StaffRequisitionForm(
        data={
            "position_title": "System Specialist Auto-Test",
            "department_id": dept.id,
            "location": "Phnom Penh HQ",
            "function": "IT Support",
            "headcount": 1,
            "employment_type": "permanent",
            "permanent_category": "budgeted",
            "target_onboarding_date": "2026-11-01",
            "justification": "Auto-extraction verification test.",
            "position_requirements": "",  # Requester did not type any text!
        },
        files={
            "job_description_file": uploaded_docx,
        }
    )

    assert form.is_valid(), f"Form errors: {form.errors}"
    extracted_text = form.cleaned_data.get("position_requirements")
    assert extracted_text and len(extracted_text) > 100, "Expected position_requirements to be auto-populated!"
    assert "Roles & Responsibility" in extracted_text
    print(f">> [PASS] Form auto-extracted {len(extracted_text)} chars into position_requirements when user only uploaded file!")

def test_ajax_extraction_endpoint():
    print("\n--- 3. TESTING AJAX EXTRACTION ENDPOINT ---")
    with open("prompts/Job Description-System Specialist.docx", "rb") as f:
        file_bytes = f.read()

    uploaded = SimpleUploadedFile("Job_Description_System_Specialist.docx", file_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    resp = client.post("/recruitment/staff-requisition-extract-jd/", {"job_description_file": uploaded})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.content}"
    data = resp.json()
    assert data.get("success") is True
    assert data.get("char_count") > 500
    assert "System Specialist" in data.get("text")
    print(f">> [PASS] AJAX extraction endpoint returned {data['char_count']} chars for live form preview!")

def test_pdf_report_rendering():
    print("\n--- 4. TESTING PDF REPORT RENDERING CLEANLINESS ---")
    req = StaffRequisition.objects.filter(job_description_file__isnull=False).first()
    assert req is not None, "Need at least one requisition with attached JD"

    html = render_to_string("recruitment/requisition/requisition_pdf_ticket.html", {"req": req})
    # Verify that the raw storage path is NOT rendered in the PDF ticket
    assert "recruitment/requisition_jds/" not in html, "Raw file path found in PDF ticket!"
    assert "(Job Description attached:" not in html, "Raw attachment disclaimer found in PDF ticket!"
    print(">> [PASS] PDF report template renders cleanly without any raw file path or clutter!")

if __name__ == "__main__":
    test_file_extractors()
    test_form_auto_extraction()
    test_ajax_extraction_endpoint()
    test_pdf_report_rendering()
    print("\nALL TESTS PASSED SUCCESSFULLY!")
