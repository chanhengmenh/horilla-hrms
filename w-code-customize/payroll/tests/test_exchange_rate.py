"""Tests for the exchange-rate UI flow (Payroll -> Salary Tax)."""

from django.test import TestCase
from django.urls import reverse

from horilla.testkit import make_company, make_employee, make_user
from payroll.methods.tax_calc import get_usd_to_khr_rate
from payroll.models.tax_models import PayrollSettings


class ExchangeRateViewTests(TestCase):
    """
    A payroll admin can update the USD -> KHR exchange rate from the Salary
    Tax page and every salary / pension calculation picks the new value up.
    """

    def setUp(self):
        # Clear any thread-local request left over from prior tests so
        # HorillaModel.save() doesn't stamp created_by/modified_by with a
        # stale user id that doesn't exist in the test database.
        from horilla.horilla_middlewares import _thread_locals, set_selected_company

        _thread_locals.request = None
        # Also reset the request-level selected-company ContextVar: the
        # middleware sets it during client requests and it survives between
        # tests, which would make HorillaCompanyManager filter model queries
        # by a stale (rolled-back) company and hide freshly created rows.
        set_selected_company(None)
        company = make_company("Rate Co")
        self.user = make_user("rate_admin", is_superuser=True)
        make_employee(company=company, email="rate_admin@test.horilla", user=self.user)
        self.client.force_login(self.user)
        PayrollSettings.objects.all().delete()

    def test_rate_can_be_updated_from_salary_tax_page(self):
        response = self.client.post(
            reverse("exchange-rate-view"),
            {"usd_to_khr_rate": "4047"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PayrollSettings.objects.first().usd_to_khr_rate, 4047.0)
        self.assertEqual(get_usd_to_khr_rate(), 4047.0)
        self.assertContains(response, "1 USD = 4047.00 KH")

    def test_invalid_rate_is_rejected(self):
        response = self.client.post(
            reverse("exchange-rate-view"),
            {"usd_to_khr_rate": "0"},
        )
        self.assertEqual(response.status_code, 200)
        # Nothing below or equal to zero is ever persisted: the rate simply
        # does not exist until HR creates a valid one from the UI.
        self.assertIsNone(get_usd_to_khr_rate())
        self.assertContains(response, "Create Exchange Rate")

    def test_no_rate_until_hr_creates_it(self):
        # No rate is hard-coded anywhere in the source code: until HR creates
        # one from the Salary Tax page there is no exchange rate at all.
        self.assertIsNone(get_usd_to_khr_rate())
        response = self.client.get(reverse("filing-status-view"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Exchange Rate")
        self.assertContains(response, "No exchange rate created yet")
        # No rate value (e.g. 4046 / 4047) may leak into the page or the code.
        self.assertNotContains(response, "4046")
        self.assertNotContains(response, "4047")

    def test_login_required(self):
        self.client.logout()
        response = self.client.post(
            reverse("exchange-rate-view"),
            {"usd_to_khr_rate": "4047"},
        )
        self.assertNotEqual(response.status_code, 200)