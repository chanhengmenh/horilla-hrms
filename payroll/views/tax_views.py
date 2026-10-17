"""
tax_views.py

This module contains view functions for handling federal tax-related operations.

The functions in this module handle various tasks related to payroll, including creating
filing status, managing tax brackets, calculating federal tax, and more. These functions
utilize the Django framework and make use of the render and redirect functions from the
django.shortcuts module.

"""

import math
import calendar
from urllib.parse import parse_qs

from datetime import date, timedelta

from django.contrib import messages
from django.db.models import ProtectedError, Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from base.methods import get_key_instances, get_session_company
from base.models import Holidays
from horilla.decorators import hx_request_required, login_required, permission_required
from horilla.http.response import HorillaRedirect
from payroll.forms.tax_forms import (
    ExchangeRateForm,
    FilingStatusForm,
    NFFSExchangeRateForm,
    SettingsExchangeRateForm,
    TaxBracketForm,
)
from payroll.methods.cambodia_calendar import get_cambodia_public_holidays
from payroll.methods.nbc_exchange import (
    NBC_RATE_DAY,
    get_nbc_rate_panel_context,
    apply_exchange_rate,
    apply_nbc_rate_for_date,
    get_official_nbc_rate,
    get_working_day_for_date,
)
from payroll.methods.safe_tax_code import TaxCodeValidationError, validate_tax_code
from payroll.methods.tax_calc import get_usd_to_khr_rate
from payroll.models.models import FilingStatus
from payroll.models.tax_models import NBCExchangeRate, PayrollSettings, TaxBracket


@login_required
@permission_required("payroll.view_filingstatus")
def filing_status_view(request):
    """
    Display the filing status view.

    This view retrieves all filing statuses from the database and renders the
    'payroll/tax/filing_status_view.html' template with the filing status data.

    """
    status = FilingStatus.objects.all()
    template = "payroll/tax/filing_status_view.html"

    # USD -> KH exchange rate created by HR from this page. It is None until
    # HR creates it via the "Create Exchange Rate" button — no rate is ever
    # hard-coded in the source code.
    exchange_rate = get_usd_to_khr_rate()
    rate_form = ExchangeRateForm()

    context = {
        "status": status,
        "exchange_rate": exchange_rate,
        "rate_form": rate_form,
    }
    return render(request, template, context)


@login_required
@permission_required("payroll.change_payrollsettings")
def exchange_rate_view(request):
    """
    Update the USD -> KHR exchange rate used by the Cambodia salary tax.

    The view is used by the inline "Exchange Rate" form on the Salary Tax page
    (Payroll -> Salary Tax). On a successful POST the rate card fragment is
    re-rendered (HTMX outerHTML swap) so the new value is displayed right away,
    and every salary / pension calculation picks the new rate up automatically.

    """
    # THE shared settings row (created lazily on the first save) so there is
    # only ever ONE active rate row — saving while a different company is
    # selected must not create a second, competing row.
    instance = _get_payroll_settings_instance(request, create=True)

    exchange_rate = instance.usd_to_khr_rate

    if request.method == "POST":
        form = ExchangeRateForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            instance.refresh_from_db()
            exchange_rate = instance.usd_to_khr_rate
            form = ExchangeRateForm(instance=instance)
            messages.success(request, _("Exchange rate updated successfully."))
        else:
            messages.error(
                request, _("Enter a valid exchange rate greater than zero.")
            )
            exchange_rate = instance.usd_to_khr_rate
    else:
        form = ExchangeRateForm(instance=instance)

    context = {
        "exchange_rate": exchange_rate,
        "rate_form": form,
    }
    return render(request, "payroll/tax/exchange_rate_form.html", context)


