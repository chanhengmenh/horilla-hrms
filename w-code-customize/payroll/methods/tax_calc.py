"""
Module: payroll.tax_calc

This module contains a function for calculating the taxable amount for an employee
based on their contract details and income information.
"""

import calendar
import logging

from payroll.methods.payslip_calc import (
    calculate_gross_pay,
    calculate_taxable_gross_pay,
)
from payroll.models.models import Contract
from payroll.models.tax_models import TaxBracket

logger = logging.getLogger(__name__)

# ============================================================
# CAMBODIA CONFIGURATION
# ============================================================
# Exchange rate used to convert the salary (entered in USD) into
# Cambodian Riel (KH) before applying the Cambodia tax brackets,
# and to convert the resulting tax amount back into USD.
#
# IMPORTANT: the exchange rate is NEVER hard-coded in the source code.
# It is created ONCE by HR from the UI:
#
#     Payroll -> Salary Tax -> "Create Exchange Rate"  (input in KH)
#
# and stored in the database (PayrollSettings.usd_to_khr_rate). Every
# salary / pension / tax calculation automatically reads the rate that
# was entered in the UI. While no rate has been created yet, the USD ->
# KH conversion is skipped (tax / pension = 0) and a warning is logged.

# Cambodia NSSF employee pension contribution (in KHR), which is deducted
# from the monthly salary BEFORE salary tax is calculated:
#   monthly salary  < 1,200,000 KHR  ->  2% of the monthly salary
#   monthly salary >= 1,200,000 KHR  ->  fixed 24,000 KHR (capped)
PENSION_RATE = 0.02  # 2%
PENSION_MAX_SALARY = 1_200_000.0  # KHR
PENSION_MAX_CONTRIBUTION = 24_000.0  # KHR

# Cambodia family deduction: the monthly taxable salary is ALSO reduced by a
# fixed amount per dependent BEFORE the tax brackets are applied. The number of
# dependents is derived from the marital status + children recorded by HR on
# the employee profile (Employee.count_tax_dependents):
#   - marital_status == "married" (both husband and wife have an income)
#         -> the spouse is NOT a dependent, only the children are counted
#   - marital_status == "married_spouse_dependent"
#     ("Married (Spouse is Dependent)": the spouse has no income)
#         -> the spouse counts as 1 dependent + the children
#   - marital_status single / divorced
#         -> no dependents
# NOTE: current Cambodian law allows 250,000 KHR per dependent — change this
# constant if the company applies the official rate instead.
DEPENDENT_DEDUCTION = 150_000.0  # KHR per dependent (spouse / child)
# ============================================================

def get_usd_to_khr_rate():
    """
    Return the USD -> KH exchange rate that HR created in the UI
    (Payroll -> Salary Tax -> Create Exchange Rate).

    The rate lives ONLY in the database (PayrollSettings.usd_to_khr_rate).
    There is NO hard-coded fallback in the source code. Until HR creates
    the rate, this returns None and every USD-based Cambodia tax / pension
    calculation returns 0.

    Returns:
        float | None: The active exchange rate (1 USD = ? KH), or None
        while no rate has been created from the UI yet.
    """
    from payroll.models.tax_models import PayrollSettings

    # NOTE: PayrollSettings uses HorillaCompanyManager, which filters by the
    # company selected in the request AND includes rows with company_id NULL.
    # That can leave several rows in the queryset (one per company scope), so
    # a plain .first() is unordered and can return an old row that has no
    # rate — which made the UI look like the rate "cleared" after a refresh.
    # Always pick the first row that actually carries a rate, in a stable
    # order. Fall back to the unfiltered manager so the rate saved from the
    # UI is still honoured when a calculation runs without a request scope
    # (e.g. background payslip generation).
    settings = (
        PayrollSettings.objects.filter(usd_to_khr_rate__isnull=False)
        .exclude(usd_to_khr_rate__lte=0)
        .order_by("id")
        .first()
    )
    if settings is None:
        settings = (
            PayrollSettings._base_manager.filter(usd_to_khr_rate__isnull=False)
            .exclude(usd_to_khr_rate__lte=0)
            .order_by("id")
            .first()
        )
    rate = getattr(settings, "usd_to_khr_rate", None)
    if rate and float(rate) > 0:
        return float(rate)
    return None


