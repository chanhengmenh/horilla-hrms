"""
delete_test_users - remove the test users / employees seeded by create_test_users.

Only the logins defined in ``create_test_users.TEST_EMPLOYEES`` (``test.sok``,
``test.chan``, ``test.sophea``, ``test.rithy``, ``test.kanha``, ``test.vireak``)
are ever touched. Logins created by HR by hand are NEVER deleted.

    python manage.py delete_test_users --dry-run   # preview, changes nothing
    python manage.py delete_test_users             # delete for real

For every test user the command removes:

  - the objects that PROTECT the employee (attendance, payslips, contracts,
    loans, reimbursements, ...). Those relations are discovered from the model
    metadata, so new payroll / attendance models are covered automatically -
    nothing is hard-coded.
  - the Employee and everything that cascades from it (work information, bank
    details, contracts, overtime attendance, allowance assignments, ...)
  - the login itself.

Shared set-up created by create_test_users (company, department, job position,
shift, filing status / tax brackets, the exchange rate and the "Overtime
Allowance") is deliberately LEFT IN PLACE: HR may already be using it.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models import PROTECT
from django.db.models.deletion import ProtectedError

from employee.models import Employee
from payroll.management.commands.create_test_users import TEST_EMPLOYEES

# The only logins this command may ever delete.
TEST_USERNAMES = tuple(row[0] for row in TEST_EMPLOYEES)


class Command(BaseCommand):
    help = (
        "Delete ONLY the test users/employees created by create_test_users "
        f"({', '.join(TEST_USERNAMES)}); HR-created users are never touched."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without changing anything.",
        )

    # ------------------------------------------------------------------
    # entrypoint
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - nothing will be deleted.\n"))
        else:
            self.stdout.write(
                "Deleting the test users created by create_test_users...\n"
            )

        user_model = get_user_model()
        deleted, missing = [], []

        for username in TEST_USERNAMES:
            user = user_model.objects.filter(username=username).first()
            if user is None:
                missing.append(username)
                self.stdout.write(f"  {username}: not found, skipped")
                continue

            employee = Employee.objects.filter(employee_user_id=user).first()
            self.stdout.write(f"  {username}:")
            if employee is not None:
                self._clear_blockers(employee, dry_run)

            if dry_run:
                self.stdout.write(
                    "      would delete the employee, work info, bank details,"
                    " contracts and the login"
                )
                continue

            if employee is not None:
                self._delete_with_blockers([employee])
            user.delete()
            deleted.append(username)
            self.stdout.write(self.style.SUCCESS("      deleted"))

        self._print_summary(deleted, missing, dry_run)

    # ------------------------------------------------------------------
    # PROTECT relations (attendance, payslips, contracts, loans, ...)
    # ------------------------------------------------------------------

    def _protected_relations(self, employee):
        """
        Return ``[(label, related), ...]`` for every relation that PROTECTs this
        employee (attendance, payslips, contracts, loans, reimbursements, ...).

        The relations are read from the model metadata instead of being
        hard-coded, so new payroll / attendance models are handled without
        touching this command. CASCADE / SET_NULL children need no handling:
        Django removes them together with the employee.
        """
        relations = []
        for relation in employee._meta.related_objects:
            field = relation.field
            if field.many_to_many:
                # Through rows are removed together with the employee.
                continue
            if getattr(field.remote_field, "on_delete", None) is not PROTECT:
                continue
            try:
                related = getattr(employee, relation.get_accessor_name())
            except ObjectDoesNotExist:
                # A reverse one-to-one that has no row.
                continue
            relations.append((field.model._meta.verbose_name_plural, related))
        return relations

    @staticmethod
    def _as_list(related):
        """A reverse FK manager expands to its rows; a one-to-one stays one row."""
        if hasattr(related, "all"):
            return list(related.all())
        return [related]

    def _clear_blockers(self, employee, dry_run):
        """Delete (or, in a dry run, just report) what PROTECTs the employee."""
        for label, related in self._protected_relations(employee):
            objects = self._as_list(related)
            if not objects:
                continue
            self.stdout.write(f"      {len(objects)} x {label}")
            if not dry_run:
                self._delete_with_blockers(objects)

    def _delete_with_blockers(self, objects):
        """
        Delete ``objects``, first removing the objects that PROTECT them
        (recursively), because Django refuses to delete a row while a PROTECT
        relation still points at it.
        """
        for obj in objects:
            try:
                obj.delete()
            except ProtectedError as exc:
                for blocker in exc.protected_objects:
                    self._delete_with_blockers([blocker])
                obj.delete()

    # ------------------------------------------------------------------
    # summary
    # ------------------------------------------------------------------

    def _print_summary(self, deleted, missing, dry_run):
        """Tell the operator exactly what happened (or would happen)."""
        self.stdout.write("")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN finished - {len(TEST_USERNAMES) - len(missing)} test "
                    "user(s) would be deleted. Re-run without --dry-run to delete "
                    "them for real."
                )
            )
            return

        if deleted:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {len(deleted)} test user(s): {', '.join(deleted)}"
                )
            )
        else:
            self.stdout.write("No test user had to be deleted.")

        if missing:
            self.stdout.write(f"Not present (skipped): {', '.join(missing)}")

        self.stdout.write(
            "Kept in place: the shared setup (company, department, job position, "
            "shift, filing status, tax brackets, exchange rate, Overtime Allowance)."
        )
        self.stdout.write("Users you created yourself were not touched.")