def _get_payroll_settings_instance(request, create=False):
    """
    Resolve THE single PayrollSettings row that carries the exchange-rate
    data (USD -> KHR and NFFS).

    Every view that touches the rates must use this helper so they all
    agree on the same row. Looking the row up by different criteria (one
    view by company, another by "usd rate is set") used to split the data
    across several rows: the NFFS rate saved by one view was invisible to
    the others after a page refresh, and empty duplicate rows piled up.
    """
    tracking_company = get_session_company(request)
    # 1) Prefer the row that actually carries rate data (oldest first).
    instance = (
        PayrollSettings._base_manager.filter(
            Q(usd_to_khr_rate__isnull=False) | Q(nffs_exchange_rate__isnull=False)
        )
        .order_by("id")
        .first()
    )
    if instance is not None:
        return instance
    # 2) Any existing row for the session company (or a global row).
    instance = (
        PayrollSettings._base_manager.filter(company_id=tracking_company)
        .order_by("id")
        .first()
    )
    # 3) Create one lazily - only ever from POST handlers (create=True),
    #    never from a plain page load.
    if instance is None and create:
        instance = PayrollSettings.objects.create(company_id=tracking_company)
    return instance


@login_required
@hx_request_required
@permission_required("payroll.change_payrollsettings")
def settings_exchange_rate_nffs_view(request):
    """
    NFFS Exchange Rate card for Settings -> General (System Preferences).

    Shows the active NFFS exchange rate (1 USD = ? NFFS) with a manual
    update form and the recent NFFS rate history. On a successful POST the
    card fragment is re-rendered (HTMX outerHTML swap) so the new value
    shows right away.
    """
    # THE shared settings row (created lazily on the first save).
    instance = _get_payroll_settings_instance(request, create=True)

    if request.method == "POST":
        form = NFFSExchangeRateForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            instance.refresh_from_db()
            messages.success(request, _("NFFS exchange rate updated successfully."))
        else:
            messages.error(
                request, _("Enter a valid exchange rate greater than zero.")
            )
    else:
        form = NFFSExchangeRateForm(instance=instance)

    context = _get_settings_rate_context(request, rate_form=form)
    return render(request, "payroll/settings/nbc_exchange_rate.html", context)


@login_required
@hx_request_required
@permission_required("payroll.change_payrollsettings")
def settings_exchange_rate_nffs_auto_fetch_toggle(request):
    """
    Toggle the "Automatic monthly NFFS fetch" switch of the Exchange Rate
    card (Settings -> General).

    The switch defaults to OFF: the NFFS exchange rate is then input MANUALLY
    and is never overwritten by the background jobs, which only ever adjust
    the USD -> KHR rate. Switching ON re-enables the automatic application
    of the official NFFS rate of the 15th of every month (scheduler job to
    be added separately).
    """
    # THE shared settings row (created lazily on the first save).
    instance = _get_payroll_settings_instance(request, create=True)
    # Honour the checkbox value posted by the oh-switch; fall back to a flip
    # when the payload does not carry one (defensive).
    if "auto_fetch_nffs_rate" in request.POST:
        enabled = request.POST.get("auto_fetch_nffs_rate") in ("on", "true", "1")
    else:
        enabled = not instance.auto_fetch_nffs_rate
    instance.auto_fetch_nffs_rate = enabled
    instance.save()

    messages.success(
        request,
        _(
            "Automatic monthly NFFS fetch enabled: the official rate of the "
            "15th will be applied automatically."
        )
        if enabled
        else _(
            "Automatic monthly NFFS fetch disabled: the exchange rate is now "
            "maintained manually and will never be overwritten."
        ),
    )
    context = _get_settings_rate_context(request)
    return render(request, "payroll/settings/nbc_exchange_rate.html", context)


def _parse_iso_date(value):
    """
    Parse an ``YYYY-MM-DD`` value coming from the effective-date field of the
    Exchange Rate Calendar form.

    Returns:
        tuple: ``(date | None, is_valid)``. An empty value is valid and means
        "today" (the caller decides); a malformed value is invalid so the view
        can reject it instead of silently saving the rate on the wrong day.
    """
    raw = (value or "").strip()
    if not raw:
        return None, True
    try:
        return date.fromisoformat(raw), True
    except ValueError:
        return None, False


