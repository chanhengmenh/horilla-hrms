"""
recruitment/accessibility.py

"""

from recruitment.templatetags.recruitmentfilters import recruitment_manages


def add_candidate_accessibility(
    request, instance=None, user_perms=[], *args, **kwargs
) -> bool:
    """
    Candidate add accessibility
    """
    return (
        request.user.has_perm("recruitment.add_candidate")
        or request.user.employee_get in instance.stage_managers.all()
        or request.user.employee_get
        in instance.recruitment_id.recruitment_managers.all()
    )


def edit_stage_accessibility(
    request, instance=None, user_perms=[], *args, **kwargs
) -> bool:
    """
    Edit stage accessibility
    """
    return (
        request.user.has_perm("recruitment.change_stage")
        or recruitment_manages(request.user, instance.recruitment_id)
        or request.user.employee_get in instance.stage_managers.all()
    )


def delete_stage_accessibility(
    request, instance=None, user_perms=[], *args, **kwargs
) -> bool:
    """
    Delete stage accessibility
    """
    return request.user.has_perm("recruitment.delete_stage")


def is_ceo(user) -> bool:
    """
    Check if a user is the Chief Executive Officer (CEO).
    Strict Access Rule: Only the CEO is authorized to approve staff requisitions.
    """
    if not user or not user.is_authenticated:
        return False

    if user.groups.filter(name__iexact="CEO").exists():
        return True

    if user.user_permissions.filter(codename="approve_staffrequisition").exists():
        return True

    employee = getattr(user, "employee_get", None)
    if not employee:
        return False

    work_info = getattr(employee, "employee_work_info", None)
    if not work_info:
        return False

    pos_name = str(work_info.job_position_id.job_position if work_info.job_position_id else "").lower().strip()
    role_name = str(work_info.job_role_id.job_role if work_info.job_role_id else "").lower().strip()

    ceo_terms = ["chief executive officer", "ceo"]
    if pos_name in ceo_terms or any(t in pos_name.split() for t in ceo_terms):
        return True
    if role_name in ceo_terms or any(t in role_name.split() for t in ceo_terms):
        return True

    return False


def is_executive_or_hod(user) -> bool:
    """
    Check if a user is an Executive / Head of Department / CTO / Director.
    """
    if not user or not user.is_authenticated:
        return False

    if is_ceo(user):
        return True

    if user.has_perm("recruitment.request_staffrequisition"):
        return True

    if user.groups.filter(
        name__in=["Executive", "Department Head", "HOD", "C-Suite", "Board", "Director"]
    ).exists():
        return True

    employee = getattr(user, "employee_get", None)
    if not employee:
        return False

    work_info = getattr(employee, "employee_work_info", None)
    if not work_info:
        return False

    role_name = str(work_info.job_role_id.job_role if work_info.job_role_id else "").lower()
    pos_name = str(work_info.job_position_id.job_position if work_info.job_position_id else "").lower()

    executive_keywords = [
        "head",
        "director",
        "chief",
        "cto",
        "cfo",
        "coo",
        "cmo",
        "cio",
        "vice president",
        "vp",
        "general manager",
        "managing director",
        "chair",
        "founder",
    ]

    if any(kw in role_name or kw in pos_name for kw in executive_keywords):
        return True

    from employee.models import EmployeeWorkInformation

    if EmployeeWorkInformation.objects.filter(reporting_manager_id=employee).exists():
        return True

    return False


def can_audit_requisition(user) -> bool:
    """
    HR, Recruiters, and Admins can audit / review all requisitions.
    """
    if not user or not user.is_authenticated:
        return False
    if (
        user.is_superuser
        or user.has_perm("recruitment.view_recruitment")
        or user.has_perm("recruitment.audit_staffrequisition")
        or user.groups.filter(name__in=["HR", "Human Resources", "Recruiter", "Admin"]).exists()
    ):
        return True

    employee = getattr(user, "employee_get", None)
    if employee:
        work_info = getattr(employee, "employee_work_info", None)
        if work_info:
            dept_name = str(work_info.department_id.department if work_info.department_id else "").lower()
            role_name = str(work_info.job_role_id.job_role if work_info.job_role_id else "").lower()
            pos_name = str(work_info.job_position_id.job_position if work_info.job_position_id else "").lower()
            if any(
                kw in dept_name or kw in role_name or kw in pos_name
                for kw in ["human resource", "hr", "recruitment", "talent acquisition", "admin-hr"]
            ):
                return True
    return False


def can_review_requisition(user) -> bool:
    """
    HR and Admin have full access to review staff requisitions.
    """
    return can_audit_requisition(user)


def can_approve_requisition(user) -> bool:
    """
    Strict Policy: ONLY the Chief Executive Officer (CEO) has authority to approve staff requisitions.
    Neither HR nor general Administrators can approve.
    """
    return is_ceo(user)


def can_request_requisition(user) -> bool:
    """
    HR and ADMIN have full admin access on Staff Requisition to request/originate headcount,
    along with Executive Leadership, Department Heads, CTO, and CEO.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if can_audit_requisition(user):
        return True

    if is_executive_or_hod(user):
        return True

    if is_ceo(user):
        return True

    if user.has_perm("recruitment.request_staffrequisition"):
        return True

    return False


def requisition_create_accessibility(request, *args, **kwargs) -> bool:
    """
    HR, Admin, and Executives / HODs can create staff requisitions.
    """
    return can_request_requisition(request.user)


def requisition_sidebar_accessibility(
    request, submenu=None, user_perms=None, *args, **kwargs
) -> bool:
    """
    Sidebar entry visible to HR, Admin, Executives, and CEO.
    """
    return can_request_requisition(request.user) or can_audit_requisition(request.user) or is_ceo(request.user)

