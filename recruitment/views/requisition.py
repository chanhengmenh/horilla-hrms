"""
recruitment/views/requisition.py

Views for Staff Requisition Form.
Strictly governed by RBAC: only Executives, Department Heads, CTO, and Directors
can originate and fill requisitions. HR and Admins audit and review.
"""

import base64
import os
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from base.methods import html_to_pdf_bytes
from base.models import Company, Department
from employee.models import Employee
from recruitment.accessibility import can_audit_requisition, is_executive_or_hod
from recruitment.forms import StaffRequisitionForm
from recruitment.models import StaffRequisition


def staff_requisition_list(request):
    """
    Overview list of all staff requisitions.
    Executives see their department's requisitions; HR and Admins can audit all.
    """
    user = request.user
    if not (is_executive_or_hod(user) or can_audit_requisition(user)):
        raise PermissionDenied(_("You do not have permission to view staff requisitions."))

    employee = getattr(user, "employee_get", None)
    is_exec = is_executive_or_hod(user)
    is_audit = can_audit_requisition(user)

    queryset = StaffRequisition.objects.select_related(
        "department_id", "job_position_id", "requested_by", "company_id"
    ).filter(is_active=True)

    # Scoping: if executive without general HR audit rights, filter to their requested requisitions or department
    if is_exec and not is_audit:
        if employee:
            work_info = getattr(employee, "employee_work_info", None)
            user_dept = work_info.department_id if work_info else None
            if user_dept:
                queryset = queryset.filter(department_id=user_dept)
            else:
                queryset = queryset.filter(requested_by=employee)

    # Status filter
    status_filter = request.GET.get("status")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    # Department filter
    dept_filter = request.GET.get("department_id")
    if dept_filter:
        queryset = queryset.filter(department_id_id=dept_filter)

    # Search filter (multi-token substring match: supports partial tokens like 'J', 'Ja', 'special', etc.)
    search_q = request.GET.get("search")
    if search_q:
        search_q = search_q.strip()
        terms = [t.strip() for t in search_q.split() if t.strip()]
        for term in terms:
            queryset = queryset.filter(
                Q(position_title__icontains=term)
                | Q(requisition_code__icontains=term)
                | Q(job_position_id__job_position__icontains=term)
                | Q(department_id__department__icontains=term)
                | Q(location__icontains=term)
                | Q(function__icontains=term)
                | Q(requested_by__employee_first_name__icontains=term)
                | Q(requested_by__employee_last_name__icontains=term)
            )

    departments = Department.objects.filter(is_active=True)

    context = {
        "requisitions": queryset.order_by("-id"),
        "is_executive": is_exec,
        "is_auditor": is_audit,
        "status_filter": status_filter,
        "departments": departments,
        "total_count": queryset.count(),
    }
    return render(request, "recruitment/requisition/requisition_list.html", context)


def staff_requisition_create(request):
    """
    Requisition Entry Form.
    RBAC ENFORCEMENT: Only Executives / Department Heads / CTO can fill this out.
    HR staff and general non-executive admins are blocked.
    """
    user = request.user
    if not is_executive_or_hod(user):
        messages.error(
            request,
            _(
                "Access Denied (RBAC): Staff Requisitions can only be requested by Executive Leadership, "
                "Department Heads, or the CTO. HR and general administrative accounts cannot originate headcount requests."
            ),
        )
        return redirect("staff-requisition-view")

    employee = getattr(user, "employee_get", None)
    if not employee:
        messages.error(
            request,
            _("Cannot create requisition: your user account is not linked to an active Employee profile."),
        )
        return redirect("staff-requisition-view")

    work_info = getattr(employee, "employee_work_info", None)
    manager_dept = work_info.department_id if work_info else None
    manager_company = work_info.company_id if work_info else None
    manager_pos_name = ""
    if work_info:
        if work_info.job_position_id:
            manager_pos_name = work_info.job_position_id.job_position
        elif work_info.job_role_id:
            manager_pos_name = work_info.job_role_id.job_role

    manager_email = employee.email or user.email or ""

    if request.method == "POST":
        form = StaffRequisitionForm(request.POST, request.FILES)
        if form.is_valid():
            req_instance = form.save(commit=False)
            req_instance.requested_by = employee
            req_instance.manager_position = manager_pos_name or _("Head of Department")
            req_instance.manager_email = manager_email
            if manager_company and not req_instance.company_id:
                req_instance.company_id = manager_company
            req_instance.status = "submitted"
            req_instance.requested_date = timezone.now().date()
            if not req_instance.position_requirements and req_instance.job_description_file:
                from recruitment.methods import extract_text_from_jd_file
                extracted = extract_text_from_jd_file(req_instance.job_description_file)
                if extracted:
                    req_instance.position_requirements = extracted
            req_instance.save()

            messages.success(
                request,
                _(
                    f"Staff Requisition {req_instance.requisition_code} successfully submitted. "
                    "You may now download the official PDF ticket for approval sign-offs."
                ),
            )
            return redirect("staff-requisition-detail", pk=req_instance.pk)
        else:
            messages.error(
                request,
                _("Please correct the errors in the requisition form below."),
            )
    else:
        initial_data = {
            "department_id": manager_dept.id if manager_dept else None,
            "company_id": manager_company.id if manager_company else None,
            "location": getattr(work_info, "location", "Phnom Penh HQ") or "Phnom Penh HQ",
            "function": getattr(manager_dept, "department", "Operations") if manager_dept else "Operations",
            "employment_type": "permanent",
            "permanent_category": "budgeted",
            "headcount": 1,
        }
        form = StaffRequisitionForm(initial=initial_data)

    context = {
        "form": form,
        "manager_name": str(employee),
        "manager_position": manager_pos_name,
        "manager_email": manager_email,
        "manager_dept": manager_dept,
    }
    return render(request, "recruitment/requisition/requisition_form.html", context)