def _holiday_bounds(holiday, year):
    """
    Inclusive ``(start, end)`` date range of a :class:`base.models.Holidays`
    row as observed in ``year``.

    Recurring holidays repeat every year, so their month / day window is
    mapped onto ``year`` (a 29 February start falls back to 28 February in
    non-leap years). Non-recurring holidays are returned exactly as stored.
    """
    start = holiday.start_date
    end = holiday.end_date or start
    if not holiday.recurring or start.year == year:
        return start, end
    span = (end - start).days
    try:
        start = start.replace(year=year)
    except ValueError:  # 29 February in a non-leap year
        start = date(year, start.month, 28)
    return start, start + timedelta(days=span)


def _build_exchange_rate_calendar(month=None):
    """
    Build the month grid of the Settings -> General "Exchange Rate Calendar".

    The grid is returned as a list of weeks (each week a list of day cells) so
    the template can render a valid 7-column ``<table>`` - a flat list made the
    template open and close ``<tr>`` on the same index, which mangled the grid.

    Each cell carries the USD -> KHR rate stored for that day (if any), the
    automatic resolution of the 15th (weekend and public-holiday days roll
    back to the closest previous working day) and the day whose rate is
    currently applied to the payroll calculation.

    The grid follows the Cambodian calendar: the week starts on Sunday and
    every day knows whether it is a weekend or a public holiday (the national
    Cambodian holidays of :mod:`payroll.methods.cambodia_calendar` merged with
    the holidays configured in Settings -> Holidays), so the template can
    colour those day numbers red and print the holiday names.

    Args:
        month (date): Any date inside the month to display (default: today).

    Returns:
        dict: Calendar context used by
        ``payroll/settings/nbc_exchange_calendar.html``.
    """
    today = date.today()
    month = (month or today).replace(day=1)

    requested_15 = month.replace(day=NBC_RATE_DAY)
    working_day = get_working_day_for_date(requested_15)
    day_15_is_weekend = requested_15 != working_day

    last_day_number = calendar.monthrange(month.year, month.month)[1]
    month_end = month.replace(day=last_day_number)
    stored_rates = {
        record.effective_date: record
        for record in NBCExchangeRate.objects.filter(
            effective_date__gte=month,
            effective_date__lte=month_end,
        )
    }

    # ── Cambodian calendar: public holidays of the displayed month ──────────
    # National Cambodian holidays (static table) merged with the holidays
    # configured in Settings -> Holidays, keyed by date so every cell can
    # show the name(s) of the day.
    holiday_names_by_date = {}
    for holiday_date, holiday_name in get_cambodia_public_holidays(month.year):
        if month <= holiday_date <= month_end:
            holiday_names_by_date.setdefault(holiday_date, []).append(holiday_name)

    for holiday in Holidays.objects.all():
        holiday_start, holiday_end = _holiday_bounds(holiday, month.year)
        if holiday_end < month or holiday_start > month_end:
            continue
        cursor = max(holiday_start, month)
        last_day = min(holiday_end, month_end)
        while cursor <= last_day:
            holiday_names_by_date.setdefault(cursor, []).append(holiday.name)
            cursor += timedelta(days=1)

    latest = NBCExchangeRate.objects.order_by("-effective_date").first()
    applied_date = latest.effective_date if latest else None

    is_current_month = (month.year, month.month) == (today.year, today.month)

    # Sunday is the first day of the week in the Cambodian calendar view.
    grid = calendar.Calendar(firstweekday=6)  # 6 = Sunday
    weeks = []
    for week in grid.monthdays2calendar(month.year, month.month):
        cells = []
        for day_number, weekday in week:
            cell_date = month.replace(day=day_number) if day_number else None
            cell = {
                "day": day_number or None,
                "weekday": weekday,
                "date": cell_date,
                # Saturday (5) and Sunday (6) are the weekend in Cambodia.
                "is_weekend": bool(day_number) and weekday >= 5,
                "holiday_names": holiday_names_by_date.get(cell_date, [])
                if cell_date
                else [],
                "is_today": bool(day_number)
                and is_current_month
                and day_number == today.day,
                "is_15th": bool(day_number) and day_number == NBC_RATE_DAY,
                "is_resolved_working_day": bool(day_number)
                and day_number == working_day.day,
                "rate": None,
                "source": "",
                "is_applied": False,
            }
            if day_number:
                record = stored_rates.get(cell_date)
                if record is not None:
                    cell["rate"] = record.rate
                    cell["source"] = record.source
                    cell["is_applied"] = record.effective_date == applied_date
            cells.append(cell)
        weeks.append(cells)

    prev_month = (month - timedelta(days=1)).replace(day=1)
    next_month = month.replace(day=last_day_number) + timedelta(days=1)

    return {
        "calendar_month": month,
        "calendar_month_value": f"{month:%Y-%m}",
        "calendar_month_label": month.strftime("%B %Y"),
        "calendar_prev_month_value": f"{prev_month:%Y-%m}",
        "calendar_next_month_value": f"{next_month:%Y-%m}",
        "calendar_weeks": weeks,
        "calendar_day_names": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "calendar_is_current_month": is_current_month,
        "calendar_requested_date": requested_15,
        "calendar_working_day_date": working_day,
        "calendar_day_15_is_weekend": day_15_is_weekend,
        "calendar_default_effective_date": today if is_current_month else requested_15,
        "calendar_applied_date": applied_date,
        # Public holidays of the displayed month, for the legend below the grid.
        "calendar_month_holidays": [
            {"date": holiday_date, "names": names}
            for holiday_date, names in sorted(holiday_names_by_date.items())
        ],
    }


