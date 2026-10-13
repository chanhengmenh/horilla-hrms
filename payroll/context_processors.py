"""
context_processor.py

This module is used to register context processor`
"""

from employee.models import Employee
from payroll.models import tax_models as models
from payroll.models.models import Deduction


def default_currency(request):
    """
    This method will return the currency
    """
    settings = models.PayrollSettings.objects.first()
    if settings is None:
        try:
            settings = models.PayrollSettings()
            settings.currency_symbol = "$"
            settings.company_id = getattr(request, "selected_company_instance", None)
            settings.save()
            settings = models.PayrollSettings.objects.first()
        except Exception:
            settings = None

    symbol = getattr(settings, "currency_symbol", "$") if settings else "$"
    position = getattr(settings, "position", "postfix") if settings else "postfix"
    return {
        "currency": request.session.get("currency", symbol),
        "position": request.session.get("position", position),
    }


def host(request):
    """
    This method will return the host
    """
    protocol = "https" if request.is_secure() else "http"
    return {"host": request.get_host(), "protocol": protocol}


def get_deductions(request):
    """
    This method used to return the deduction
    """
    deductions = Deduction.objects.filter(
        only_show_under_employee=False, employer_rate__gt=0
    )
    return {"get_deductions": deductions}


def get_active_employees(request):
    """
    This method used to return the deduction
    """
    employees = Employee.objects.filter(
        is_active=True, contract_set__isnull=False, payslip__isnull=False
    ).distinct()
    return {"get_active_employees": employees}
