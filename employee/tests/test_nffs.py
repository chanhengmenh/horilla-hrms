"""NFFS name + NFFS ID number coverage.

The Add Employee flow must demand both NFFS values, edits of existing
employees must keep them optional, and the values must surface in the
employee excel export columns, the list view columns, the quick-import
fields, the employee filter form and the employee report pivot.
"""

import json

from django.test import TestCase
from django.urls import reverse

from employee.cbv.employees import EmployeesList
from employee.filters import EmployeeFilter
from employee.forms import excel_columns
from employee.models import Employee
from horilla.testkit import CompanyFilterTestMixin, make_company, make_employee, make_user


def personal_payload(**overrides):
    """Minimal valid EmployeeForm payload; override per test."""
    data = {
        "employee_first_name": "Nora",
        "employee_last_name": "Ffson",
        "email": "nora.ffs@test.horilla",
        "phone": "0123456789",
        "badge_id": "NFFS-001",
        "gender": "female",
    }
    data.update(overrides)
    return data


class NffsCreateTests(CompanyFilterTestMixin, TestCase):
    """Creating an employee requires NFFS name + NFFS ID number."""

    def setUp(self):
        super().setUp()
        self.company = make_company("NFFS Co")
        self.admin = make_user("nffs_admin", is_superuser=True)
        make_employee(
            company=self.company,
            email="nffs_admin@test.horilla",
            user=self.admin,
        )
        self.client.force_login(self.admin)

    def test_get_create_form_marks_nffs_required(self):
        response = self.client.get(reverse("employee-view-new"))
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertTrue(form.fields["nffs_name"].required)
        self.assertTrue(form.fields["nffs_id_number"].required)

    def test_create_without_nffs_is_rejected(self):
        response = self.client.post(
            reverse("employee-create-personal-info"),
            personal_payload(),
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("nffs_name", form.errors)
        self.assertIn("nffs_id_number", form.errors)
        self.assertFalse(
            Employee.objects.entire()
            .filter(email="nora.ffs@test.horilla")
            .exists()
        )

    def test_create_with_nffs_persists(self):
        response = self.client.post(
            reverse("employee-create-personal-info"),
            personal_payload(
                nffs_name="Sandford NGO",
                nffs_id_number="NFFS-2024-001",
            ),
        )
        self.assertEqual(response.status_code, 302)
        employee = Employee.objects.entire().get(email="nora.ffs@test.horilla")
        self.assertEqual(employee.nffs_name, "Sandford NGO")
        self.assertEqual(employee.nffs_id_number, "NFFS-2024-001")

    def test_create_form_renders_nffs_section(self):
        """The Add Employee page shows a dedicated NFFS form section."""
        response = self.client.get(reverse("employee-view-new"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # both NFFS inputs are present, rendered exactly once
        self.assertIn('for="id_nffs_name"', content)
        self.assertIn('for="id_nffs_id_number"', content)
        self.assertEqual(content.count('name="nffs_name"'), 1)
        self.assertEqual(content.count('name="nffs_id_number"'), 1)
        # labels carry the required marker while creating
        self.assertIn("NFFS Name", content)
        self.assertIn("NFFS ID Number", content)


class NffsEditTests(CompanyFilterTestMixin, TestCase):
    """Editing an existing employee keeps NFFS optional."""

    def setUp(self):
        super().setUp()
        self.company = make_company("NFFS Edit Co")
        self.admin = make_user("nffs_edit_admin", is_superuser=True)
        make_employee(
            company=self.company,
            email="nffs_edit_admin@test.horilla",
            user=self.admin,
        )
        self.employee = make_employee(
            company=self.company,
            email="existing.emp@test.horilla",
            first_name="Existing",
            last_name="Emp",
        )
        self.client.force_login(self.admin)

    def _existing_payload(self, **overrides):
        return personal_payload(
            employee_first_name="Existing",
            employee_last_name="Emp",
            email="existing.emp@test.horilla",
            phone=self.employee.phone,
            badge_id=self.employee.badge_id or "",
            gender=self.employee.gender or "male",
            **overrides,
        )

    def test_edit_without_nffs_is_allowed(self):
        response = self.client.post(
            reverse("employee-update-personal-info", args=[self.employee.pk]),
            self._existing_payload(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Personal Info updated")
        employee = Employee.objects.entire().get(pk=self.employee.pk)
        self.assertIn(employee.nffs_name, ("", None))
        self.assertIn(employee.nffs_id_number, ("", None))

    def test_edit_can_set_nffs_values(self):
        response = self.client.post(
            reverse("employee-update-personal-info", args=[self.employee.pk]),
            self._existing_payload(
                nffs_name="State Fund",
                nffs_id_number="NFFS-EDIT-9",
            ),
        )
        self.assertEqual(response.status_code, 200)
        employee = Employee.objects.entire().get(pk=self.employee.pk)
        self.assertEqual(employee.nffs_name, "State Fund")
        self.assertEqual(employee.nffs_id_number, "NFFS-EDIT-9")

    def test_edit_form_renders_nffs_section(self):
        """The update page also carries the dedicated NFFS form section."""
        session = self.client.session
        session["selected_company"] = self.company.pk
        session.save()
        response = self.client.get(
            reverse("employee-view-update", args=[self.employee.pk])
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('for="id_nffs_name"', content)
        self.assertIn('for="id_nffs_id_number"', content)
        self.assertEqual(content.count('name="nffs_name"'), 1)
        self.assertEqual(content.count('name="nffs_id_number"'), 1)

    def test_personal_tab_edit_via_update_view_allows_missing_nffs(self):
        session = self.client.session
        session["selected_company"] = self.company.pk
        session.save()
        response = self.client.post(
            reverse("employee-view-update", args=[self.employee.pk]),
            self._existing_payload(form="personal"),
        )
        self.assertEqual(response.status_code, 200)
        employee = Employee.objects.entire().get(pk=self.employee.pk)
        self.assertIn(employee.nffs_name, ("", None))
        self.assertIn(employee.nffs_id_number, ("", None))


class NffsExposedEverywhereTests(CompanyFilterTestMixin, TestCase):
    """Exports, list columns, filters and the report pivot carry NFFS."""

    @classmethod
    def setUpTestData(cls):
        cls.company = make_company("NFFS Report Co")
        cls.admin = make_user("nffs_report_admin", is_superuser=True)
        make_employee(
            company=cls.company,
            email="nffs_report_admin@test.horilla",
            user=cls.admin,
        )
        cls.subject = make_employee(
            company=cls.company,
            email="nffs.subject@test.horilla",
            first_name="Nffs",
            last_name="Subject",
        )
        cls.subject.nffs_name = "Cambodia NFFS Fund"
        cls.subject.nffs_id_number = "KF-998877"
        cls.subject.save()

    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_excel_columns_include_nffs(self):
        keys = [key for key, _label in excel_columns]
        self.assertIn("nffs_name", keys)
        self.assertIn("nffs_id_number", keys)

    def test_list_view_columns_include_nffs(self):
        keys = [column[1] for column in EmployeesList.columns]
        self.assertIn("nffs_name", keys)
        self.assertIn("nffs_id_number", keys)

    def test_quick_import_fields_include_nffs(self):
        self.assertIn("nffs_name", EmployeesList.import_fields)
        self.assertIn("nffs_id_number", EmployeesList.import_fields)

    def test_employee_filter_form_exposes_nffs_fields(self):
        form = EmployeeFilter().form
        self.assertIn("nffs_name", form.fields)
        self.assertIn("nffs_id_number", form.fields)

    def test_report_pivot_rows_include_nffs(self):
        response = self.client.get(reverse("employee-pivot"))
        self.assertEqual(response.status_code, 200)
        rows = json.loads(response.content)
        row = next(
            row for row in rows if row.get("Email") == "nffs.subject@test.horilla"
        )
        self.assertEqual(row["NFFS Name"], "Cambodia NFFS Fund")
        self.assertEqual(row["NFFS ID Number"], "KF-998877")