def _get_settings_rate_context(request, rate_form=None):
    """
    Shared context builder for the Exchange Rate card on the System
    Preferences page (Settings -> General).
        """
    # THE shared settings row. Never created on a plain page load: render the
    # empty state instead of writing a junk row to the database.
    instance = _get_payroll_settings_instance(request)
    if instance is None:
        instance = PayrollSettings()

    today = date.today()

    # Month displayed by the Exchange Rate Calendar (default: this month).
    calendar_month = _parse_month(
        (request.GET.get("month") or request.POST.get("month")) if request else None
    )

    # Resolve the 15th of *this* month to a working day (automatic schedule).
    requested_15 = today.replace(day=NBC_RATE_DAY)
    working_day = get_working_day_for_date(requested_15)
    day_15_is_weekend = requested_15 != working_day

    # Next month's 15th and its working-day resolution (for the preview).
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    next_15 = next_month.replace(day=NBC_RATE_DAY)
    next_working_day = get_working_day_for_date(next_15)
    next_day_is_weekend = next_15 != next_working_day

    # ── Next-month NBC preview (best-effort, may be None) ────────────
    next_preview = None
    try:
        next_preview = get_official_nbc_rate(month=next_month, refresh=False)
    except Exception:
        next_preview = None

    # Automatic monthly fetch toggles (both default OFF = manual entry only).
    # The flags live on THE shared settings row so the switches on the card
    # always match what the toggle views write.
    auto_fetch_nbc_rate = bool(instance.auto_fetch_nbc_rate)
    auto_fetch_nffs_rate = bool(instance.auto_fetch_nffs_rate)

    # Create the NFFS exchange rate form from the rate_form parameter if provided,
    # otherwise create a new form for the instance. This ensures the saved/updated
    # form state is preserved after HTMX form submission.
    if rate_form is not None:
        nffs_rate_form = rate_form
    else:
        nffs_rate_form = NFFSExchangeRateForm(instance=instance)

    context = {
        "exchange_rate": instance.usd_to_khr_rate,
        "rate_form": rate_form or SettingsExchangeRateForm(instance=instance),
        "nffs_rate_form": nffs_rate_form,
        "nffs_exchange_rate": instance.nffs_exchange_rate,
        "nffs_effective_date": instance.nffs_effective_date,
        "nffs_auto_fetch_rate": auto_fetch_nffs_rate,
        "rate_history": NBCExchangeRate.objects.all()[:12],
        "current_date": today,
        "auto_fetch_nbc_rate": auto_fetch_nbc_rate,
        "next_effective_date": requested_15,
        # Automatic day-15 schedule (always about the CURRENT month).
        "day_15_date": requested_15,
        "working_day_date": working_day,
        "day_15_is_weekend": day_15_is_weekend,
        "next_month_15": next_15,
        "next_working_day": next_working_day,
        "next_day_is_weekend": next_day_is_weekend,
        "next_preview_rate": next_preview.get("rate") if next_preview else None,
        "next_preview_published_date": next_preview.get("published_date")
        if next_preview
        else None,
    }
    # Month grid + per-day rate form of the Exchange Rate Calendar.
    context.update(_build_exchange_rate_calendar(calendar_month))
    return context


