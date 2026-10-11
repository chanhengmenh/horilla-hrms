"""Tests for the assign-leave-type Excel import and its error report.

``leave.views.generate_error_report`` builds a workbook on the fly and serves
it through a dynamically registered URL.  The code that created ``data_frame``
and ``response`` had been dropped, so every import containing at least one bad
row raised ``NameError``.  ``horilla.decorators.login_required`` swallowed that
exception into a 404 page, which meant HR never saw the "Download Error File"
button whenever the uploaded sheet had errors.
"""

from io import BytesIO

import pandas as pd
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from horilla.testkit import make_company, make_employee, make_user
from leave import urls as leave_urls
from leave.views import generate_error_report


def error_report_template():
    """The error columns exactly as ``assign_leave_type_import`` declares them."""
    return {
        "Employee Badge ID": [],
        "Leave Type": [],
        "Badge ID Error": [],
        "Leave Type Error": [],
        "Available Days": [],
        "Carry Forward Days": [],
        "Assigned Date Error": [],
        "Other Errors": [],
    }


class DynamicUrlCleanupMixin:
    """Keep the globally registered error-sheet routes inside each test."""

    def setUp(self):
        super().setUp()
        self._pattern_count = len(leave_urls.urlpatterns)

    def tearDown(self):
        # Dynamic routes live on the module-level urlpatterns list, so drop the
        # ones this test added before the next test starts.
        for pattern in leave_urls.urlpatterns[self._pattern_count :]:
            if pattern.name in settings.DYNAMIC_URL_PATTERNS:
                settings.DYNAMIC_URL_PATTERNS.remove(pattern.name)
        del leave_urls.urlpatterns[self._pattern_count :]
        super().tearDown()


class GenerateErrorReportTests(DynamicUrlCleanupMixin, TestCase):
    """The generator must hand back a downloadable workbook, never raise."""

    def test_report_is_served_as_a_real_xlsx(self):
        path_info = generate_error_report(
            [
                {
                    "Employee Badge ID": "NO-SUCH-BADGE",
                    "Badge ID Error": "This badge id does not exist.",
                }
            ],
            error_report_template(),
            "AssignLeaveError.xlsx",
        )

        # The caller feeds this straight into the template's download href.
        self.assertTrue(path_info.startswith("leave/error-sheet-"))

        route = leave_urls.urlpatterns[self._pattern_count]
        self.assertEqual(route.name, path_info.removeprefix("leave/"))

        response = route.callback(request=None)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/ms-excel")
        self.assertIn("AssignLeaveError.xlsx", response["Content-Disposition"])
        # An xlsx file is a zip container: a missing response would be empty.
        self.assertTrue(response.content.startswith(b"PK"))

    def test_downloading_the_report_deregisters_the_route(self):
        """The download is one-shot: its dynamic route must not leak."""
        path_info = generate_error_report(
            [{"Employee Badge ID": "NO-SUCH-BADGE", "Badge ID Error": "nope"}],
            error_report_template(),
            "AssignLeaveError.xlsx",
        )
        route = leave_urls.urlpatterns[self._pattern_count]
        self.assertEqual(route.name, path_info.removeprefix("leave/"))
        self.assertIn(route.name, settings.DYNAMIC_URL_PATTERNS)

        route.callback(request=None)

        # While ``path_info`` carried the "leave/" prefix, remove_dynamic_url
        # matched nothing and both the route and its tracking entry survived.
        self.assertNotIn(route.name, settings.DYNAMIC_URL_PATTERNS)
        self.assertNotIn(route, leave_urls.urlpatterns)

    def test_report_keeps_columns_with_data_and_drops_empty_ones(self):
        generate_error_report(
            [{"Employee Badge ID": "NO-SUCH-BADGE", "Badge ID Error": "nope"}],
            error_report_template(),
            "AssignLeaveError.xlsx",
        )
        response = leave_urls.urlpatterns[self._pattern_count].callback(request=None)
        report = pd.read_excel(BytesIO(response.content))

        self.assertEqual(list(report.columns), ["Employee Badge ID", "Badge ID Error"])
        self.assertEqual(report.loc[0, "Employee Badge ID"], "NO-SUCH-BADGE")
        self.assertEqual(report.loc[0, "Badge ID Error"], "nope")

    def test_report_can_be_generated_twice_in_a_row(self):
        """A second import must still work (no leftover empty columns)."""
        for _unused in range(2):
            path_info = generate_error_report(
                [{"Employee Badge ID": "NO-SUCH-BADGE", "Badge ID Error": "nope"}],
                error_report_template(),
                "AssignLeaveError.xlsx",
            )
            self.assertTrue(path_info.startswith("leave/error-sheet-"))


class AssignLeaveImportViewTests(DynamicUrlCleanupMixin, TestCase):
    """End-to-end: a bad row must still offer the error-report download."""

    def setUp(self):
        from horilla.horilla_middlewares import _thread_locals, set_selected_company

        # Drop request state left behind by earlier tests; a stale value makes
        # HorillaCompanyManager filter by a company that no longer exists.
        _thread_locals.request = None
        set_selected_company(None)
        super().setUp()

        company = make_company("Assign Co")
        self.user = make_user("assign_hr", is_superuser=True)
        make_employee(company=company, email="assign_hr@test.horilla", user=self.user)
        self.client.force_login(self.user)

    @staticmethod
    def _workbook(rows):
        buffer = BytesIO()
        pd.DataFrame(rows).to_excel(buffer, index=False)
        buffer.seek(0)
        buffer.name = "assign_leave.xlsx"
        return buffer

    def test_bad_badge_row_returns_the_download_link(self):
        upload = self._workbook(
            [{"Employee Badge ID": "NO-SUCH-BADGE", "Leave Type": "Casual"}]
        )
        response = self.client.post(
            reverse("assign-leave-type-info-import"),
            {"assign_leave_type_import": upload},
            headers={"HX-Request": "true"},
        )

        # A NameError would have been turned into a 404 page by login_required.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Download Error File")
        self.assertContains(response, "leave/error-sheet-")
