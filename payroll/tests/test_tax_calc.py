"""Tests for the Cambodia payroll tax calculation (pension + tax)."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from employee.models import Employee
from payroll.methods.tax_calc import (
    DEPENDENT_DEDUCTION,
    PENSION_MAX_CONTRIBUTION,
    PENSION_MAX_SALARY,
    calculate_pension_amount,
    calculate_pension_contribution,
    calculate_taxable_amount,
    get_dependent_count,
    get_usd_to_khr_rate,
)
from payroll.models.tax_models import PayrollSettings


class FakeQuerySet:
    """Mimics the TaxBracket queryset API used inside calculate_taxable_amount."""

    def __init__(self, rows):
        self._rows = rows
    def order_by(self, *_args):
        return self

    def exists(self):
        return True

    def values(self, *_fields):
        return list(self._rows)


class CalculatePensionContributionTests(TestCase):
    def test_below_threshold_uses_two_percent(self):
        # 1,000,000 KHR < 1,200,000 KHR -> 2%
        self.assertEqual(calculate_pension_contribution(1_000_000), 20_000.0)

    def test_at_threshold_uses_cap(self):
        # Exactly 1,200,000 KHR -> fixed 24,000 KHR (2% equals the cap here)
        self.assertEqual(calculate_pension_contribution(PENSION_MAX_SALARY), 24_000.0)

    def test_above_threshold_is_capped(self):
        self.assertEqual(calculate_pension_contribution(2_000_000), 24_000.0)
        self.assertEqual(calculate_pension_contribution(5_000_000), 24_000.0)

    def test_zero_salary_zero_pension(self):
        self.assertEqual(calculate_pension_contribution(0), 0.0)

    def test_cap_constant_consistency(self):
        self.assertEqual(PENSION_MAX_CONTRIBUTION, PENSION_MAX_SALARY * 0.02)


def _reset_rate_state(rate=None):
    """
    Reset the environment around the USD -> KH exchange rate before a test:
    clear any thread-local request (so HorillaModel.save() doesn't stamp
    created_by/modified_by with a stale user id) and reset PayrollSettings.

    Pass a rate to simulate HR having created that rate from the UI, or None
    to simulate a fresh system where HR has not created any rate yet.
    """
    from horilla.horilla_middlewares import _thread_locals

    _thread_locals.request = None
    PayrollSettings.objects.all().delete()
    if rate is not None:
        PayrollSettings.objects.create(usd_to_khr_rate=rate)


class CalculateTaxableAmountTests(TestCase):
    """
    Full-month period (Jan 2024, 31 days) so the monthly and period amounts
    are equal. Filing status is "basic_pay" so income == basic_pay (USD).
    """

    def setUp(self):
        # HR has created the exchange rate 1 USD = 4046 KH from the UI.
        _reset_rate_state(rate=4046.0)
        self.kwargs = {
            "employee": 1,
            "allowances": {"allowances": []},
            "total_allowance": 0,
            "day_dict": {},
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
        }
        self.filing = SimpleNamespace(based_on="basic_pay")
        self.contract = SimpleNamespace(filing_status=self.filing)
        self.brackets = [
            {"tax_rate": 0.0, "min_income": 0, "max_income": 1_500_000},
            {"tax_rate": 5.0, "min_income": 1_500_001, "max_income": 2_000_000},
            {"tax_rate": 10.0, "min_income": 2_000_001, "max_income": 8_500_000},
            {"tax_rate": 15.0, "min_income": 8_500_001, "max_income": 12_500_000},
            {"tax_rate": 20.0, "min_income": 12_500_001, "max_income": float("inf")},
        ]

    def _run(self, basic_pay):
        self.kwargs["basic_pay"] = basic_pay
        with patch(
            "payroll.methods.tax_calc.Contract.objects.filter",
            return_value=SimpleNamespace(first=lambda: self.contract),
        ), patch(
            "payroll.methods.tax_calc.TaxBracket.objects.filter",
            return_value=FakeQuerySet(self.brackets),
        ):
            return calculate_taxable_amount(**self.kwargs)

    def test_low_salary_no_tax(self):
        # 200 USD -> 809,200 KHR/month, pension 16,184 KHR,
        # taxable 793,016 KHR still in the 0% bracket.
        self.assertEqual(self._run(200), 0)

    def test_no_filing_status_returns_zero(self):
        self.contract.filing_status = None
        self.assertEqual(self._run(200), 0)

    def test_medium_salary_five_percent(self):
        # 400 USD -> 1,618,400 KHR/month, pension capped 24,000 KHR,
        # taxable 1,594,400 KHR -> 5% bracket:
        # tax = 1,594,400 * 0.05 - 75,000 = 4,720 KHR = 1.17 USD
        self.assertEqual(self._run(400), 1.17)

    def test_high_salary_ten_percent(self):
        # 600 USD -> 2,427,600 KHR/month, pension capped 24,000 KHR,
        # taxable 2,403,600 KHR -> 10% bracket:
        # tax = 2,403,600 * 0.10 - 175,000 = 65,360 KHR = 16.15 USD
        self.assertEqual(self._run(600), 16.15)

    def test_top_bracket_twenty_percent(self):
        # 3,100 USD -> 12,542,600 KHR/month, pension capped 24,000 KHR,
        # taxable 12,518,600 KHR -> 20% bracket:
        # tax = 12,518,600 * 0.20 - 1,225,000 = 1,278,720 KHR = 316.05 USD
        self.assertEqual(self._run(3100), 316.05)


class CalculatePensionAmountTests(TestCase):
    """
    Full-month period (Jan 2024, 31, days) unless overridden. Filing
    status is "basic_pay" so income == basic_pay (USD), like the tax tests.
    """

    def setUp(self):
        # HR has created the exchange rate 1 USD = 4046 KH from the UI.
        _reset_rate_state(rate=4046.0)
        self.kwargs = {
            "employee": 1,
            "allowances": {"allowances": []},
            "total_allowance": 0,
            "day_dict": {},
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
        }
        self.filing = SimpleNamespace(based_on="basic_pay")
        self.contract = SimpleNamespace(filing_status=self.filing)

    def _run(self, basic_pay, start_date=None, end_date=None):
        self.kwargs["basic_pay"] = basic_pay
        if start_date is not None:
            self.kwargs["start_date"] = start_date
        if end_date is not None:
            self.kwargs["end_date"] = end_date
        with patch(
            "payroll.methods.tax_calc.Contract.objects.filter",
            return_value=SimpleNamespace(first=lambda: self.contract),
        ):
            return calculate_pension_amount(**self.kwargs)

    def test_two_percent_below_threshold(self):
        # 200 USD -> 809,200 KHR/month -> 2% = 16,184 KHR -> 4.00 USD
        self.assertEqual(self._run(200), 4.0)

    def test_capped_above_threshold(self):
        # 400 USD -> 1,618,400 KHR/month -> fixed 24,000 KHR -> 5.93 USD
        self.assertEqual(self._run(400), 5.93)

    def test_zero_when_no_filing_status(self):
        self.contract.filing_status = None
        self.assertEqual(self._run(400), 0.0)

    def test_partial_period_is_scaled(self):
        # 300 USD over 15 of 31 days -> monthly 1,213,800 KHR ->
        # capped 24,000 KHR, scaled to the period: 24,000 / 31 * 15 =
        # 11,612.90 KHR -> 2.87 USD
        result = self._run(300, date(2024, 1, 1), date(2024, 1, 15))
        self.assertAlmostEqual(result, 2.87, places=2)


class FakeEmployeeQuerySet:
    """Mimics employee.models.Employee.objects.filter(...).first()."""

    def __init__(self, employee):
        self._employee = employee

    def first(self):
        return self._employee


class GetDependentCountTests(TestCase):
    """
    Cambodia dependents counted from the employee profile:
        married                  -> husband and wife both have an income, so
                                    only the children are dependents
        married_spouse_dependent -> the spouse has no income: 1 dependent for
                                    the spouse + the children
        single / divorced        -> 0
    """

    def _run(self, marital_status, children):
        employee = SimpleNamespace(marital_status=marital_status, children=children)
        with patch(
            "employee.models.Employee.objects.filter",
            return_value=FakeEmployeeQuerySet(employee),
        ):
            return get_dependent_count(employee)

    # ---- "married": husband and wife both have an income -> children only ---
    def test_married_both_working_zero_children(self):
        self.assertEqual(self._run("married", 0), 0)

    def test_married_both_working_no_children_recorded(self):
        self.assertEqual(self._run("married", None), 0)

    def test_married_both_working_one_child_is_one_dependent(self):
        # "if have only son in dependent" -> 1 dependent
        self.assertEqual(self._run("married", 1), 1)

    def test_married_both_working_with_children(self):
        self.assertEqual(self._run("married", 3), 3)

    # ---- new option: the spouse has no income -> the spouse is a dependent --
    def test_married_spouse_dependent_zero_children(self):
        # "if man/wife is in dependent" -> 1 dependent
        self.assertEqual(self._run("married_spouse_dependent", 0), 1)

    def test_married_spouse_dependent_no_children_recorded(self):
        self.assertEqual(self._run("married_spouse_dependent", None), 1)

    def test_married_spouse_dependent_one_child_is_two_dependents(self):
        # "if have man/wife with son is 2 people in dependent" -> 2 dependents
        self.assertEqual(self._run("married_spouse_dependent", 1), 2)

    def test_married_spouse_dependent_with_children(self):
        self.assertEqual(self._run("married_spouse_dependent", 3), 4)

    # ---- not married -------------------------------------------------------
    def test_single_no_dependents_even_with_children_field(self):
        self.assertEqual(self._run("single", 2), 0)

    def test_divorced_no_dependents(self):
        self.assertEqual(self._run("divorced", 1), 0)

    def test_dependent_deduction_constant(self):
        self.assertEqual(DEPENDENT_DEDUCTION, 150_000.0)


class EmployeeTaxDependentHelperTests(TestCase):
    """
    The dependent rules have a single source of truth on the Employee model
    (Employee.count_tax_dependents / get_tax_dependent_count), which is what
    the payroll tax calculation calls through get_dependent_count().
    """

    def test_static_helper_follows_marital_status_and_children(self):
        self.assertEqual(Employee.count_tax_dependents("single", 5), 0)
        self.assertEqual(Employee.count_tax_dependents("divorced", 3), 0)
        self.assertEqual(Employee.count_tax_dependents("married", 0), 0)
        self.assertEqual(Employee.count_tax_dependents("married", 2), 2)
        self.assertEqual(Employee.count_tax_dependents("married_spouse_dependent", 0), 1)
        self.assertEqual(Employee.count_tax_dependents("married_spouse_dependent", 2), 3)

    def test_instance_method_uses_the_profile_fields(self):
        employee = Employee(marital_status="married_spouse_dependent", children=2)
        self.assertEqual(employee.get_tax_dependent_count(), 3)

    def test_new_spouse_dependent_option_is_available(self):
        values = [value for value, _label in Employee.choice_marital]
        self.assertIn("married_spouse_dependent", values)
        # The three original options are kept.
        self.assertEqual(values[:2], ["single", "married"])
        self.assertIn("divorced", values)


class TaxFamilyDeductionTests(TestCase):
    """
    Tax with the family deduction applied: 150,000 KHR per dependent
    (non-working spouse + children) is subtracted from (salary - pension)
    BEFORE the tax brackets are applied.

    Dependents come from the marital status + children fields:
        "married"                  -> children only (husband and wife work)
        "married_spouse_dependent" -> the spouse without income (1) + children
    """

    def setUp(self):
        # HR has created the exchange rate 1 USD = 4046 KH from the UI.
        _reset_rate_state(rate=4046.0)
        self.kwargs = {
            "employee": 1,
            "allowances": {"allowances": []},
            "total_allowance": 0,
            "day_dict": {},
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
        }
        self.filing = SimpleNamespace(based_on="basic_pay")
        self.contract = SimpleNamespace(filing_status=self.filing)
        self.brackets = [
            {"tax_rate": 0.0, "min_income": 0, "max_income": 1_500_000},
            {"tax_rate": 5.0, "min_income": 1_500_001, "max_income": 2_000_000},
            {"tax_rate": 10.0, "min_income": 2_000_001, "max_income": 8_500_000},
            {"tax_rate": 15.0, "min_income": 8_500_001, "max_income": 12_500_000},
            {"tax_rate": 20.0, "min_income": 12_500_001, "max_income": float("inf")},
        ]

    def _run(self, basic_pay, marital_status="single", children=None):
        self.kwargs["basic_pay"] = basic_pay
        employee = SimpleNamespace(marital_status=marital_status, children=children)
        with patch(
            "payroll.methods.tax_calc.Contract.objects.filter",
            return_value=SimpleNamespace(first=lambda: self.contract),
        ), patch(
            "payroll.methods.tax_calc.TaxBracket.objects.filter",
            return_value=FakeQuerySet(self.brackets),
        ), patch(
            "employee.models.Employee.objects.filter",
            return_value=FakeEmployeeQuerySet(employee),
        ):
            return calculate_taxable_amount(**self.kwargs)

    # ---- "married": husband and wife both have an income -> children only ---
    def test_married_both_working_no_children_is_not_a_dependent(self):
        # No dependents at all -> the result equals the single employee result.
        self.assertEqual(self._run(600, "married", 0), 16.15)

    def test_married_both_working_one_child(self):
        # "if have only son in dependent" -> 1 dependent = 150,000 KHR
        # 600 USD -> 2,427,600 KHR, pension 24,000 -> 2,403,600 KHR,
        # family deduction 150,000 -> 2,253,600 KHR -> 10% bracket:
        # tax = 2,253,600 * 0.10 - 175,000 = 50,360 KHR = 12.45 USD
        self.assertEqual(self._run(600, "married", 1), 12.45)

    def test_married_both_working_two_children(self):
        # 2 dependents = 300,000 KHR:
        # 2,403,600 - 300,000 = 2,103,600 KHR -> 10% bracket:
        # tax = 2,103,600 * 0.10 - 175,000 = 35,360 KHR = 8.74 USD
        self.assertEqual(self._run(600, "married", 2), 8.74)

    # ---- new option: the spouse has no income -> 1 extra dependent ---------
    def test_spouse_dependent_no_children_one_dependent(self):
        # "if man/wife is in dependent" -> 1 dependent (the spouse), so the
        # deduction equals married + 1 child: tax 12.45 USD as well.
        self.assertEqual(self._run(600, "married_spouse_dependent", 0), 12.45)

    def test_spouse_dependent_one_child_two_dependents(self):
        # "if have man/wife with son is 2 people in dependent":
        # 2 x 150,000 = 300,000 KHR -> 2,103,600 KHR -> 10% bracket = 8.74 USD
        self.assertEqual(self._run(600, "married_spouse_dependent", 1), 8.74)

    def test_spouse_dependent_two_children_no_tax(self):
        # 400 USD -> 1,618,400 KHR, pension 24,000 -> 1,594,400 KHR,
        # family deduction 3 x 150,000 = 450,000 -> 1,144,400 KHR -> 0% bracket
        self.assertEqual(self._run(400, "married_spouse_dependent", 2), 0)

    def test_spouse_dependent_two_children_five_percent_bracket(self):
        # 600 USD -> 2,427,600 KHR, pension 24,000 -> 2,403,600 KHR,
        # family deduction 450,000 -> 1,953,600 KHR -> 5% bracket:
        # tax = 1,953,600 * 0.05 - 75,000 = 22,680 KHR = 5.61 USD
        self.assertEqual(self._run(600, "married_spouse_dependent", 2), 5.61)

    def test_family_deduction_cannot_go_negative(self):
        # 200 USD -> 809,200 KHR, pension 16,184 -> 793,016 KHR,
        # family deduction 6 x 150,000 = 900,000 -> below 0 -> tax 0
        self.assertEqual(self._run(200, "married_spouse_dependent", 5), 0)

    def test_single_employee_unchanged(self):
        # No dependents: same result as before the family deduction existed.
        self.assertEqual(self._run(600), 16.15)


class GetUsdToKhrRateTests(TestCase):
    """
    get_usd_to_khr_rate() reads ONLY the exchange rate that HR created in the
    UI (PayrollSettings.usd_to_khr_rate). There is no hard-coded fallback:
    while no rate has been created (or the stored value is invalid) it simply
    returns None.
    """

    def setUp(self):
        # Clear any thread-local request left over from prior tests so
        # HorillaModel.save() doesn't stamp created_by/modified_by with a
        # stale user id that doesn't exist in the test database.
        from horilla.horilla_middlewares import _thread_locals

        _thread_locals.request = None

        PayrollSettings.objects.all().delete()

    def test_returns_none_when_no_rate_created_yet(self):
        # No rate exists in the DB and nothing is hard-coded in the source.
        self.assertIsNone(get_usd_to_khr_rate())

    def test_db_rate_created_from_ui_is_used(self):
        PayrollSettings.objects.create(usd_to_khr_rate=4047)
        self.assertEqual(get_usd_to_khr_rate(), 4047.0)

    def test_ignores_zero_rate(self):
        PayrollSettings.objects.create(usd_to_khr_rate=0)
        self.assertIsNone(get_usd_to_khr_rate())

    def test_rate_survives_refresh_with_multiple_settings_rows(self):
        """
        Regression: an old PayrollSettings row without a rate (company NULL)
        must not hide the row that carries the rate. Before the fix, the
        unordered .first() could return the empty row, so the UI showed
        "No exchange rate created yet" right after a page refresh.
        """
        # Old empty row (as left behind by earlier saves / migrations).
        PayrollSettings.objects.create(company_id=None, usd_to_khr_rate=None)
        # The row the rate was actually saved to (per-company scope).
        from base.models import Company

        company = Company.objects.create(
            company="Test Company",
            address="Test Address",
            country="Cambodia",
            state="Phnom Penh",
            city="Phnom Penh",
            zip="12000",
        )
        PayrollSettings.objects.create(company_id=company, usd_to_khr_rate=4047.0)
        self.assertEqual(get_usd_to_khr_rate(), 4047.0)


class DynamicExchangeRateInTaxTests(TestCase):
    """
    Changing the exchange rate in the database shifts the computed salary tax:
    a higher rate means the same USD salary converts to more KHR and lands in
    the same tax bracket, producing a slightly higher tax (and vice versa).
    """

    def setUp(self):
        # Clear any thread-local request left over from prior tests so
        # HorillaModel.save() doesn't stamp created_by/modified_by with a
        # stale user id that doesn't exist in the test database.
        from horilla.horilla_middlewares import _thread_locals

        _thread_locals.request = None

        PayrollSettings.objects.all().delete()
        self.kwargs = {
            "employee": 1,
            "allowances": {"allowances": []},
            "total_allowance": 0,
            "day_dict": {},
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
        }
        self.filing = SimpleNamespace(based_on="basic_pay")
        self.contract = SimpleNamespace(filing_status=self.filing)
        self.brackets = [
            {"tax_rate": 0.0, "min_income": 0, "max_income": 1_500_000},
            {"tax_rate": 5.0, "min_income": 1_500_001, "max_income": 2_000_000},
            {"tax_rate": 10.0, "min_income": 2_000_001, "max_income": 8_500_000},
            {"tax_rate": 15.0, "min_income": 8_500_001, "max_income": 12_500_000},
            {"tax_rate": 20.0, "min_income": 12_500_001, "max_income": float("inf")},
        ]

    def _run(self, basic_pay):
        self.kwargs["basic_pay"] = basic_pay
        with patch(
            "payroll.methods.tax_calc.Contract.objects.filter",
            return_value=SimpleNamespace(first=lambda: self.contract),
        ), patch(
            "payroll.methods.tax_calc.TaxBracket.objects.filter",
            return_value=FakeQuerySet(self.brackets),
        ):
            return calculate_taxable_amount(**self.kwargs)

    def test_no_rate_created_yet_means_zero_tax(self):
        # Nothing is hard-coded: until HR creates the exchange rate from the
        # UI there is no USD -> KH conversion, so the tax is 0.
        PayrollSettings.objects.all().delete()
        self.assertEqual(self._run(1000), 0)

    def test_tax_follows_the_configured_db_rate(self):
        # 1,000 USD at 4,046 -> 10% bracket (56.15 USD tax).
        PayrollSettings.objects.create(usd_to_khr_rate=4046.0)
        self.assertEqual(self._run(1000), 56.15)

        # Same salary at 4,047 -> slightly more KHR, slightly higher tax.
        PayrollSettings.objects.all().delete()
        PayrollSettings.objects.create(usd_to_khr_rate=4047.0)
        self.assertEqual(self._run(1000), 56.17)
