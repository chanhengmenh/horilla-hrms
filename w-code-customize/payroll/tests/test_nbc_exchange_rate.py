"""Tests for the NBC exchange-rate flow (Settings -> General)."""

from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from horilla.testkit import make_company, make_employee, make_user
from payroll.methods.nbc_exchange import (
    apply_exchange_rate,
    apply_nbc_rate_for_date,
    ensure_monthly_nbc_rate,
    get_nbc_month_rates,
    get_official_nbc_rate,
    get_working_day_for_date,
)
from payroll.methods.tax_calc import get_usd_to_khr_rate
from payroll.models.tax_models import NBCExchangeRate, PayrollSettings


class WorkingDayResolutionTests(TestCase):
    """The 15th is only used when it is a working day (Monday - Friday)."""

    def test_15th_on_a_tuesday_is_used_as_is(self):
        # 2026-09-15 is a Tuesday
        self.assertEqual(get_working_day_for_date(date(2026, 9, 15)), date(2026, 9, 15))

    def test_15th_on_saturday_rolls_back_to_friday(self):
        # 2026-08-15 is a Saturday -> Friday 2026-08-14
        self.assertEqual(get_working_day_for_date(date(2026, 8, 15)), date(2026, 8, 14))

    def test_15th_on_sunday_rolls_back_to_friday(self):
        # 2026-11-15 is a Sunday -> Friday 2026-11-13
        self.assertEqual(get_working_day_for_date(date(2026, 11, 15)), date(2026, 11, 13))

    def test_15th_on_public_holiday_rolls_back_to_previous_working_day(self):
        # 2026-10-15 is the Commemoration Day of King's Father (a Thursday):
        # NBC publishes no rate that day, so Wednesday the 14th is used.
        self.assertEqual(get_working_day_for_date(date(2026, 10, 15)), date(2026, 10, 14))


class ApplyExchangeRateTests(TestCase):
    """Applying a rate updates the payroll salary-tax rate automatically."""

    def setUp(self):
        from horilla.horilla_middlewares import _thread_locals, set_selected_company

        _thread_locals.request = None
        set_selected_company(None)
        PayrollSettings.objects.all().delete()
        NBCExchangeRate.objects.all().delete()

    def test_apply_updates_active_rate(self):
        apply_exchange_rate(rate=4053, effective_date=date(2026, 9, 15), source="nbc")
        self.assertEqual(get_usd_to_khr_rate(), 4053.0)
        self.assertEqual(NBCExchangeRate.objects.count(), 1)
        self.assertEqual(NBCExchangeRate.objects.first().source, "nbc")

    def test_manual_source_is_recorded(self):
        apply_exchange_rate(rate=4050, effective_date=date(2026, 9, 16), source="manual")
        self.assertEqual(get_usd_to_khr_rate(), 4050.0)
        self.assertEqual(NBCExchangeRate.objects.first().source, "manual")

    def test_invalid_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_exchange_rate(rate=0, effective_date=date(2026, 9, 15))
        self.assertIsNone(get_usd_to_khr_rate())


class NBCFetchTests(TestCase):
    """Fetching from NBC updates the rate (and never uses weekend rates)."""

    def setUp(self):
        from horilla.horilla_middlewares import _thread_locals, set_selected_company

        _thread_locals.request = None
        set_selected_company(None)
        PayrollSettings.objects.all().delete()
        NBCExchangeRate.objects.all().delete()

    def test_apply_nbc_rate_uses_working_day_rate(self):
        fake_rates = [
            (date(2026, 9, 11), 4052.0),  # Friday
            (date(2026, 9, 15), 4053.0),  # Tuesday (the 15th)
        ]
        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            return_value=fake_rates,
        ):
            record, message = apply_nbc_rate_for_date(date(2026, 9, 15))

        self.assertIsNotNone(record)
        self.assertEqual(record.rate, 4053.0)
        self.assertEqual(record.effective_date, date(2026, 9, 15))
        self.assertEqual(record.source, "nbc")
        self.assertEqual(get_usd_to_khr_rate(), 4053.0)
        self.assertIn("NBC", message)

    def test_15th_on_weekend_uses_friday_rate(self):
        # 2026-11-15 is a Sunday; the published Sunday rate must never be used.
        fake_rates = [
            (date(2026, 11, 13), 4051.0),  # Friday 13th (working day)
            (date(2026, 11, 14), 4090.0),  # Saturday (must be skipped)
            (date(2026, 11, 15), 4091.0),  # Sunday (must be skipped)
        ]
        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            return_value=fake_rates,
        ):
            record, _message = apply_nbc_rate_for_date(date(2026, 11, 15))

        self.assertEqual(record.effective_date, date(2026, 11, 13))
        self.assertEqual(record.rate, 4051.0)
        self.assertEqual(get_usd_to_khr_rate(), 4051.0)

    def test_network_failure_returns_message(self):
        import requests

        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            side_effect=requests.ConnectionError(),
        ):
            record, message = apply_nbc_rate_for_date(date(2026, 9, 15))

        self.assertIsNone(record)
        self.assertIn("Could not connect", message)


