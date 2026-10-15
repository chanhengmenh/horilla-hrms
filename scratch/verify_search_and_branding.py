import os
import sys

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from recruitment.models import StaffRequisition
from django.template.loader import render_to_string

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.first()

client = Client()
client.force_login(admin_user)

def test_search_scenarios():
    print("--- TESTING SEARCH QUERY SCENARIOS ---")
    scenarios = [
        ("J", ["Java Developer", "Java Specialist", "Java Junior", "Java Senior"], []),
        ("Ja", ["Java Developer", "Java Specialist", "Java Junior", "Java Senior"], []),
        ("special", ["Java Specialist"], ["Java Developer", "Java Junior", "Java Senior"]),
        ("java special", ["Java Specialist"], ["System Specialist", "Java Developer", "Java Junior", "Java Senior"]),
    ]

    for query, expected_present, expected_absent in scenarios:
        response = client.get(f"/recruitment/staff-requisitions/?search={query}")
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}"
        content = response.content.decode("utf-8")

        for role in expected_present:
            assert role in content, f"[FAILED] Query '{query}': expected '{role}' to be in response!"
        for role in expected_absent:
            assert role not in content, f"[FAILED] Query '{query}': expected '{role}' NOT to be in response!"

        print(f">> [PASS] Query '{query}' correctly filtered results:")
        print(f"         Present: {expected_present}")
        if expected_absent:
            print(f"         Excluded: {expected_absent}")

def test_no_rmo_branding():
    print("\n--- TESTING ZERO OCCURRENCES OF 'RMO-HRA-QF-001' ---")
    sample_req = StaffRequisition.objects.filter(position_title="Java Specialist").first()
    assert sample_req is not None

    # 1. Requisition List
    resp_list = client.get("/recruitment/staff-requisitions/")
    assert resp_list.status_code == 200
    assert "RMO-HRA-QF-001" not in resp_list.content.decode("utf-8"), "[FAILED] 'RMO-HRA-QF-001' found in list view!"
    print(">> [PASS] Requisition List view: 0 occurrences of 'RMO-HRA-QF-001'")

    # 2. Requisition Detail
    resp_det = client.get(f"/recruitment/staff-requisition-detail/{sample_req.id}/")
    assert resp_det.status_code == 200
    assert "RMO-HRA-QF-001" not in resp_det.content.decode("utf-8"), "[FAILED] 'RMO-HRA-QF-001' found in detail view!"
    print(">> [PASS] Requisition Detail view: 0 occurrences of 'RMO-HRA-QF-001'")

    # 3. PDF Ticket Template render
    html_rendered = render_to_string(
        "recruitment/requisition/requisition_pdf_ticket.html",
        {"req": sample_req}
    )
    assert "RMO-HRA-QF-001" not in html_rendered, "[FAILED] 'RMO-HRA-QF-001' found in PDF ticket HTML!"
    print(">> [PASS] PDF Ticket Template: 0 occurrences of 'RMO-HRA-QF-001'")

    # 4. Form Template
    resp_form = client.get("/recruitment/staff-requisition-create/")
    assert resp_form.status_code in (200, 302)
    if resp_form.status_code == 200:
        assert "RMO-HRA-QF-001" not in resp_form.content.decode("utf-8"), "[FAILED] 'RMO-HRA-QF-001' found in form HTML!"
        print(">> [PASS] Requisition Form template: 0 occurrences of 'RMO-HRA-QF-001'")

if __name__ == "__main__":
    test_search_scenarios()
    test_no_rmo_branding()
    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
