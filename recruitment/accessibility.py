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


def is_executive_or_hod(user) -> bool:
    """
    Check if a user is an Executive / Head of Department / CTO / Director
    authorized to request and fill out staff requisitions.
    Excludes regular HR staff and general non-executive admins from originating requisitions.
    """
    if not user or not user.is_authenticated:
        return False

    # Check explicit permission
    if user.has_perm("recruitment.request_staffrequisition"):
        return True

    # Check designated executive groups
    if user.groups.filter(
        name__in=["Executive", "Department Head", "HOD", "C-Suite", "Board", "Director"]
    ).exists():
        return True

    employee = getattr(user, "employee_get", None)
    if not employee:
        # Bare admin or user without linked employee cannot initiate requisitions
        return False

    work_info = getattr(employee, "employee_work_info", None)
    if not work_info:
        return False

    dept_name = str(work_info.department_id.department if work_info.department_id else "").lower()
    role_name = str(work_info.job_role_id.job_role if work_info.job_role_id else "").lower()
    pos_name = str(work_info.job_position_id.job_position if work_info.job_position_id else "").lower()

    # Executive title indicators
    executive_keywords = [
        "head",
        "director",
        "chief",
        "cto",
        "ceo",
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

    is_exec_title = any(kw in role_name or kw in pos_name for kw in executive_keywords)
    if is_exec_title:
        return True

    # Pure HR / Recruitment / General Admin without executive title is strictly barred
    is_hr = any(
        kw in dept_name
        for kw in ["human resource", "hr & admin", "hr and admin", "talent acquisition", "recruitment"]
    )
    if is_hr:
        return False

    # Also allow active reporting managers (Line Managers of non-HR departments)
    from employee.models import EmployeeWorkInformation

    if EmployeeWorkInformation.objects.filter(reporting_manager_id=employee).exists():
        return True

    return False


def requisition_create_accessibility(request, *args, **kwargs) -> bool:
    """
    Only Executives / Department Heads can create / fill staff requisitions.
    """
    return is_executive_or_hod(request.user)


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

    # Also check if employee belongs to HR / Recruitment department
    employee = getattr(user, "employee_get", None)
    if employee:
        work_info = getattr(employee, "employee_work_info", None)
        if work_info:
            dept_name = str(work_info.department_id.department if work_info.department_id else "").lower()
            role_name = str(work_info.job_role_id.job_role if work_info.job_role_id else "").lower()
            pos_name = str(work_info.job_position_id.job_position if work_info.job_position_id else "").lower()
            if any(
                kw in dept_name or kw in role_name or kw in pos_name
                for kw in ["human resource", "hr", "recruitment", "talent acquisition"]
            ):
                return True
    return False


def requisition_sidebar_accessibility(
    request, submenu=None, user_perms=None, *args, **kwargs
) -> bool:
    """
    Sidebar entry visible to Executives (to request) and HR/Management (to review/audit).
    """
    return is_executive_or_hod(request.user) or can_audit_requisition(request.user)