def calculate_pension_contribution(monthly_income_khr):
    """
    Return the Cambodia NSSF employee pension contribution (in KHR) for the
    given full-month equivalent salary (in KHR).

    The contribution is deducted from the salary BEFORE salary tax is applied:
        monthly salary  < 1,200,000 KHR  ->  2% of the monthly salary
        monthly salary >= 1,200,000 KHR  ->  fixed 24,000 KHR

    Args:
        monthly_income_khr (float): Full-month equivalent salary in KHR.

    Returns:
        float: The employee pension contribution in KHR.
    """
    if monthly_income_khr >= PENSION_MAX_SALARY:
        return PENSION_MAX_CONTRIBUTION
    return monthly_income_khr * PENSION_RATE

def get_dependent_count(employee):
    """
    Return the number of Cambodia tax dependents for the employee.

    The rules live on the Employee model (Employee.count_tax_dependents) and
    use the fields HR fills in on the employee profile:

        marital_status == "married"                  -> both husband and wife
                                                        have an income, so the
                                                        spouse is NOT a
                                                        dependent; only the
                                                        children are counted
        marital_status == "married_spouse_dependent" -> the non-working spouse
                                                        (1) + the children
        single / divorced                            -> 0

    Examples:
        married, 0 children                          -> 0
        married, 1 child                             -> 1
        married_spouse_dependent, 0 children         -> 1
        married_spouse_dependent, 1 child            -> 2

    Args:
        employee: Employee instance or Employee primary key. When only the id
            is given, the employee record is loaded from the database.

    Returns:
        int: number of dependents (0 when the employee cannot be resolved or
        is single/divorced).
    """
    from employee.models import Employee

    if not isinstance(employee, Employee):
        employee = Employee.objects.filter(id=employee).first()
        if employee is None:
            return 0

    return Employee.count_tax_dependents(
        getattr(employee, "marital_status", None),
        getattr(employee, "children", None),
    )

def get_income_for_period(**kwargs):
    """
    Resolve the income base (in USD) for the period plus the period/months info.

    The income base follows the filing status "based on" setting (basic pay,
    gross pay or taxable gross pay). Salaries are entered in USD, so the
    returned income amount is in USD.

    Args:
        Same kwargs as calculate_taxable_amount().

    Returns:
        tuple (income_usd, num_days, days_in_month) or None when the active
        contract has no filing status.
    """
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]
    basic_pay = kwargs["basic_pay"]

    contract = Contract.objects.filter(
        employee_id=employee, contract_status="active"
    ).first()
    filing = contract.filing_status
    if not filing:
        return None

    num_days = (end_date - start_date).days + 1

    # Income base for the period ("based on" gross / taxable gross / basic pay).
    # IMPORTANT: this amount is in USD (salaries are entered in USD).
    calculation_functions = {
        "taxable_gross_pay": calculate_taxable_gross_pay,
        "gross_pay": calculate_gross_pay,
    }

    based = filing.based_on
    if based in calculation_functions:
        calculation_function = calculation_functions[based]
        income = calculation_function(**kwargs)
        income = float(income[based])
    else:
        income = float(basic_pay)

    days_in_month = calendar.monthrange(end_date.year, end_date.month)[1]
    return income, num_days, days_in_month, filing

