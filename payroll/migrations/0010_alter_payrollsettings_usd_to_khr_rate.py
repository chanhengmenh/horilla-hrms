from django.db import migrations, models


def clear_seeded_rates(apps, schema_editor):
    """
    The exchange rate must come ONLY from the UI input (Payroll -> Salary Tax
    -> Create Exchange Rate). Drop any value that was pre-seeded by the old
    hard-coded default so HR creates the real rate themselves.
    """
    PayrollSettings = apps.get_model("payroll", "PayrollSettings")
    PayrollSettings.objects.update(usd_to_khr_rate=None)


class Migration(migrations.Migration):

    dependencies = [
        ("payroll", "0009_payrollsettings_usd_to_khr_rate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payrollsettings",
            name="usd_to_khr_rate",
            field=models.FloatField(
                blank=True,
                default=None,
                help_text=(
                    "1 USD equals this many Cambodian Riel (KH). Create it once "
                    "from Payroll -> Salary Tax -> Create Exchange Rate; every "
                    "salary calculation then uses it automatically. No rate is "
                    "hard-coded."
                ),
                null=True,
                verbose_name="USD to KHR Exchange Rate",
            ),
        ),
        migrations.RunPython(clear_seeded_rates, migrations.RunPython.noop),
    ]