@login_required
@hx_request_required
@permission_required("payroll.change_payrollsettings")
def settings_exchange_rate_view(request):
    """
    Exchange Rate card for Settings -> General (System Preferences).

    Shows the active USD -> KHR exchange rate (the very same value the
    Cambodia salary tax / NSSF pension calculation uses) with a manual
    update form, a "Fetch from NBC" button and the recent rate history.
    On a successful POST the card fragment is re-rendered (HTMX outerHTML
    swap) so the new value shows right away.
    """
    form = None
    if request.method == "POST":
        instance = _get_payroll_settings_instance(request, create=True)

        # The Exchange Rate Calendar can set the rate of one explicit day;
        # the plain card form always applies to today.
        effective_date, effective_valid = _parse_iso_date(
            request.POST.get("effective_date")
        )
        form = SettingsExchangeRateForm(request.POST, instance=instance)
        if not effective_valid:
            messages.error(request, _("Enter a valid effective date (YYYY-MM-DD)."))
        elif effective_date and effective_date > date.today():
            messages.error(request, _("The effective date can not be in the future."))
        elif form.is_valid():
            new_rate = form.cleaned_data["usd_to_khr_rate"]
            apply_date = effective_date or date.today()
            apply_exchange_rate(
                rate=new_rate,
                effective_date=apply_date,
                source="manual",
                requested_date=apply_date,
            )
            messages.success(request, _("Exchange rate updated successfully."))
            form = None
        else:
            messages.error(
                request, _("Enter a valid exchange rate greater than zero.")
            )

    context = _get_settings_rate_context(request, rate_form=form)
    return render(request, "payroll/settings/nbc_exchange_rate.html", context)


@login_required
@hx_request_required
@permission_required("payroll.change_payrollsettings")
def settings_exchange_rate_fetch_nbc(request):
    """
    "Fetch from NBC" button on the Exchange Rate card.

    Pulls the official National Bank of Cambodia USD -> KHR rate of the 15th
    of the current month (resolved to the closest working day Monday-Friday
    when the 15th falls on a weekend) and applies it as the active exchange
    rate used by the payroll salary tax / NSSF pension calculation.
    """
    _record, message = apply_nbc_rate_for_date()
    if _record is not None:
        messages.success(request, _(message))
    else:
        messages.error(request, _(message))

    context = _get_settings_rate_context(request)
    return render(request, "payroll/settings/nbc_exchange_rate.html", context)