def calculate_pension_amount(**kwargs):
    """
    Return the Cambodia NSSF employee pension contribution for the period, in USD.

    Uses the exact same income base and period scaling as
    calculate_taxable_amount(), so the amount shown on the payslip matches the
    pension that was subtracted from the monthly salary before tax:

        monthly salary  < 1,200,000 KHR  ->  2% of the salary
        monthly salary >= 1,200,000 KHR  ->  fixed 24,000 KHR

    The contribution is computed on the full-month equivalent salary (KHR),
    scaled down to the actual payslip period, and converted back to USD (the
    currency of the payslip).

    Args:
        Same kwargs as calculate_taxable_amount().

    Returns:
        float: The pension contribution for the specified period (in USD).
    """
    period_info = get_income_for_period(**kwargs)
    if period_info is None:
        return 0.0

    income, num_days, days_in_month, _filing = period_info

    # USD -> KH exchange rate created by HR in the UI
    # (Payroll -> Salary Tax -> Create Exchange Rate).
    usd_to_khr_rate = get_usd_to_khr_rate()
    if not usd_to_khr_rate:
        logger.warning(
            "No USD -> KH exchange rate has been created yet "
            "(Payroll -> Salary Tax -> Create Exchange Rate). "
            "Pension contribution is calculated as 0."
        )
        return 0.0

    # ---- Convert USD income to KHR ----
    income_khr = income * usd_to_khr_rate

    # Cambodia tax (and pension) applies on a MONTHLY basis, so convert the
    # period income to a full-month equivalent salary (in KHR).
    monthly_income_khr = round(income_khr / num_days * days_in_month, 2)

    monthly_pension_khr = calculate_pension_contribution(monthly_income_khr)

    # Scale the monthly pension down to the actual payslip period and convert
    # it back from KHR to USD.
    period_pension_khr = monthly_pension_khr / days_in_month * num_days
    period_pension_usd = period_pension_khr / usd_to_khr_rate
    return round(period_pension_usd, 2)

