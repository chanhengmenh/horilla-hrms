from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("payroll", "0010_alter_payrollsettings_usd_to_khr_rate"),
    ]

    operations = [
        migrations.CreateModel(
            name="NBCExchangeRate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, null=True, verbose_name="Created At"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Is Active"),
                ),
                (
                    "requested_date",
                    models.DateField(
                        blank=True,
                        default=None,
                        help_text=(
                            "The date that was asked for (usually the 15th of "
                            "the month)."
                        ),
                        null=True,
                        verbose_name="Requested Date",
                    ),
                ),
                (
                    "effective_date",
                    models.DateField(
                        help_text="The working day the exchange rate is valid for.",
                        unique=True,
                        verbose_name="Effective Date",
                    ),
                ),
                (
                    "rate",
                    models.FloatField(verbose_name="Rate (1 USD = ? KHR)"),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("nbc", "National Bank of Cambodia (automatic)"),
                            ("manual", "Manual entry"),
                        ],
                        default="nbc",
                        max_length=10,
                        verbose_name="Source",
                    ),
                ),
                (
                    "company_id",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="base.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_modified_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Modified By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Exchange Rate (NBC)",
                "verbose_name_plural": "Exchange Rates (NBC)",
                "ordering": ["-effective_date"],
            },
        ),
    ]