class SettingsExchangeRateViewTests(TestCase):
    """The Settings -> General exchange-rate card updates the salary tax rate."""

    def setUp(self):
        from horilla.horilla_middlewares import _thread_locals, set_selected_company

        _thread_locals.request = None
        set_selected_company(None)
        company = make_company("NBC Co")
        self.user = make_user("nbc_admin", is_superuser=True)
        make_employee(company=company, email="nbc_admin@test.horilla", user=self.user)
        self.client.force_login(self.user)
        PayrollSettings.objects.all().delete()
        NBCExchangeRate.objects.all().delete()

    def test_manual_update_from_settings_page(self):
        response = self.client.post(
            reverse("settings-exchange-rate-view"),
            {"usd_to_khr_rate": "4050"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_usd_to_khr_rate(), 4050.0)
        self.assertEqual(NBCExchangeRate.objects.first().source, "manual")

    def test_invalid_update_is_rejected(self):
        response = self.client.post(
            reverse("settings-exchange-rate-view"),
            {"usd_to_khr_rate": "0"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(get_usd_to_khr_rate())

    def test_rate_can_be_set_for_a_specific_day_from_the_calendar(self):
        response = self.client.post(
            reverse("settings-exchange-rate-view"),
            {
                "usd_to_khr_rate": "4050",
                "effective_date": "2026-09-10",
                "month": "2026-09",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        record = NBCExchangeRate.objects.get()
        self.assertEqual(record.effective_date, date(2026, 9, 10))
        self.assertEqual(record.source, "manual")
        self.assertEqual(get_usd_to_khr_rate(), 4050.0)
        # The card stays on the month of the day that was edited.
        self.assertIn('value="2026-09"', response.content.decode())

    def test_future_effective_date_is_rejected(self):
        future = date.today() + timedelta(days=10)
        response = self.client.post(
            reverse("settings-exchange-rate-view"),
            {"usd_to_khr_rate": "4050", "effective_date": future.isoformat()},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(get_usd_to_khr_rate())
        self.assertEqual(NBCExchangeRate.objects.count(), 0)

    def test_malformed_effective_date_is_rejected(self):
        response = self.client.post(
            reverse("settings-exchange-rate-view"),
            {"usd_to_khr_rate": "4050", "effective_date": "10/09/2026"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(get_usd_to_khr_rate())
        self.assertEqual(NBCExchangeRate.objects.count(), 0)

    def test_fetch_from_nbc_button(self):
        fake_rates = [(date(2026, 9, 15), 4053.0)]
        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            return_value=fake_rates,
        ):
            response = self.client.post(
                reverse("settings-exchange-rate-fetch-nbc"),
                HTTP_HX_REQUEST="true",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_usd_to_khr_rate(), 4053.0)
        self.assertEqual(NBCExchangeRate.objects.first().source, "nbc")

    def test_login_required(self):
        self.client.logout()
        response = self.client.post(
            reverse("settings-exchange-rate-view"),
            {"usd_to_khr_rate": "4050"},
            HTTP_HX_REQUEST="true",
        )
        self.assertNotEqual(response.status_code, 200)


class ExchangeRateCalendarTests(TestCase):
    """Month grid and month-navigation form of the Exchange Rate Calendar."""

    def setUp(self):
        from horilla.horilla_middlewares import _thread_locals, set_selected_company

        _thread_locals.request = None
        set_selected_company(None)
        company = make_company("Rate Calendar Co")
        self.user = make_user("rate_calendar_admin", is_superuser=True)
        make_employee(
            company=company, email="rate_calendar_admin@test.horilla", user=self.user
        )
        self.client.force_login(self.user)
        PayrollSettings.objects.all().delete()
        NBCExchangeRate.objects.all().delete()

    def _get_calendar(self, **params):
        return self.client.get(
            reverse("settings-exchange-rate-calendar"),
            params,
            HTTP_HX_REQUEST="true",
        )

    def test_calendar_renders_a_valid_month_grid(self):
        response = self._get_calendar(month="2026-09")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("nbcExchangeRateCalendar", content)
        # The header used to print today's date (09/25/26), not the month.
        self.assertIn("September 2026", content)
        # Every row must be opened AND closed. The old template emitted <tr>
        # and </tr> on the same loop index, which mangled the whole grid.
        # ("<tr" also matches the <tr class="..."> of the header row.)
        self.assertEqual(content.count("</tr>"), content.count("<tr"))
        # September 2026 starts on a Tuesday: 5 Sunday-first weeks = 35 cells.
        self.assertEqual(content.count("<td"), 35)

    def test_calendar_highlights_the_resolved_working_day(self):
        weekday_15th = self._get_calendar(month="2026-09").content.decode()
        # 2026-09-15 is a Tuesday, so the 15th itself is the working day.
        self.assertIn('rounded-full bg-green-100 text-green-700 font-medium">15<', weekday_15th)
        self.assertNotIn(
            'rounded-full bg-orange-100 text-orange-700 font-medium">15<', weekday_15th
        )

        weekend_15th = self._get_calendar(month="2026-08").content.decode()
        # 2026-08-15 is a Saturday -> Friday 2026-08-14 is used instead.
        self.assertIn(
            'rounded-full bg-orange-100 text-orange-700 font-medium">15<', weekend_15th
        )
        self.assertIn('rounded-full bg-blue-100 text-blue-700 font-medium">14<', weekend_15th)

    def test_calendar_marks_weekends_in_red(self):
        content = self._get_calendar(month="2026-09").content.decode()

        # 2026-09-05 is a Saturday and 2026-09-06 a Sunday -> red numbers.
        self.assertIn('leading-7 font-medium text-danger">5<', content)
        self.assertIn('leading-7 font-medium text-danger">6<', content)
        # Monday 2026-09-07 is a normal working day -> no colour.
        self.assertIn('leading-7">7<', content)
        # The weekend column headers are red as well (Sun first, Sat last).
        self.assertIn('text-center text-danger">Sun<', content)
        self.assertIn('text-center text-danger">Sat<', content)

    def test_calendar_marks_and_names_public_holidays_in_red(self):
        content = self._get_calendar(month="2026-10").content.decode()

        # Pchum Ben Festival, 10 - 12 October 2026: the weekend days 10/11
        # and the working day 12 must all be red and carry the name.
        # NOTE: only the class tail is asserted — when a holiday day is also
        # "today" the number is wrapped in the primary circle, which reorders
        # the classes (bg-primary-100 ... text-danger).
        for day in (10, 11, 12):
            self.assertIn(f'text-danger">{day}<', content)
        self.assertIn("Pchum Ben Festival", content)
        # The legend below the grid lists every holiday of the month,
        # including Thursday 15 October (Commemoration Day of King's Father).
        self.assertIn("Public holidays this month", content)
        self.assertIn("15 Oct", content)

    def test_calendar_shows_holidays_configured_in_settings(self):
        from base.models import Holidays

        Holidays.objects.create(
            name="Company Founders Day",
            start_date=date(2026, 10, 5),
            end_date=date(2026, 10, 5),
        )

        content = self._get_calendar(month="2026-10").content.decode()

        self.assertIn("Company Founders Day", content)
        # 2026-10-05 is a Monday: red because it is a holiday, not a weekend.
        self.assertIn('leading-7 font-medium text-danger">5<', content)

    def test_calendar_shows_the_rate_stored_for_a_day(self):
        apply_exchange_rate(rate=4053, effective_date=date(2026, 9, 15), source="nbc")

        content = self._get_calendar(month="2026-09").content.decode()

        self.assertIn("4053.00", content)
        # The day whose rate is applied to payroll is marked in green.
        self.assertIn(
            "text-[0.625rem] leading-3 font-medium text-success", content
        )

    def test_calendar_legend_explains_the_colours(self):
        """The legend swatches must match what the grid really prints.

        Regression guard for the legend row: the "applied rate" swatch used to
        print the word "Green" glued to its label - "Green= rate currently
        applied to the payroll calculation" - and the weekend swatch was a
        filled red circle while the grid renders those day numbers as plain red
        text.
        """

        content = self._get_calendar(month="2026-09").content.decode()

        self.assertIn("15th - working day", content)
        self.assertIn("Saturday, Sunday or public holiday", content)
        self.assertIn("Rate applied to the payroll calculation", content)
        # The old legend glued the label to the "=" sign.
        self.assertNotIn("Green=", content)

    def test_calendar_navigates_to_the_requested_month(self):
        content = self._get_calendar(month="2026-08").content.decode()

        # The month picker shows the browsed month ...
        self.assertIn('value="2026-08"', content)
        # ... and the arrows point at the adjacent months.
        self.assertIn('"month": "2026-07"', content)
        self.assertIn('"month": "2026-09"', content)

    def test_bad_month_falls_back_to_the_current_month(self):
        content = self._get_calendar(month="not-a-month").content.decode()

        self.assertIn(f'value="{date.today():%Y-%m}"', content)

    def test_calendar_is_htmx_and_login_only(self):
        response = self.client.get(reverse("settings-exchange-rate-calendar"))
        self.assertEqual(response.status_code, 405)

        self.client.logout()
        response = self._get_calendar(month="2026-09")
        self.assertNotEqual(response.status_code, 200)


class SystemPreferencesPageTests(TestCase):
    """The exchange-rate card must really show up on Settings -> General.

    Regression guard for the template-shadowing bug: Horilla's template loaders
    are (horilla_dbtemplate, filesystem(horilla_theme/templates), app_directories,
    filesystem(templates)) - see horilla/settings/base.py. Because the theme
    filesystem loader runs *before* the app-directories loader, the page that is
    actually served comes from
    horilla_theme/templates/base/settings/system_preferences.html and NOT from
    base/templates/base/settings/system_preferences.html. Adding the include to
    only one of the two copies is invisible in the UI, so both are asserted here.
    """

    def setUp(self):
        from horilla.horilla_middlewares import _thread_locals, set_selected_company

        _thread_locals.request = None
        set_selected_company(None)
        company = make_company("NBC Page Co")
        self.user = make_user("nbc_page_admin", is_superuser=True)
        make_employee(
            company=company, email="nbc_page_admin@test.horilla", user=self.user
        )
        self.client.force_login(self.user)
        PayrollSettings.objects.all().delete()
        NBCExchangeRate.objects.all().delete()

    def test_system_preferences_page_renders_exchange_rate_card(self):
        apply_exchange_rate(rate=4053, effective_date=date(2026, 9, 15), source="nbc")

        response = self.client.get(reverse("system-preferences-view"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("nbcExchangeRateContainer", content)
        self.assertIn("Exchange Rate", content)
        self.assertTrue(
            "4053.00" in content or "4,053.00" in content,
            "the active USD -> KHR rate should be shown on the card",
        )
        # The manual update form and the NBC fetch button must be usable.
        self.assertIn(reverse("settings-exchange-rate-view"), content)
        self.assertIn(reverse("settings-exchange-rate-fetch-nbc"), content)

    def test_page_renders_card_even_without_a_rate_yet(self):
        response = self.client.get(reverse("system-preferences-view"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("nbcExchangeRateContainer", content)
        self.assertIn("Create Exchange Rate", content)

    def test_no_raw_template_comment_is_rendered(self):
        """A multi-line {# ... #} is NOT a Django comment - it leaks as text.

        Regression guard for the card's explanatory comment: it has to be a
        single-line {# ... #} or a comment block, otherwise Django prints the
        raw "{# Exchange Rate ... #}" line right above the card on the page.
        """

        response = self.client.get(reverse("system-preferences-view"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("{#", content)
        self.assertNotIn(
            "payroll/templates/payroll/settings/nbc_exchange_rate.html", content
        )

    def test_no_markup_comment_leaks_into_the_card(self):
        """A "// -- ... -- //" marker is not a template comment - it leaks.

        Regression guard for the "Fetch from NBC" separator of the card: it was
        written with JavaScript comment markers, so the browser printed
        "// -- Fetch from NBC button -- //" in the middle of the card.
        """

        response = self.client.get(reverse("system-preferences-view"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("// -- Fetch", content)
        self.assertNotIn("Fetch from NBC button", content)

    def test_every_copy_of_the_settings_template_includes_the_card(self):
        """Both copies must include the card - one is shadowed by the loaders."""

        from django.conf import settings

        base_dir = Path(settings.BASE_DIR)
        copies = [
            base_dir
            / "horilla_theme"
            / "templates"
            / "base"
            / "settings"
            / "system_preferences.html",
            base_dir
            / "base"
            / "templates"
            / "base"
            / "settings"
            / "system_preferences.html",
        ]
        found = 0
        for path in copies:
            if not path.exists():
                continue
            found += 1
            with self.subTest(template=str(path)):
                self.assertIn(
                    "payroll/settings/nbc_exchange_rate.html",
                    path.read_text(encoding="utf-8"),
                )
        self.assertEqual(found, 2, "expected both settings templates to exist")

    def test_page_does_not_query_nbc_on_load(self):
        """The NBC panel loads with its own request, never with the page.

        The month list comes from an external service, so the System
        Preferences page must stay fast and must keep working when NBC is
        unreachable - the card only renders a placeholder that HTMX fills in.
        """

        with mock.patch("payroll.methods.nbc_exchange._fetch_nbc_rates") as fetch:
            response = self.client.get(reverse("system-preferences-view"))

        self.assertEqual(response.status_code, 200)
        fetch.assert_not_called()
        self.assertIn(
            reverse("settings-exchange-rate-nbc-panel"),
            response.content.decode(),
        )


class NBCCacheTests(TestCase):
    """The NBC month list is cached; the settings page is not charged twice."""

    def setUp(self):
        cache.clear()

    def test_month_rates_are_cached(self):
        fake_rates = [(date(2026, 9, 15), 4053.0)]
        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            return_value=fake_rates,
        ) as fetch:
            first = get_nbc_month_rates(date(2026, 9, 1))
            second = get_nbc_month_rates(date(2026, 9, 10))

        self.assertEqual(fetch.call_count, 1)
        self.assertTrue(first["available"])
        self.assertFalse(first["from_cache"])
        self.assertTrue(second["from_cache"])
        self.assertEqual(second["rates"], fake_rates)

    def test_refresh_bypasses_the_cache(self):
        fake_rates = [(date(2026, 9, 15), 4053.0)]
        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            return_value=fake_rates,
        ) as fetch:
            get_nbc_month_rates(date(2026, 9, 1))
            refreshed = get_nbc_month_rates(date(2026, 9, 1), refresh=True)

        self.assertEqual(fetch.call_count, 2)
        self.assertFalse(refreshed["from_cache"])

    def test_network_failure_is_reported(self):
        import requests

        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            side_effect=requests.ConnectionError(),
        ):
            data = get_nbc_month_rates(date(2026, 9, 1))

        self.assertFalse(data["available"])
        self.assertEqual(data["rates"], [])
        self.assertIn("Could not connect", data["message"])

    def test_network_failure_falls_back_to_the_cached_list(self):
        import requests

        fake_rates = [(date(2026, 9, 15), 4053.0)]
        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            return_value=fake_rates,
        ):
            get_nbc_month_rates(date(2026, 9, 1))

        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            side_effect=requests.ConnectionError(),
        ):
            data = get_nbc_month_rates(date(2026, 9, 1), refresh=True)

        self.assertFalse(data["available"])
        self.assertTrue(data["from_cache"])
        self.assertEqual(data["rates"], fake_rates)


class OfficialNBCRateTests(TestCase):
    """The official rate is the NBC rate of the 15th - working days only."""

    def setUp(self):
        cache.clear()

    def test_official_rate_is_the_rate_of_the_15th(self):
        fake_rates = [
            (date(2026, 9, 14), 4052.0),
            (date(2026, 9, 15), 4053.0),
        ]
        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            return_value=fake_rates,
        ):
            official = get_official_nbc_rate(date(2026, 9, 1))

        self.assertEqual(official["requested_date"], date(2026, 9, 15))
        self.assertEqual(official["published_date"], date(2026, 9, 15))
        self.assertEqual(official["rate"], 4053.0)

    def test_sunday_15th_uses_the_friday_rate(self):
        # 2026-11-15 is a Sunday -> Friday 2026-11-13.
        fake_rates = [
            (date(2026, 11, 12), 4050.0),
            (date(2026, 11, 13), 4051.0),
            (date(2026, 11, 14), 4090.0),  # Saturday - never used
            (date(2026, 11, 15), 4091.0),  # Sunday - never used
        ]
        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            return_value=fake_rates,
        ):
            official = get_official_nbc_rate(date(2026, 11, 1))

        self.assertEqual(official["effective_date"], date(2026, 11, 13))
        self.assertEqual(official["published_date"], date(2026, 11, 13))
        self.assertEqual(official["rate"], 4051.0)

    def test_not_published_yet_returns_no_rate(self):
        # Only a rate of the 1st exists, so the 15th has no official rate yet.
        fake_rates = [(date(2026, 9, 1), 4050.0)]
        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            return_value=fake_rates,
        ):
            official = get_official_nbc_rate(date(2026, 9, 1))

        self.assertIsNone(official["rate"])
        self.assertTrue(official["available"])
        # The month list is still shown, only the official rate is pending.
        self.assertEqual(official["rates"], fake_rates)


class SettingsExchangeRatePanelTests(TestCase):
    """The NBC part of the Exchange Rate card (Settings -> General)."""

    def setUp(self):
        from horilla.horilla_middlewares import _thread_locals, set_selected_company

        cache.clear()
        _thread_locals.request = None
        set_selected_company(None)
        company = make_company("NBC Panel Co")
        self.user = make_user("nbc_panel_admin", is_superuser=True)
        make_employee(
            company=company, email="nbc_panel_admin@test.horilla", user=self.user
        )
        self.client.force_login(self.user)
        PayrollSettings.objects.all().delete()
        NBCExchangeRate.objects.all().delete()

    def _get_panel(self, **params):
        fake_rates = [
            (date(2026, 9, 14), 4052.0),
            (date(2026, 9, 15), 4053.0),
        ]
        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            return_value=fake_rates,
        ):
            return self.client.get(
                reverse("settings-exchange-rate-nbc-panel"),
                params,
                HTTP_HX_REQUEST="true",
            )

    def test_panel_shows_the_official_rate_of_the_15th(self):
        response = self._get_panel(month="2026-09")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("nbcExchangeRatePanel", content)
        self.assertIn("Official NBC rate of the 15th", content)
        self.assertIn("4053.00", content)
        # Every NBC rate of the month is listed, not only the 15th.
        self.assertIn("4052.00", content)
        self.assertIn("Not applied yet", content)

    def test_panel_marks_the_official_rate_as_applied(self):
        apply_exchange_rate(rate=4053, effective_date=date(2026, 9, 15), source="nbc")

        response = self._get_panel(month="2026-09")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Applied to payroll", response.content.decode())

    def test_bad_month_value_falls_back_to_the_current_month(self):
        response = self._get_panel(month="not-a-month")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f'value="{date.today():%Y-%m}"',
            response.content.decode(),
        )

    def test_panel_reports_an_unreachable_nbc(self):
        import requests

        with mock.patch(
            "payroll.methods.nbc_exchange._fetch_nbc_rates",
            side_effect=requests.ConnectionError(),
        ):
            response = self.client.get(
                reverse("settings-exchange-rate-nbc-panel"),
                {"month": "2026-09"},
                HTTP_HX_REQUEST="true",
            )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Could not connect", content)
        self.assertIn("No NBC rate is available for this month.", content)

    def test_panel_is_htmx_and_login_only(self):
        response = self.client.get(reverse("settings-exchange-rate-nbc-panel"))
        self.assertEqual(response.status_code, 405)

        self.client.logout()
        response = self.client.get(
            reverse("settings-exchange-rate-nbc-panel"), HTTP_HX_REQUEST="true"
        )
        self.assertNotEqual(response.status_code, 200)


class AutoFetchToggleTests(TestCase):
    """
    Manual mode (default): the USD -> KHR exchange rate is input manually and
    the automatic monthly NBC fetch never overwrites it, unless HR switches
    the "Automatic monthly NBC fetch" toggle ON (Settings -> General).
    """

    def setUp(self):
        from horilla.horilla_middlewares import _thread_locals, set_selected_company

        _thread_locals.request = None
        set_selected_company(None)
        company = make_company("Toggle Co")
        self.user = make_user("toggle_admin", is_superuser=True)
        make_employee(
            company=company, email="toggle_admin@test.horilla", user=self.user
        )
        self.client.force_login(self.user)
        PayrollSettings.objects.all().delete()
        NBCExchangeRate.objects.all().delete()

    def test_ensure_monthly_rate_is_a_noop_in_manual_mode(self):
        # No settings row at all -> manual mode (default).
        with mock.patch(
            "payroll.methods.nbc_exchange.apply_nbc_rate_for_date"
        ) as apply_mock:
            record, reason = ensure_monthly_nbc_rate(date(2026, 9, 15))
        self.assertIsNone(record)
        self.assertIn("disabled", reason)
        apply_mock.assert_not_called()

    def test_ensure_monthly_rate_is_a_noop_when_toggle_is_off(self):
        # A settings row exists (HR created the rate) but the toggle is off.
        PayrollSettings.objects.create(usd_to_khr_rate=4050)
        with mock.patch(
            "payroll.methods.nbc_exchange.apply_nbc_rate_for_date"
        ) as apply_mock:
            record, reason = ensure_monthly_nbc_rate(date(2026, 9, 15))
        self.assertIsNone(record)
        self.assertIn("disabled", reason)
        apply_mock.assert_not_called()
        # The manually entered rate is untouched.
        self.assertEqual(get_usd_to_khr_rate(), 4050.0)

    def test_scheduler_does_not_overwrite_manual_rate_by_default(self):
        # HR entered a rate manually on the 5th; the scheduler fires on the
        # 15th and must leave the rate alone (manual mode, no network call).
        apply_exchange_rate(rate=4050, effective_date=date(2026, 9, 5), source="manual")
        record, reason = ensure_monthly_nbc_rate(date(2026, 9, 15))
        self.assertIsNone(record)
        self.assertIn("disabled", reason)
        self.assertEqual(get_usd_to_khr_rate(), 4050.0)
        self.assertEqual(NBCExchangeRate.objects.count(), 1)

    def test_ensure_monthly_rate_applies_when_toggle_is_on(self):
        PayrollSettings.objects.create(usd_to_khr_rate=4050, auto_fetch_nbc_rate=True)
        fake_record = mock.Mock()
        with mock.patch(
            "payroll.methods.nbc_exchange.apply_nbc_rate_for_date",
            return_value=(fake_record, "applied"),
        ) as apply_mock:
            record, reason = ensure_monthly_nbc_rate(date(2026, 9, 15))
        apply_mock.assert_called_once()
        self.assertEqual(record, fake_record)

    def test_toggle_endpoint_switches_auto_fetch_on_and_off(self):
        url = reverse("settings-exchange-rate-auto-fetch-toggle")
        # Turn ON (a checked oh-switch posts its value).
        response = self.client.post(
            url, {"auto_fetch_nbc_rate": "on"}, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 200)
        row = PayrollSettings._base_manager.order_by("id").first()
        self.assertIsNotNone(row)
        self.assertTrue(row.auto_fetch_nbc_rate)
        # Turn OFF (an unchecked checkbox posts nothing -> flip).
        response = self.client.post(url, {}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertFalse(row.auto_fetch_nbc_rate)

    def test_card_defaults_to_manual_mode_text(self):
        response = self.client.get(reverse("system-preferences-view"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Manual mode", content)
        self.assertIn(
            reverse("settings-exchange-rate-auto-fetch-toggle"),
            content,
        )
        # The schedule block must NOT be advertised while in manual mode.
        self.assertNotIn("Automatic NBC fetch scheduled for", content)

    def test_toggle_view_requires_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("settings-exchange-rate-auto-fetch-toggle"),
            {"auto_fetch_nbc_rate": "on"},
            HTTP_HX_REQUEST="true",
        )
        self.assertNotEqual(response.status_code, 200)