@login_required
@hx_request_required
@permission_required("payroll.change_payrollsettings")
def settings_exchange_rate_auto_fetch_toggle(request):
    """
    Toggle the "Automatic monthly NBC fetch" switch of the Exchange Rate card
    (Settings -> General).

    The switch defaults to OFF: the USD -> KHR exchange rate is then input
    MANUALLY and the background scheduler (payroll.scheduler
    .fetch_nbc_exchange_rate -> ensure_monthly_nbc_rate) never overwrites it.
    Switching ON re-enables the automatic application of the official NBC
    rate of the 15th of every month.
    """
    # THE shared settings row (created lazily on the first save).
    instance = _get_payroll_settings_instance(request, create=True)
    # Honour the checkbox value posted by the oh-switch; fall back to a flip
    # when the payload does not carry one (defensive).
    if "auto_fetch_nbc_rate" in request.POST:
        enabled = request.POST.get("auto_fetch_nbc_rate") in ("on", "true", "1")
    else:
        enabled = not instance.auto_fetch_nbc_rate
    instance.auto_fetch_nbc_rate = enabled
    instance.save()

    messages.success(
        request,
        _(
            "Automatic monthly NBC fetch enabled: the official rate of the "
            "15th will be applied automatically."
        )
        if enabled
        else _(
            "Automatic monthly NBC fetch disabled: the exchange rate is now "
            "maintained manually and will never be overwritten."
        ),
    )
    context = _get_settings_rate_context(request)
    return render(request, "payroll/settings/nbc_exchange_rate.html", context)


def _parse_month(value):
    """
    Parse a ``YYYY-MM`` value coming from the NBC panel's month picker.

    Any missing or malformed value falls back to the current month, so a bad
    query string can never break the exchange-rate card.
    """
    if value:
        try:
            year, month = str(value).split("-")[:2]
            return date(int(year), int(month), 1)
        except (TypeError, ValueError):
            pass
    return date.today()


@login_required
@hx_request_required
@permission_required("payroll.view_payrollsettings")
def settings_exchange_rate_nbc_panel(request):
    """
    National Bank of Cambodia panel of the Exchange Rate card.

    This is the "NBC" part of the card on Settings -> General: the official
    rate of the 15th of the month, shown prominently, plus every USD -> KHR
    rate NBC published during that month. It is rendered as its own fragment
    and loaded lazily by the card, so a slow or unreachable NBC service never
    blocks the System Preferences page.

    ``?month=YYYY-MM`` browses another month and ``?refresh=1`` ignores the
    one hour cache and asks NBC again.
    """
    context = get_nbc_rate_panel_context(
        month=_parse_month(request.GET.get("month")),
        refresh=request.GET.get("refresh") in ("1", "true", "True", "yes"),
    )
    return render(request, "payroll/settings/nbc_exchange_panel.html", context)


@login_required
@hx_request_required
@permission_required("payroll.view_payrollsettings")
def settings_exchange_rate_calendar(request):
    """
    Exchange Rate Calendar of the Settings -> General "Exchange Rate" card.

    The calendar is a self-contained fragment: the month navigation
    (previous / month picker / next) and the "set the rate of a day" form
    refresh only this fragment with HTMX, so navigating the calendar never
    reloads the System Preferences page and never queries NBC (the grid is
    built from the stored :class:`~payroll.models.tax_models.NBCExchangeRate`
    history only).

    ``?month=YYYY-MM`` browses another month; anything malformed falls back to
    the current month.
    """
    context = _build_exchange_rate_calendar(_parse_month(request.GET.get("month")))
    context["exchange_rate"] = get_usd_to_khr_rate()
    context["current_date"] = date.today()
    return render(request, "payroll/settings/nbc_exchange_calendar.html", context)


@login_required
@hx_request_required
@permission_required("payroll.add_filingstatus")
def create_filing_status(request):
    """
    Create a filing status record for tax bracket based on user input.

    If the request method is POST and the form data is valid, save the filing status form
    and redirect to the create-filing-status page.

    """
    filing_status_form = FilingStatusForm()
    if request.method == "POST":
        filing_status_form = FilingStatusForm(request.POST)
        if filing_status_form.is_valid():
            filing_status_form.save()
            messages.success(request, _("Filing status created successfully "))
            filing_status_form = FilingStatusForm()
            if len(FilingStatus.objects.filter()) == 1:
                return HorillaRedirect(request)
    return render(
        request,
        "payroll/tax/filing_status_creation.html",
        {
            "form": filing_status_form,
        },
    )


