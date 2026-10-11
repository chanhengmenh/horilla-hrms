"""The attendance import error reports are served through one-shot URL routes.

``handle_attendance_errors`` and ``handle_activity_import_error`` both append a
fresh route to ``attendance.urls.urlpatterns`` for every failed import and rely
on ``remove_dynamic_url`` to drop it again once the file has been downloaded.
They handed that helper a name prefixed with ``attendance/``, which never
matched the registered route name, so both the route and its
``settings.DYNAMIC_URL_PATTERNS`` entry leaked for the lifetime of the process.
"""

from django.conf import settings
from django.test import SimpleTestCase

from attendance import urls as attendance_urls
from attendance.views.handle_attendance_errors import handle_attendance_errors
from attendance.views.views import handle_activity_import_error


class DynamicUrlCleanupMixin:
    """Keep the globally registered error-sheet routes inside each test."""

    def setUp(self):
        super().setUp()
        self._pattern_count = len(attendance_urls.urlpatterns)

    def tearDown(self):
        # Dynamic routes live on the module-level urlpatterns list, so drop the
        # ones this test added before the next test starts.
        for pattern in attendance_urls.urlpatterns[self._pattern_count :]:
            if pattern.name in settings.DYNAMIC_URL_PATTERNS:
                settings.DYNAMIC_URL_PATTERNS.remove(pattern.name)
        del attendance_urls.urlpatterns[self._pattern_count :]
        super().tearDown()


class AttendanceErrorSheetRouteTests(DynamicUrlCleanupMixin, SimpleTestCase):
    """Downloading the error file must deregister its own route."""

    def _assert_route_is_one_shot(self, path_info):
        route = attendance_urls.urlpatterns[self._pattern_count]

        # import_popup.html builds the href as "/" + path_info, so the returned
        # value keeps the "attendance/" prefix while the closure gets the bare
        # registered name that remove_dynamic_url() matches on.
        self.assertEqual(path_info, f"attendance/{route.name}")
        self.assertIn(route.name, settings.DYNAMIC_URL_PATTERNS)

        response = route.callback(request=None)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/ms-excel")
        self.assertIn("ImportError.xlsx", response["Content-Disposition"])
        # An xlsx file is a zip container: a missing response would be empty.
        self.assertTrue(response.content.startswith(b"PK"))

        self.assertNotIn(route.name, settings.DYNAMIC_URL_PATTERNS)
        self.assertNotIn(route, attendance_urls.urlpatterns)

    def test_attendance_import_error_sheet_is_one_shot(self):
        path_info = handle_attendance_errors(
            [
                {
                    "Badge ID": "NO-SUCH-BADGE",
                    "Badge ID Error": "This badge id does not exist.",
                }
            ]
        )
        self._assert_route_is_one_shot(path_info)

    def test_activity_import_error_sheet_is_one_shot(self):
        path_info = handle_activity_import_error(
            [
                {
                    "Badge ID": "NO-SUCH-BADGE",
                    "Error": "This badge id does not exist.",
                }
            ]
        )
        self._assert_route_is_one_shot(path_info)
