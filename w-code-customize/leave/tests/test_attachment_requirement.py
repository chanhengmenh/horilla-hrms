"""Tests for the day-based attachment requirement on LeaveRequest.clean().

Rule: when a leave type has ``require_attachment == "yes"`` the attachment
is only mandatory for requests of 2 days or more. Requests of 1.5 days or
less (half-day / single-day) must pass without any attachment.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import TestCase


class LeaveRequestAttachmentRequirementTests(TestCase):
    def setUp(self):
        from horilla.horilla_middlewares import _thread_locals
        from horilla.testkit import make_company, make_employee, make_user
        from leave.models import AvailableLeave, LeaveType

        # Fixtures are created without a request in context, then a real
        # superuser request is installed so clean() skips the past-date and
        # restricted-leave gates (we only exercise the attachment gate).
        _thread_locals.request = None
        self.addCleanup(setattr, _thread_locals, "request", None)

        company = make_company("Attachment Co")
        self.employee = make_employee(
            company=company, email="attachment@test.horilla"
        )
        self.leave_type = LeaveType.objects.create(
            name="Attachment Required Leave",
            total_days=30,
            require_attachment="yes",
        )
        AvailableLeave.objects.create(
            employee_id=self.employee,
            leave_type_id=self.leave_type,
            available_days=30,
            carryforward_days=0,
            total_leave_days=30,
        )

        superuser = make_user("attachment_su", is_superuser=True)
        _thread_locals.request = SimpleNamespace(user=superuser, GET={})

    def _make_request(
        self,
        start_offset,
        end_offset,
        start_breakdown="full_day",
        end_breakdown="full_day",
        attachment=None,
    ):
        from leave.models import LeaveRequest

        today = date.today()
        req = LeaveRequest(
            employee_id=self.employee,
            leave_type_id=self.leave_type,
            start_date=today + timedelta(days=start_offset),
            end_date=today + timedelta(days=end_offset),
            start_date_breakdown=start_breakdown,
            end_date_breakdown=end_breakdown,
            description="attachment requirement test",
        )
        if attachment:
            req.attachment = attachment
        return req

    def test_single_day_without_attachment_allowed(self):
        req = self._make_request(1, 1)
        # Should not raise even though the leave type requires attachment.
        req.clean()

    def test_one_and_half_days_without_attachment_allowed(self):
        # Two calendar days but only 1.5 leave days (half-day on the last day).
        req = self._make_request(1, 2, "full_day", "first_half")
        req.clean()

    def test_two_days_without_attachment_rejected(self):
        req = self._make_request(1, 2)
        with self.assertRaises(ValidationError) as ctx:
            req.clean()
        self.assertIn("attachment", str(ctx.exception).lower())

    def test_two_days_with_attachment_allowed(self):
        req = self._make_request(1, 2, attachment="medical-proof.pdf")
        req.clean()

    def test_two_and_half_days_without_attachment_rejected(self):
        req = self._make_request(1, 3, "full_day", "first_half")
        with self.assertRaises(ValidationError) as ctx:
            req.clean()
        self.assertIn("attachment", str(ctx.exception).lower())