@login_required
@hx_request_required
@permission_required("payroll.change_filingstatus")
def update_filing_status(request, filing_status_id):
    """
    Update an existing filing status record based on user input.

    If the request method is POST and the form data is valid, update the filing status form
    and redirect to the update-filing-status page.

    :param tax_bracket_id: The ID of the filing status to update.
    """
    filing_status = FilingStatus.find(filing_status_id)
    if not filing_status:
        messages.error(request, _("Filing status not found"))
        return HorillaRedirect(request)
    filing_status_form = FilingStatusForm(instance=filing_status)
    if request.method == "POST":
        filing_status_form = FilingStatusForm(request.POST, instance=filing_status)
        if filing_status_form.is_valid():
            filing_status_form.save()
            messages.success(request, _("Filing status updated successfully."))
    return render(
        request,
        "payroll/tax/filing_status_edit.html",
        {
            "form": filing_status_form,
        },
    )


@login_required
@hx_request_required
@permission_required("payroll.delete_filingstatus")
def filing_status_delete(request, filing_status_id):
    """
    Delete a filing status.

    This view deletes a filing status with the given `filing_status_id` from the
    database and redirects to the filing status view.

    """
    try:
        filing_status = FilingStatus.find(filing_status_id)
        if filing_status:
            try:
                filing_status.delete()
                messages.info(request, _("Filing status successfully deleted."))
            except ProtectedError:
                messages.error(
                    request,
                    _("Filing status is in use by tax brackets. Remove them first."),
                )
        else:
            messages.error(request, _("This filing status was not found."))
    except Exception as e:
        messages.error(
            request, _("An error occurred while trying to delete the filing status.")
        )
    if not FilingStatus.objects.exists():
        return HorillaRedirect(request)
    return redirect(filing_status_search)


@login_required
@hx_request_required
@permission_required("payroll.view_filingstatus")
def filing_status_search(request):
    """
    Display the filing status search view.

    This view handles the search functionality for filing statuses. It retrieves
    the search term from the GET parameters, filters the FilingStatus objects
    based on the search term, and renders the 'payroll/tax/filing_status_list.html'
    template with the filtered filing statuses.
    """
    search = request.GET.get("search") if request.GET.get("search") else ""
    status = FilingStatus.objects.filter(filing_status__icontains=search)
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    get_key_instances(FilingStatus, data_dict)
    context = {
        "status": status,
        "pd": previous_data,
        "filter_dict": data_dict,
    }
    return render(request, "payroll/tax/filing_status_list.html", context)


@login_required
@hx_request_required
@permission_required("payroll.view_taxbracket")
def tax_bracket_list(request, filing_status_id):
    """
    Display a list of tax brackets for a specific filing status.

    This view retrieves all tax brackets associated with the given `filing_status_id`
    and renders them in the "tax_bracket_view.html" template.

    Args:
        request: The HTTP request object.
        filing_status_id: The ID of the filing status for which to display tax brackets.

    Returns:
        The rendered "tax_bracket_view.html" template with the tax brackets for the
        specified filing status.
    """
    filing_status = FilingStatus.objects.get(id=filing_status_id)
    tax_brackets = TaxBracket.objects.filter(
        filing_status_id=filing_status_id
    ).order_by("max_income")
    context = {"tax_brackets": tax_brackets, "filing_status": filing_status}
    return render(request, "payroll/tax/tax_bracket_view.html", context)


