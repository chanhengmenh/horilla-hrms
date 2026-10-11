"""
Management command to fetch the monthly NBC exchange rate manually.

    python manage.py fetch_nbc_exchange_rate
    python manage.py fetch_nbc_exchange_rate --date 2026-09-15

Fetches the official National Bank of Cambodia USD -> KHR rate of the 15th of
the given month (or of the current month when ``--date`` is omitted),
resolving weekends to the closest previous working day (Monday - Friday),
and applies it as the active exchange rate used by the payroll salary tax /
NSSF pension calculation.

The background scheduler runs the same logic automatically every few hours
(payroll.scheduler.fetch_nbc_exchange_rate); this command exists for manual
runs and cron setups.
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from payroll.methods.nbc_exchange import apply_nbc_rate_for_date


class Command(BaseCommand):
    help = (
        "Fetch the official NBC USD -> KHR exchange rate of the 15th of the "
        "month (closest working day when the 15th is a weekend) and apply it "
        "to the payroll salary-tax calculation."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Requested date, e.g. 2026-09-15. The 15th of that month is used.",
        )

    def handle(self, *args, **options):
        requested = None
        raw_date = options.get("date")
        if raw_date:
            try:
                requested = date.fromisoformat(raw_date)
            except ValueError:
                raise CommandError(f"Invalid --date value: {raw_date}")

        record, message = apply_nbc_rate_for_date(requested=requested)
        if record is not None:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.WARNING(message))
