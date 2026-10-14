"""
generate_system_specialist_pdf.py

Populates and renders the official RMO Staff Requisition Form (RMO-HRA-QF-001)
using data extracted from prompts/Job Description-System Specialist.docx.
"""

import os
import sys
from render_requisition_from_payload import render_requisition_pdf_from_dict
import pymupdf

payload = {
    "requisition_code": "REQ-2026-0013",
    "position_title": "System Specialist",
    "location": "RMO Technology Co., Ltd Main Office",
    "function": "Technical Operations & Infrastructure",
    "department": "Technical Department",
    "manager_name": "Sophea Chan",
    "manager_position": "Hybrid IT Manager",
    "employment_type": "permanent",
    "permanent_category": "budgeted",
    "target_onboarding_date": "15.11.26",
    "position_level": "Specialist",
    "replacement_for": "",
    "replacement_reason": "",
    "contract_term": "full_time",
    "period_from": "",
    "period_to": "",
    "working_days_hours": "",
    "justification": (
        "Install & Configuration Server & Storage, Support Service operation.\n"
        "Due to increasing operational workload and expanding enterprise infrastructure deployments, "
        "the Technical Department requires an additional dedicated System Specialist to handle server "
        "installations, storage configurations, virtualization administration, and provide ongoing Level 1/2 "
        "service support to maintain SLA commitments."
    ),
    "position_requirements": (
        "Roles & Responsibilities:\n"
        "• Installing, configuring, managing and troubleshooting Server and Storage (Virtualized and Hardware).\n"
        "• Systems administration and monitoring infrastructure.\n"
        "• Participate in the design of information and operational support systems.\n"
        "• Evaluate and apply necessary operating system security patches, hotfixes, service packs and hardware updates.\n"
        "• Provide Level 1 support, and escalate to Level 2 when needed.\n\n"
        "Job Requirements:\n"
        "• Bachelor's degree or 4th year student in Computer Science or related IT discipline.\n"
        "• Basic knowledge of server hardware and networking.\n"
        "• Experience working with VMware vSphere, vCenter.\n"
        "• Understanding of basic Active Directory and DNS concepts with Windows Server 2016/2022 operating systems.\n"
        "• Experience in installing, configuring and troubleshooting UNIX / Linux based environments.\n"
        "• Good team player, willing to share knowledge with the team, good written and verbal communication skills.\n"
        "• Ability to work reliably under pressure."
    ),
    "job_description_file": "Job Description-System Specialist.docx",
    "requested_date": "14.10.26",
    "hr_rep_name": "Sin Thida",
    "hr_reviewed_date": "14.10.26",
    "ceo_name": "KHIEU Sarvorneat",
    "approved_date": "14.10.26",
    "status": "approved",
}

output_pdf = "Staff_Requisition_System_Specialist_RMO-HRA-QF-001.pdf"
pdf_bytes = render_requisition_pdf_from_dict(payload, output_pdf)

# Audit with pymupdf
doc = pymupdf.open(output_pdf)
print(f"Generated PDF: {output_pdf}")
print(f"Total Pages: {len(doc)}")
print(f"Filesize: {len(pdf_bytes):,} bytes")
for idx, page in enumerate(doc):
    print(f"Page {idx+1} character count: {len(page.get_text())}")
