import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "horilla.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from horilla_crumbs.context_processors import breadcrumbs
from report.views.standard_reports import (
    standard_report_catalog,
    standard_report_inspector,
    standard_report_print_filters,
    standard_report_detail,
)

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    raise RuntimeError("No superuser found in database!")

factory = RequestFactory()


def make_request(path, session=None):
    req = factory.get(path)
    req.user = admin_user
    # Add session
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    if session is not None:
        req.session.update(session)
    req.session.save()
    return req


def test_breadcrumbs_scenario():
    print("\n--- Testing Breadcrumbs Navigation ---")

    # Step 1: User visits Recruitment > Staff Requisitions
    req1 = make_request("/recruitment/staff-requisitions/")
    ctx1 = breadcrumbs(req1)
    crumbs1 = [c["name"] for c in ctx1["breadcrumbs"]]
    print("Step 1 (/recruitment/staff-requisitions/):", crumbs1)
    assert "Horilla" in crumbs1[0]
    assert crumbs1[1] == "Recruitment"
    assert crumbs1[2] == "Staff Requisitions"

    # Step 2: User navigates from Recruitment to Reports > Standard Reports
    # We pass req1's session so session state persists
    req2 = make_request("/report/standard/", session=dict(req1.session))
    ctx2 = breadcrumbs(req2)
    crumbs2 = [c["name"] for c in ctx2["breadcrumbs"]]
    print("Step 2 (/report/standard/):", crumbs2)
    assert crumbs2[1] == "Reports", f"Expected 'Reports', got {crumbs2[1]}"
    assert crumbs2[2] == "Standard Reports", f"Expected 'Standard Reports', got {crumbs2[2]}"
    assert "Recruitment" not in crumbs2, f"Recruitment leaked into crumbs: {crumbs2}"
    assert "staff-requisitions" not in crumbs2, f"staff-requisitions leaked into crumbs: {crumbs2}"

    # Step 3: User opens Staff Requisition Summary from Standard Reports
    req3 = make_request("/report/standard/staff-requisition-summary/", session=dict(req2.session))
    ctx3 = breadcrumbs(req3)
    crumbs3 = [c["name"] for c in ctx3["breadcrumbs"]]
    print("Step 3 (/report/standard/staff-requisition-summary/):", crumbs3)
    assert crumbs3[1] == "Reports"
    assert crumbs3[2] == "Standard Reports"
    assert crumbs3[3] == "Staff Requisition Summary"
    assert "Recruitment" not in crumbs3

    # Step 4: Cross-module jump: user is in Recruitment and clicks direct report link
    req4_start = make_request("/recruitment/staff-requisitions/")
    breadcrumbs(req4_start)
    req4_jump = make_request("/report/standard/staff-requisition-summary/", session=dict(req4_start.session))
    ctx4 = breadcrumbs(req4_jump)
    crumbs4 = [c["name"] for c in ctx4["breadcrumbs"]]
    print("Step 4 (Jump from Recruitment to /report/standard/staff-requisition-summary/):", crumbs4)
    assert crumbs4[1] == "Reports"
    assert crumbs4[2] == "Standard Reports"
    assert crumbs4[3] == "Staff Requisition Summary"
    assert "Recruitment" not in crumbs4

    print("SUCCESS: All breadcrumbs tests passed cleanly!")


def test_standard_report_views():
    print("\n--- Testing Standard Report Views & Inspector ---")

    # 1. Catalog view: original listing preserved (no extra links or view buttons on rows)
    req_catalog = make_request("/report/standard/")
    resp_catalog = standard_report_catalog(req_catalog)
    content_cat = resp_catalog.content.decode("utf-8")
    assert resp_catalog.status_code == 200
    assert "Staff Requisition Summary" in content_cat
    assert "sr-row__title-link" not in content_cat, "Report titles must remain original text without links"
    assert "data-detail-url=" not in content_cat, "Row markup must remain in original form"
    print("Catalog view: HTTP 200, listing preserved in original form (no extra row links).")

    # 2. Inspector fragment for staff-requisition-summary: has View Report button & KPIs
    req_insp = make_request("/report/standard/staff-requisition-summary/inspector/")
    resp_insp = standard_report_inspector(req_insp, "staff-requisition-summary")
    content_insp = resp_insp.content.decode("utf-8")
    assert resp_insp.status_code == 200
    assert "View Report" in content_insp
    assert "/report/standard/staff-requisition-summary/" in content_insp
    assert "Live KPI Summary" in content_insp
    print("Inspector view (Staff Requisition): HTTP 200, has 'View Report' button and Live KPI Summary.")

    # 3. Inspector fragment for other reports: strictly original form (NO View Report button, NO KPI summary)
    req_other = make_request("/report/standard/workforce-composition/inspector/")
    resp_other = standard_report_inspector(req_other, "workforce-composition")
    content_other = resp_other.content.decode("utf-8")
    assert resp_other.status_code == 200
    assert "View Report" not in content_other, "Other reports must NOT have View Report button"
    assert "Live KPI Summary" not in content_other, "Other reports must NOT have Live KPI Summary"
    assert "Run now" in content_other
    assert "PDF · Excel" in content_other
    print("Inspector view (Other reports): HTTP 200, strictly in original form (no View Report button).")

    # 4. Detail view
    req_detail = make_request("/report/standard/staff-requisition-summary/")
    resp_detail = standard_report_detail(req_detail, "staff-requisition-summary")
    content_detail = resp_detail.content.decode("utf-8")
    assert resp_detail.status_code == 200
    assert "Staff Requisition Summary" in content_detail
    assert "ApexCharts" in content_detail or "apexcharts" in content_detail.lower()
    print("Detail view: HTTP 200, contains full dashboard with ApexCharts and KPIs.")

    print("SUCCESS: All view & inspector tests passed cleanly!")


if __name__ == "__main__":
    test_breadcrumbs_scenario()
    test_standard_report_views()