@login_required
@hx_request_required
@permission_required("payroll.add_taxbracket")
def create_tax_bracket(request, filing_status_id):
    """
    Create a tax bracket record for federal tax calculation based on user input.

    If the request method is POST and the form data is valid, save the tax bracket form
    and redirect to the tax-bracket-create page.

    """
    tax_bracket_form = TaxBracketForm(initial={"filing_status_id": filing_status_id})
    context = {
        "form": tax_bracket_form,
        "filing_status_id": filing_status_id,
    }
    if request.method == "POST":
        tax_bracket_form = TaxBracketForm(
            request.POST, initial={"filing_status_id": filing_status_id}
        )
        if tax_bracket_form.is_valid():
            max_income = tax_bracket_form.cleaned_data.get("max_income")
            if not max_income:
                messages.info(request, _("The maximum income will be infinite"))
                tax_bracket_form.instance.max_income = math.inf
            tax_bracket_form.save()
            messages.success(request, _("The tax bracket was created successfully."))
            return redirect(create_tax_bracket, filing_status_id=filing_status_id)

        context["form"] = tax_bracket_form

    return render(request, "payroll/tax/tax_bracket_creation.html", context)


@login_required
@hx_request_required
@permission_required("payroll.change_taxbracket")
def update_tax_bracket(request, tax_bracket_id):
    """
    Update an existing tax bracket record based on user input.

    If the request method is POST and the form data is valid, update the tax bracket form
    and redirect to the tax-bracket-create page.

    :param tax_bracket_id: The ID of the tax bracket to update.
    """
    tax_bracket = TaxBracket.find(tax_bracket_id)
    if tax_bracket:
        filing_status_id = tax_bracket.filing_status_id.id
        tax_bracket_form = TaxBracketForm(instance=tax_bracket)
        if request.method == "POST":
            tax_bracket_form = TaxBracketForm(request.POST, instance=tax_bracket)
            if tax_bracket_form.is_valid():
                max_income = tax_bracket_form.cleaned_data.get("max_income")
                if not max_income:
                    messages.info(request, _("The maximum income will be infinite"))
                    tax_bracket_form.instance.max_income = math.inf
                tax_bracket_form.save()
                messages.success(
                    request, _("The tax bracket has been updated successfully.")
                )

        context = {
            "form": tax_bracket_form,
            "filing_status_id": filing_status_id,
        }
        return render(request, "payroll/tax/tax_bracket_edit.html", context)
    messages.error(request, _("Tax bracket not found"))
    return HorillaRedirect(request)


@login_required
@hx_request_required
@permission_required("payroll.delete_taxbracket")
def delete_tax_bracket(request, tax_bracket_id):
    """
    Delete an existing tax bracket record.

    Retrieve the tax bracket with the specified ID and delete it from the database.
    Then, redirect to the tax-bracket-create page.

    :param tax_bracket_id: The ID of the tax bracket to delete.
    """
    tax_bracket = TaxBracket.find(tax_bracket_id)
    filing_status_id = (
        tax_bracket.filing_status_id.id
        if tax_bracket and tax_bracket.delete()
        else None
    )
    if filing_status_id:
        messages.success(request, _("Tax bracket successfully deleted."))
    else:
        messages.error(request, _("Tax bracket not found"))
    return (
        redirect(tax_bracket_list, filing_status_id=filing_status_id)
        if filing_status_id
        else HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    )


@login_required
@permission_required("payroll.change_taxbracket")
def update_py_code(request, pk):
    """
    Ajax method to update python code of filing status
    """
    code = request.POST.get("code")
    if not code:
        messages.error(request, _("Missing required parameter"))
        return JsonResponse({"message": "Missing required parameter: code"}, status=400)
    filing = FilingStatus.find(pk)
    if not filing:
        messages.error(request, _("Filing status not found"))
        return JsonResponse({"message": "Filing status not found"}, status=404)

    try:
        validate_tax_code(code)
    except TaxCodeValidationError as exc:
        messages.error(request, _("Invalid tax code"))
        return JsonResponse({"message": str(exc)}, status=400)

    if not filing.python_code == code:
        filing.python_code = code
        filing.save()
        messages.success(request, _("Python code saved successfully!"))
    return JsonResponse({"message": "success"})
