"""
render_requisition_from_payload.py

CLI & programmatic engine to populate and render the official RMO Staff Requisition Form
(RMO-HRA-QF-001) from any JSON / Key-Value payload, strictly adhering to layout, styling,
typography, checkbox, and multi-page dynamic expansion rules.

Usage:
    python render_requisition_from_payload.py [input_payload.json] [output_path.pdf]
"""

import os
import sys
import json
import base64
from pathlib import Path

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
import django
django.setup()

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from base.methods import html_to_pdf_bytes


def render_requisition_pdf_from_dict(payload: dict, output_pdf_path: str = None) -> bytes:
    """
    Populates and renders the official RMO Staff Requisition Form (RMO-HRA-QF-001)
    from a dictionary / JSON payload into PDF bytes, saving to output_pdf_path if provided.
    """
    def _read_b64(rel_path):
        full_path = os.path.join(settings.BASE_DIR, rel_path)
        if os.path.exists(full_path):
            with open(full_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        return ""

    logo_b64 = _read_b64("recruitment/static/recruitment/images/rmo_logo.jpg")
    empty_b64 = _read_b64("recruitment/static/recruitment/images/chk_empty.png")
    checked_b64 = _read_b64("recruitment/static/recruitment/images/chk_checked.png")

    chk_empty_html = f'<img src="data:image/png;base64,{empty_b64}" width="8" height="8" style="vertical-align: middle;" />' if empty_b64 else '[&nbsp;]'
    chk_checked_html = f'<img src="data:image/png;base64,{checked_b64}" width="8" height="8" style="vertical-align: middle;" />' if checked_b64 else '[X]'

    class PayloadWrapper:
        def __init__(self, data):
            self._data = dict(data) if isinstance(data, dict) else {}

        def __getattr__(self, name):
            val = self._data.get(name)
            if val is None:
                if name == "department_id":
                    dept = self._data.get("department", "")
                    return PayloadWrapper({"department": dept}) if dept else ""
                if name == "requested_by":
                    return self._data.get("manager_name", "")
                if name == "hr_reviewer":
                    return self._data.get("hr_rep_name", "")
                if name == "approved_by":
                    return self._data.get("ceo_name", "")
                if name == "job_description_file":
                    jd = self._data.get("job_description_file")
                    return type("FileStub", (), {"name": jd})() if jd else None
                return ""
            if name in ("target_onboarding_date", "period_from", "period_to", "requested_date", "hr_reviewed_date", "approved_date"):
                if isinstance(val, str) and val.strip():
                    from datetime import datetime
                    for fmt in ("%d.%m.%y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
                        try:
                            return datetime.strptime(val.strip(), fmt).date()
                        except ValueError:
                            pass
            if isinstance(val, dict):
                return PayloadWrapper(val)
            return val

        def __getitem__(self, item):
            return getattr(self, item)

    req_obj = PayloadWrapper(payload)

    # Context dictionary passed into the template
    context = {
        "req": req_obj,
        "now": timezone.now(),
        "logo_b64": logo_b64,
        "empty_b64": empty_b64,
        "checked_b64": checked_b64,
        "chk_empty_html": chk_empty_html,
        "chk_checked_html": chk_checked_html,
    }

    html = render_to_string("recruitment/requisition/requisition_pdf_ticket.html", context)
    pdf_bytes = html_to_pdf_bytes(html)

    if output_pdf_path:
        out_file = Path(output_pdf_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "wb") as f:
            f.write(pdf_bytes)
        print(f"[SUCCESS] Official RMO Staff Requisition Form generated: {out_file.resolve()} ({len(pdf_bytes):,} bytes)")

    return pdf_bytes


def get_sample_payload() -> dict:
    """Returns a canonical sample payload conforming to RMO-HRA-QF-001 specification."""
    return {
        "requisition_code": "REQ-2026-0015",
        "position_title": "Senior Cloud Infrastructure Engineer",
        "location": "Phnom Penh Main Office",
        "function": "Engineering & Technology",
        "department": "Technical Department",
        "manager_name": "Dr. Chanheng Menh",
        "manager_position": "Chief Technology Officer",
        "employment_type": "permanent",
        "permanent_category": "budgeted",
        "target_onboarding_date": "01.12.26",
        "position_level": "Senior Level (L4)",
        "replacement_for": "",
        "replacement_reason": "",
        "contract_term": "full_time",
        "period_from": "",
        "period_to": "",
        "working_days_hours": "",
        "justification": (
            "To support our rapid expansion into multi-cloud enterprise deployments for key telecom and banking clients, "
            "we require a dedicated Senior Cloud Infrastructure Engineer. This role is critical to design, deploy, and "
            "maintain our high-availability microservices architecture, implement automated CI/CD pipelines, and ensure "
            "99.99% uptime for core enterprise services."
        ),
        "position_requirements": (
            "• Bachelor's or Master's degree in Computer Science, Software Engineering, or related technical field.\n"
            "• Minimum 5+ years of production experience in AWS/GCP and Kubernetes orchestration.\n"
            "• Strong proficiency in Terraform, Ansible, Docker, and Linux kernel administration.\n"
            "• Proven track record with PostgreSQL replication, Redis clusters, and Prometheus/Grafana monitoring.\n"
            "• Industry certifications: AWS Certified Solutions Architect (Professional) or CKA preferred.\n"
            "• Excellent cross-functional technical communication and mentoring abilities."
        ),
        "job_description_file": "JD_Senior_Cloud_Infrastructure_Engineer.docx",
        "requested_date": "14.10.26",
        "hr_rep_name": "Sin Thida",
        "hr_reviewed_date": "14.10.26",
        "ceo_name": "KHIEU Sarvorneat",
        "approved_date": "14.10.26",
        "status": "approved"
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] not in ("--help", "-h"):
        input_arg = sys.argv[1]
        out_path = sys.argv[2] if len(sys.argv) > 2 else "output_requisition_form.pdf"

        if os.path.exists(input_arg):
            with open(input_arg, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            try:
                payload = json.loads(input_arg)
            except Exception as e:
                print(f"[ERROR] Could not parse JSON input: {e}")
                sys.exit(1)
        render_requisition_pdf_from_dict(payload, out_path)
    else:
        # Default self-test with canonical sample payload
        out_path = "Staff_Requisition_Sample_RMO-HRA-QF-001.pdf"
        print(f"[INFO] Generating sample PDF using canonical payload to '{out_path}'...")
        sample_payload = get_sample_payload()
        render_requisition_pdf_from_dict(sample_payload, out_path)