def calculate_taxable_amount(**kwargs):
    """
    Calculate the tax amount for a given employee within a specific period.

    CUSTOMISED FOR CAMBODIA - Salary is entered in USD, but the Cambodia
    monthly tax-slab deduction is applied in Cambodian Riel (KHR):

        Monthly Taxable Salary        Tax Rate     Deduction
        0 - 1,500,000 KHR                  0%            0
        1,500,001 - 2,000,000 KHR          5%       75,000
        2,000,001 - 8,500,000 KHR         10%      175,000
        8,500,001 - 12,500,000 KHR        15%      600,000
        Over 12,500,000 KHR               20%    1,225,000

    Cambodia formula:  Tax (KHR) = (monthly taxable salary in KHR x rate) - deduction

    BEFORE tax is applied, the Cambodia NSSF employee pension contribution is
    deducted from the monthly salary, so the tax slabs are applied on the
    net-of-pension salary:

        Monthly Salary               Pension Contribution
        < 1,200,000 KHR               2% of the salary
        >= 1,200,000 KHR              fixed 24,000 KHR

    AFTER the pension contribution, the monthly taxable salary is also reduced
    by a family deduction of 150,000 KHR per dependent (spouse for married
    employees + number of children) BEFORE the tax slabs are applied.

    The salary amount is converted USD -> KHR for the bracket lookup, and the
    resulting tax is converted back KHR -> USD, so the function always returns
    the tax amount in USD (the currency of the payslip).

    Args:
        employee (int): The ID of the employee.
        start_date (datetime.date): The start date of the period.
        end_date (datetime.date): The end date of the period.
        allowances (int): The number of allowances claimed by the employee.
        total_allowance (float): The total allowance amount.
        basic_pay (float): The basic pay amount.
        day_dict (dict): A dictionary containing specific day-related information.

    Returns:
        float: The tax amount for the specified period (in USD).
    """
    period_info = get_income_for_period(**kwargs)
    if period_info is None:
        return 0

    income, num_days, days_in_month, filing = period_info

    # USD -> KH exchange rate created by HR in the UI
    # (Payroll -> Salary Tax -> Create Exchange Rate).
    usd_to_khr_rate = get_usd_to_khr_rate()
    if not usd_to_khr_rate:
        logger.warning(
            "No USD -> KH exchange rate has been created yet "
            "(Payroll -> Salary Tax -> Create Exchange Rate). "
            "Salary tax is calculated as 0."
        )
        return 0

    # ---- Convert USD income to KHR ----
    # USD -> KHR:  income (USD) x rate = income (KHR)
    income_khr = income * usd_to_khr_rate

    # Cambodia tax applies on a MONTHLY basis, so convert the period income
    # to a full-month equivalent salary (in KHR).
    monthly_income_khr = income_khr / num_days * days_in_month
    monthly_income_khr = round(monthly_income_khr, 2)

    # ---- Cambodia NSSF employee pension (deducted from salary BEFORE tax) ----
    # The contribution is based on the full-month equivalent salary:
    #   monthly salary  < 1,200,000 KHR  ->  2% of the salary
    #   monthly salary >= 1,200,000 KHR  ->  fixed 24,000 KHR
    pension_contribution_khr = calculate_pension_contribution(monthly_income_khr)

    # Tax base = total salary - pension contribution
    taxable_monthly_income_khr = monthly_income_khr - pension_contribution_khr

    # ---- Cambodia family deduction (spouse / children) ----
    # AFTER the pension contribution, the monthly taxable salary is reduced by
    # 150,000 KHR per dependent (1 for the spouse when married, plus the
    # number of children recorded on the employee profile) BEFORE the tax
    # brackets are applied:
    #   tax base = (salary - pension) - (dependents x 150,000 KHR)
    dependent_count = get_dependent_count(kwargs["employee"])
    family_deduction_khr = dependent_count * DEPENDENT_DEDUCTION
    taxable_monthly_income_khr = taxable_monthly_income_khr - family_deduction_khr

    # The tax base can never be negative (a large family deduction on a small
    # salary simply means no tax for that month).
    taxable_monthly_income_khr = max(taxable_monthly_income_khr, 0)
    taxable_monthly_income_khr = round(taxable_monthly_income_khr, 2)

    # Load the tax brackets that were created in the UI under this filing
    # status (amounts are in KHR), ordered from lowest to highest income.
    tax_brackets = TaxBracket.objects.filter(filing_status_id=filing).order_by(
        "min_income"
    )
    if not tax_brackets.exists():
        return 0

    # Cambodia flat deduction amounts per tax rate (in KHR). These are fixed by
    # Cambodia law and applied in code (they are not entered in the UI):
    #   rate %  ->  deduction (KHR)
    RATE_DEDUCTION_MAP = {
        0: 0,
        5: 75_000,
        10: 175_000,
        15: 600_000,
        20: 1_225_000,
    }

    # Cambodia formula:  Tax (KHR) = (monthly taxable salary x rate) - deduction
    # Only one bracket applies to the salary (the one whose range it falls in),
    # so find the matching bracket and apply its rate and deduction to the whole
    # monthly income (already reduced by the pension contribution).
    monthly_tax_khr = 0
    for item in tax_brackets.values("tax_rate", "min_income", "max_income"):
        min_income = item["min_income"]
        max_income = item["max_income"]
        # A blank max income is stored as math.inf (the top bracket).
        if min_income <= taxable_monthly_income_khr <= max_income:
            rate = item["tax_rate"]
            deduction = RATE_DEDUCTION_MAP.get(round(rate), 0)
            monthly_tax_khr = taxable_monthly_income_khr * (rate / 100) - deduction
            break

    monthly_tax_khr = max(monthly_tax_khr, 0)

    # Scale the monthly tax (KHR) down to the actual payslip period
    period_tax_khr = monthly_tax_khr / days_in_month * num_days

    # ---- Convert the tax result back from KHR to USD ----
    tax_for_period_usd = period_tax_khr / usd_to_khr_rate
    return round(tax_for_period_usd, 2)