def staff_requisition_detail(request, pk):
    """
    Detailed view of a staff requisition ticket.
    """
    requisition = get_object_or_404(
        StaffRequisition.objects.select_related(
            "department_id", "job_position_id", "requested_by", "company_id", "hr_reviewer", "approved_by"
        ),
        pk=pk,
    )
    user = request.user
    is_exec = is_executive_or_hod(user)
    is_audit = can_audit_requisition(user)

    context = {
        "req": requisition,
        "is_executive": is_exec,
        "is_auditor": is_audit,
    }
    return render(request, "recruitment/requisition/requisition_detail.html", context)


def staff_requisition_pdf(request, pk):
    """
    Generates and downloads the individual PDF ticket matching
    the official Staff Requisition Form standard.
    """
    requisition = get_object_or_404(
        StaffRequisition.objects.select_related(
            "department_id", "job_position_id", "requested_by", "company_id", "hr_reviewer", "approved_by"
        ),
        pk=pk,
    )

    company = requisition.company_id or Company.objects.filter(hq=True).first() or Company.objects.first()

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

    context = {
        "req": requisition,
        "company": company,
        "now": timezone.now(),
        "logo_b64": logo_b64,
        "empty_b64": empty_b64,
        "checked_b64": checked_b64,
        "chk_empty_html": chk_empty_html,
        "chk_checked_html": chk_checked_html,
    }

    html = render_to_string("recruitment/requisition/requisition_pdf_ticket.html", context)
    pdf_bytes = html_to_pdf_bytes(html)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"Staff_Requisition_{requisition.requisition_code or requisition.pk}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def staff_requisition_status_update(request, pk):
    """
    Update status: HR review or CEO approval.
    """
    if request.method != "POST":
        return redirect("staff-requisition-detail", pk=pk)

    requisition = get_object_or_404(StaffRequisition, pk=pk)
    action = request.POST.get("action")
    user = request.user
    employee = getattr(user, "employee_get", None)

    if action == "hr_review" and can_audit_requisition(user):
        requisition.status = "reviewed_hr"
        requisition.hr_reviewer = employee
        requisition.hr_reviewed_date = timezone.now().date()
        requisition.hr_remarks = request.POST.get("remarks", "")
        requisition.save()
        messages.success(request, _(f"Requisition {requisition.requisition_code} marked as Reviewed by HR."))

    elif action == "ceo_approve" and is_executive_or_hod(user):
        requisition.status = "approved"
        requisition.approved_by = employee
        requisition.approved_date = timezone.now().date()
        requisition.approval_remarks = request.POST.get("remarks", "")
        requisition.save()
        messages.success(request, _(f"Requisition {requisition.requisition_code} successfully Approved."))

    elif action == "reject" and (can_audit_requisition(user) or is_executive_or_hod(user)):
        requisition.status = "rejected"
        requisition.approval_remarks = request.POST.get("remarks", "")
        requisition.save()
        messages.warning(request, _(f"Requisition {requisition.requisition_code} has been Rejected."))

    return redirect("staff-requisition-detail", pk=pk)


def staff_requisition_extract_jd(request):
    """
    AJAX endpoint: extracts plain text on-the-fly from an uploaded Job Description
    document (.docx, .pdf, .txt) so the requester can preview and auto-populate
    the Position Requirements field without manually typing.
    """
    if request.method != "POST":
        return JsonResponse({"error": _("POST required")}, status=405)

    if not is_executive_or_hod(request.user):
        return JsonResponse({"error": _("Permission denied")}, status=403)

    uploaded_file = request.FILES.get("job_description_file")
    if not uploaded_file:
        return JsonResponse({"error": _("No file provided")}, status=400)

    from recruitment.methods import extract_text_from_jd_file

    try:
        extracted = extract_text_from_jd_file(uploaded_file, uploaded_file.name)
        if not extracted:
            return JsonResponse(
                {
                    "success": False,
                    "error": _(
                        "Could not extract text from document. Please ensure it is a valid .docx, .pdf, or text file."
                    ),
                },
                status=422,
            )

        return JsonResponse(
            {
                "success": True,
                "filename": uploaded_file.name,
                "text": extracted,
                "char_count": len(extracted),
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=500)

