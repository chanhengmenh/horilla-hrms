"""
tax_models.py

This module contains the models for the tax calculation of taxable income.
"""

import math

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from horilla.models import HorillaModel
from payroll.models.models import FilingStatus


class PayrollSettings(HorillaModel):
    """
    Payroll settings model
    """

    choices = [
        ("prefix", _("Prefix")),
        ("postfix", _("Suffix")),
    ]

    currency_symbol = models.CharField(null=True, default="$", max_length=5)
    position = models.CharField(
        max_length=15, null=True, choices=choices, default="postfix"
    )
    usd_to_khr_rate = models.FloatField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("USD to KHR Exchange Rate"),
        help_text=_(
            "1 USD equals this many Cambodian Riel (KH). Create it once from "
            "Payroll -> Salary Tax -> Create Exchange Rate; every salary "
            "calculation then uses it automatically. No rate is hard-coded."
        ),
    )
    nffs_exchange_rate = models.FloatField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("NFFS Exchange Rate"),
        help_text=_(
            "1 USD equals this many NFFS units. Used to convert USD "
            "amounts for NFFS membership and contribution records. Create "
            "it once from Settings -> General -> Exchange Rate; every NFFS "
            "calculation then uses it automatically. No rate is hard-coded."
        ),
    )
    nffs_effective_date = models.DateField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("NFFS Exchange Rate Effective Date"),
        help_text=_(
            "The day the manually entered NFFS exchange rate applies from. "
            "Defaults to the day the rate was saved."
        ),
    )
    auto_fetch_nffs_rate = models.BooleanField(
        default=False,
        verbose_name=_("Automatic monthly NFFS fetch"),
        help_text=_(
            "Off (default): the NFFS exchange rate is maintained manually "
            "and is never overwritten automatically. On: the official rate "
            "of the 15th of every month is applied automatically by the "
            "background scheduler (manual mode is recommended)."
        ),
    )
    auto_fetch_nbc_rate = models.BooleanField(
        default=False,
        verbose_name=_("Automatic monthly NBC fetch"),
        help_text=_(
            "Off (default): the USD -> KHR exchange rate is maintained manually "
            "and is never overwritten automatically. On: the official National "
            "Bank of Cambodia rate of the 15th of every month is applied "
            "automatically by the background scheduler."
        ),
    )

    company_id = models.ForeignKey(Company, null=True, on_delete=models.PROTECT)
    objects = HorillaCompanyManager("company_id")

    class Meta:
        verbose_name = _("Payroll Settings")
        verbose_name_plural = _("Payroll Settings")

    def __str__(self):
        return f"Payroll Settings {self.currency_symbol}"


class NBCExchangeRate(HorillaModel):
    """
    History of the USD -> KHR exchange rates that have been applied to the
    system.

    The official rate published by the National Bank of Cambodia (NBC) on the
    15th of every month is fetched automatically ONLY when HR switched the
    "Automatic monthly NBC fetch" toggle ON from Settings -> General (see
    :func:`payroll.methods.nbc_exchange.ensure_monthly_nbc_rate`); by default
    the exchange rate is maintained manually and the automatic fetch never
    overwrites it. If the 15th falls on a Saturday or a
    Sunday, the rate of the closest working day BEFORE the 15th (Friday) is
    used, because only Monday - Friday are working days in Cambodia. Manual
    entries made from Settings -> General -> System Preferences are stored
    here too.
    """

    SOURCE_CHOICES = [
        ("nbc", _("National Bank of Cambodia (automatic)")),
        ("nffs", _("National Social Security Fund (automatic)")),
        ("manual", _("Manual entry")),
    ]

    requested_date = models.DateField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("Requested Date"),
        help_text=_("The date that was asked for (usually the 15th of the month)."),
    )
    effective_date = models.DateField(
        unique=True,
        verbose_name=_("Effective Date"),
        help_text=_("The working day the exchange rate is valid for."),
    )
    rate = models.FloatField(
        verbose_name=_("Rate (1 USD = ? KHR)"),
    )
    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default="nbc",
        verbose_name=_("Source"),
    )
    company_id = models.ForeignKey(Company, null=True, on_delete=models.PROTECT)
    objects = HorillaCompanyManager("company_id")

    class Meta:
        verbose_name = _("Exchange Rate (NBC)")
        verbose_name_plural = _("Exchange Rates (NBC)")
        ordering = ["-effective_date"]

    def __str__(self):
        return (
            f"1 USD = {self.rate} KHR "
            f"({self.effective_date}, {self.get_source_display()})"
        )


class TaxBracket(HorillaModel):
    """
    TaxBracket model
    """

    filing_status_id = models.ForeignKey(
        FilingStatus,
        on_delete=models.CASCADE,
        verbose_name=_("Filing status"),
    )
    min_income = models.FloatField(
        null=False, blank=False, verbose_name=_("Min. Income")
    )
    max_income = models.FloatField(null=True, blank=True, verbose_name=_("Max. Income"))
    tax_rate = models.FloatField(
        null=False, blank=False, default=0.0, verbose_name=_("Tax Rate")
    )
    deduction = models.FloatField(
        null=False,
        blank=False,
        default=0.0,
        verbose_name=_("Deduction"),
        help_text=_(
            "Flat deduction amount used with the Cambodia tax formula: "
            "(monthly salary x tax rate) - deduction."
        ),
    )
    objects = models.Manager()

    def __str__(self):
        if self.max_income != math.inf:
            return (
                f"{self.filing_status_id}"
                f"{self.tax_rate}% tax rate on "
                f"{self.min_income} and {self.max_income}"
            )
        return (
            f"{self.tax_rate}% tax rate on taxable income equal or above "
            f"{self.min_income} for {self.filing_status_id}"
        )

    def get_display_max_income(self):
        """
        Retrieves the maximum income.
        Returns:
            float or None: The maximum income if it is a finite value, otherwise None.
        """
        if self.max_income != math.inf:
            return self.max_income
        return None

    def get_update_url(self):
        """
        Returns the URL for updating the tax bracket.
        """

        return reverse("tax-bracket-update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        Returns the URL for updating the tax bracket.
        """

        return reverse("tax-bracket-delete", kwargs={"tax_bracket_id": self.pk})

    def clean(self):
        super().clean()

        existing_bracket = TaxBracket.objects.filter(
            filing_status_id=self.filing_status_id,
            min_income=self.min_income,
            max_income=self.max_income,
            tax_rate=self.tax_rate,
        ).exclude(pk=self.pk)
        if existing_bracket.exists():
            raise ValidationError(_("This tax bracket already exists"))

        if self.max_income is None:
            self.max_income = math.inf

        if self.min_income >= self.max_income:
            raise ValidationError(
                {"max_income": _("Maximum income must be greater than minimum income.")}
            )

        existing_brackets = TaxBracket.objects.filter(
            filing_status_id=self.filing_status_id
        ).exclude(pk=self.pk)
        if existing_brackets.filter(max_income__gte=self.min_income).exists():
            tax_bracket = existing_brackets.filter(
                max_income__gte=self.min_income
            ).first()
            if tax_bracket.min_income <= self.max_income:
                raise ValidationError(
                    {
                        "min_income": format_lazy(
                            "The minimum income of this tax bracket must be \
                                greater than the maximum income of {}.",
                            tax_bracket,
                        )
                    }
                )
