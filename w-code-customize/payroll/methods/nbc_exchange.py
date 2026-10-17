"""
nbc_exchange.py

Automatic exchange-rate synchronisation with the National Bank of Cambodia
(NBC).

Every month the system uses the official NBC rate of the **15th** of the
month:

- The 15th is a working day (Monday - Friday, not a public holiday) -> the
  rate of the 15th.
- The 15th is a Saturday                       -> the rate of Friday the 14th.
- The 15th is a Sunday                         -> the rate of Friday the 13th.
- The 15th is a Cambodian public holiday       -> the rate of the closest
  working day before it (NBC publishes nothing on public holidays either,
  e.g. 15 October 2026 is the Commemoration Day of King's Father).

(The rate is never taken from a weekend or a public holiday itself - only
working days, Monday to Friday outside the national public-holiday calendar,
are used. See :mod:`payroll.methods.cambodia_calendar`.)

The fetched rate is written into ``PayrollSettings.usd_to_khr_rate``, which is
exactly the value used by the Cambodia salary tax / NSSF pension calculation
(Payroll -> Salary Tax -> Exchange Rate). Updating the exchange rate here
therefore updates the payroll salary-tax calculation automatically. A history
of every applied rate is kept in the ``NBCExchangeRate`` model.

IMPORTANT: by default the automatic monthly fetch is OFF
(``PayrollSettings.auto_fetch_nbc_rate`` = False): HR maintains the exchange
rate MANUALLY (Settings -> General -> Exchange Rate card) and
:func:`ensure_monthly_nbc_rate` never overwrites it. Switching the
"Automatic monthly NBC fetch" toggle ON re-enables the monthly application.

The Settings -> General "Exchange Rate" card additionally shows the official
rate of the 15th and every rate NBC published during the month (see
:func:`get_nbc_rate_panel_context`). That month list is served from a short
lived cache so opening the settings page does not query NBC every time.
"""

import calendar
import logging
from datetime import date, timedelta

import requests
from django.core.cache import cache
from django.utils import timezone

from payroll.methods.cambodia_calendar import is_cambodia_public_holiday
from payroll.models.tax_models import NBCExchangeRate, PayrollSettings

logger = logging.getLogger(__name__)

# Frankfurter exposes the official NBC reference rates as a provider feed
# (no API key required, free for commercial use).
NBC_EXCHANGE_API_URL = "https://api.frankfurter.dev/v2/providers/nbc/rates"

# The day of the month the NBC rate is applied on.
NBC_RATE_DAY = 15

# Max number of days to look back from the requested day (the 15th) when it
# falls on a weekend - a Sunday 15th means Friday the 13th is the working day,
# so this window is plenty.
NBC_MAX_LOOKBACK_DAYS = 7

# Hard safety cap on the fetched rate (guards against API glitches).
NBC_RATE_MIN = 1000.0
NBC_RATE_MAX = 100000.0

# NBC is an external HTTP service: never keep a request thread waiting for
# long, and cache the monthly rate list so the Settings -> General card does
# not query NBC again on every page view.
NBC_REQUEST_TIMEOUT = 10  # seconds
NBC_CACHE_KEY_PREFIX = "payroll:nbc_exchange:month"
NBC_CACHE_TIMEOUT = 60 * 60  # 1 hour


def _is_weekend(day: date) -> bool:
    """Saturday (5) or Sunday (6)."""
    return day.weekday() >= 5


def _is_non_working_day(day: date) -> bool:
    """Weekend (Saturday / Sunday) or Cambodian public holiday."""
    return _is_weekend(day) or is_cambodia_public_holiday(day)


def get_working_day_for_date(requested: date) -> date:
    """
    Resolve ``requested`` (usually the 15th of a month) to a working day.

    Saturday, Sunday and Cambodian public holidays are NOT working days in
    Cambodia, so if the 15th falls on one of them the closest working day
    BEFORE it is returned (a Saturday rolls back to Friday the 14th, a Sunday
    to Friday the 13th, a public holiday to the working day before it - e.g.
    Thursday 15 October 2026, the Commemoration Day of King's Father, resolves
    to Wednesday 14 October 2026).
    """
    day = requested
    for _ in range(NBC_MAX_LOOKBACK_DAYS):
        if not _is_non_working_day(day):
            return day
        day = day - timedelta(days=1)
    return day


def _fetch_nbc_rates(from_date: date, to_date: date, timeout=NBC_REQUEST_TIMEOUT):
    """
    Return ``[(date, rate), ...]`` of official NBC USD -> KHR rates for the
    inclusive date range, oldest first. Raises on network / API errors.
    """
    response = requests.get(
        NBC_EXCHANGE_API_URL,
        params={
            "base": "USD",
            "quotes": "KHR",
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    rows = data if isinstance(data, list) else data.get("rates") or []
    rates = []
    for row in rows:
        try:
            row_date = date.fromisoformat(str(row.get("date")))
            row_rate = float(row.get("rate"))
        except (TypeError, ValueError):
            continue
        rates.append((row_date, row_rate))
    rates.sort(key=lambda item: item[0])
    return rates


def _month_cache_key(month: date) -> str:
    """Cache key of the NBC rate list of the month that contains ``month``."""
    return f"{NBC_CACHE_KEY_PREFIX}:{month:%Y-%m}"


def _drop_stale_month_cache(applied_day: date, applied_rate=None) -> None:
    """
    Drop the cached month list when it does not match the rate that was just
    applied, so the NBC panel of the Settings -> General card can never show an
    outdated list.

    The cache is kept when it already holds that exact date and rate (the
    normal case), which avoids an extra request to NBC right after a successful
    fetch.
    """
    key = _month_cache_key(applied_day)
    cached = cache.get(key) or {}
    if not cached:
        return

    cached_rates = {day: rate for day, rate in cached.get("rates", [])}
    stored_rate = cached_rates.get(applied_day.isoformat())
    if stored_rate is None or (
        applied_rate is not None and float(stored_rate) != float(applied_rate)
    ):
        cache.delete(key)


def get_nbc_month_rates(month: date = None, refresh: bool = False) -> dict:
    """
    Official NBC USD -> KHR rates published during ``month``.

    The list is cached for :data:`NBC_CACHE_TIMEOUT` seconds because the
    Settings -> General card reads it every time the page is opened, while NBC
    itself only publishes one reference rate per working day.

    Args:
        month (date): Any date inside the wanted month (default: today).
        refresh (bool): Ignore the cache and query NBC again.

    Returns:
        dict: {
            "rates": [(date, rate), ...]   oldest first, working days only,
            "fetched_at": datetime | None,
            "available": bool,     False when NBC could not be reached and no
                                   cached list exists either,
            "from_cache": bool,
            "message": str,        user facing note when not available,
        }
    """
    month = month or date.today()
    key = _month_cache_key(month)

    cached = None if refresh else cache.get(key)
    if cached:
        return {
            "rates": [
                (date.fromisoformat(day), rate) for day, rate in cached["rates"]
            ],
            "fetched_at": cached.get("fetched_at"),
            "available": True,
            "from_cache": True,
            "message": "",
        }

    last_day = calendar.monthrange(month.year, month.month)[1]
    try:
        rates = _fetch_nbc_rates(
            date(month.year, month.month, 1),
            date(month.year, month.month, last_day),
        )
    except (requests.RequestException, ValueError) as exc:
        logger.error("NBC exchange-rate fetch failed: %s", exc)
        # Fall back to the last known good list so the card can still show
        # something useful while NBC is unreachable.
        cached = cache.get(key) or {}
        return {
            "rates": [
                (date.fromisoformat(day), rate)
                for day, rate in cached.get("rates", [])
            ],
            "fetched_at": cached.get("fetched_at"),
            "available": False,
            "from_cache": bool(cached),
            "message": _message_could_not_connect(),
        }

    fetched_at = timezone.now()
    cache.set(
        key,
        {
            "rates": [[day.isoformat(), rate] for day, rate in rates],
            "fetched_at": fetched_at,
        },
        NBC_CACHE_TIMEOUT,
    )
    return {
        "rates": rates,
        "fetched_at": fetched_at,
        "available": True,
        "from_cache": False,
        "message": "",
    }


def get_official_nbc_rate(month: date = None, refresh: bool = False) -> dict:
    """
    The official NBC rate of the 15th of ``month``.

    Cambodian payroll uses the official NBC rate of the 15th. NBC publishes a
    reference rate only on working days (Monday - Friday, never on a Cambodian
    public holiday), so when the 15th is a weekend day or a public holiday the
    rate of the closest working day BEFORE it is the official one (see
    :func:`get_working_day_for_date`).

    Returns:
        dict: {
            "requested_date": date,      the 15th itself,
            "effective_date": date,      the working day it resolves to,
            "published_date": date | None,
            "rate": float | None,        None while the 15th is not published,
            "available": bool,           False when NBC could not be reached,
            "from_cache": bool,
            "fetched_at": datetime | None,
            "message": str,
            "rates": [(date, rate), ...] the whole month, oldest first,
        }
    """
    month = month or date.today()
    requested = date(month.year, month.month, NBC_RATE_DAY)
    effective = get_working_day_for_date(requested)

    data = get_nbc_month_rates(month=month, refresh=refresh)

    # Same window as apply_nbc_rate_for_date: the 15th is only ever matched
    # with a rate published on / shortly before that working day, never with
    # an older rate of the same month.
    window_start = max(
        effective - timedelta(days=NBC_MAX_LOOKBACK_DAYS),
        effective.replace(day=1),
    )

    published_date = None
    rate = None
    for day, published_rate in reversed(data["rates"]):
        if day < window_start or day > effective or _is_non_working_day(day):
            continue
        if not (NBC_RATE_MIN <= published_rate <= NBC_RATE_MAX):
            continue
        published_date, rate = day, published_rate
        break

    message = data["message"]
    if rate is None and not message:
        message = _message_no_rate_found(requested)

    return {
        "requested_date": requested,
        "effective_date": effective,
        "published_date": published_date,
        "rate": rate,
        "available": data["available"],
        "from_cache": data["from_cache"],
        "fetched_at": data["fetched_at"],
        "message": message,
        "rates": data["rates"],
    }


def get_nbc_rate_panel_context(month: date = None, refresh: bool = False) -> dict:
    """
    Context of the NBC panel of the Settings -> General "Exchange Rate" card.

    The panel shows the official rate of the 15th prominently, every rate NBC
    published during the month and whether the official rate is the one that
    is currently applied to the payroll / salary-tax calculation.

    Args:
        month (date): The month to display (default: the current month).
        refresh (bool): Ignore the cache and query NBC again.

    Returns:
        dict: Context used by ``payroll/settings/nbc_exchange_panel.html``.
    """
    from payroll.methods.tax_calc import get_usd_to_khr_rate

    today = date.today()
    month = month or today
    month = date(month.year, month.month, 1)

    official = get_official_nbc_rate(month=month, refresh=refresh)
    active_rate = get_usd_to_khr_rate()
    official_rate = official["rate"]

    applied = (
        active_rate is not None
        and official_rate is not None
        and round(float(active_rate), 2) == round(float(official_rate), 2)
    )

    published_date = official["published_date"]
    rows = [
        {
            "date": day,
            "rate": rate,
            "is_official": published_date is not None and day == published_date,
        }
        for day, rate in official["rates"]
    ]

    return {
        "nbc_month": month,
        "nbc_month_value": f"{month:%Y-%m}",
        "nbc_is_current_month": (month.year, month.month)
        == (today.year, today.month),
        "nbc_rates": rows,
        "nbc_official_rate": official_rate,
        "nbc_official_published_date": published_date,
        "nbc_official_effective_date": official["effective_date"],
        "nbc_official_requested_date": official["requested_date"],
        "nbc_official_applied": applied,
        "nbc_available": official["available"],
        "nbc_from_cache": official["from_cache"],
        "nbc_fetched_at": official["fetched_at"],
        "nbc_message": official["message"],
    }


def apply_exchange_rate(
    rate,
    effective_date=None,
    source="manual",
    requested_date=None,
):
    """
    Store a rate in the history table and make it the ACTIVE exchange rate
    used by the payroll salary-tax calculation.
    """
    rate = float(rate)
    if rate <= 0:
        raise ValueError("Exchange rate must be greater than zero.")
    if effective_date is None:
        effective_date = date.today()

    existing = NBCExchangeRate.objects.filter(effective_date=effective_date).first()
    if existing:
        existing.rate = rate
        existing.source = source
        existing.requested_date = requested_date
        existing.save()
        record = existing
    else:
        record = NBCExchangeRate.objects.create(
            requested_date=requested_date,
            effective_date=effective_date,
            rate=rate,
            source=source,
        )

    # The active rate lives on PayrollSettings and is read by every salary /
    # tax / pension calculation, so updating it updates the salary tax
    # automatically. Exactly one active row is kept (same behaviour as the
    # Salary Tax page's "Update" form).
    instance = PayrollSettings.objects.filter(usd_to_khr_rate__isnull=False).first()
    if instance is None:
        instance = PayrollSettings.objects.first()
    if instance is None:
        PayrollSettings.objects.create(usd_to_khr_rate=rate)
    else:
        instance.usd_to_khr_rate = rate
        instance.save()

    return record


def apply_nbc_rate_for_date(requested: date = None):
    """
    Fetch the official NBC rate for ``requested`` (default: the 15th of the
    current month), resolving weekends to the closest previous working day,
    and make it the active exchange rate.

    Returns:
        tuple: ``(record, message)`` where ``record`` is the saved
        ``NBCExchangeRate`` (or ``None`` on failure) and ``message`` is a
        user-facing message string describing the result.
    """
    if requested is None:
        requested = date.today().replace(day=NBC_RATE_DAY)
    if requested.day != NBC_RATE_DAY:
        requested = requested.replace(day=NBC_RATE_DAY)

    effective = get_working_day_for_date(requested)
    from_date = max(
        effective - timedelta(days=NBC_MAX_LOOKBACK_DAYS),
        effective.replace(day=1),
    )

    try:
        rates = _fetch_nbc_rates(from_date, requested)
    except requests.RequestException as exc:
        logger.error("NBC exchange-rate fetch failed: %s", exc)
        return None, _message_could_not_connect()
    except ValueError as exc:
        logger.error("NBC exchange-rate response invalid: %s", exc)
        return None, _message_could_not_connect()

    # NBC only publishes rates on working days: walk back from the resolved
    # day (weekends and public holidays are never used) until a published rate
    # is found.
    for day, rate in reversed(rates):
        if _is_non_working_day(day):
            continue
        if not (NBC_RATE_MIN <= rate <= NBC_RATE_MAX):
            continue
        if day > effective:
            continue
        record = apply_exchange_rate(
            rate=rate,
            effective_date=day,
            source="nbc",
            requested_date=requested,
        )
        _drop_stale_month_cache(day, rate)
        return (
            record,
            (
                f"Exchange rate updated from NBC: 1 USD = {rate} KHR "
                f"(official rate of {day:%d %B %Y})."
            ),
        )

    return None, _message_no_rate_found(requested)


def _message_could_not_connect():
    return (
        "Could not connect to the National Bank of Cambodia exchange-rate "
        "service. Please try again later."
    )


def _message_no_rate_found(requested):
    return (
        "No official NBC exchange rate was published for the working day "
        f"around {requested:%d %B %Y}. Please try again later."
    )


# ============================================================
# NFFS EXCHANGE RATE (Laos National Social Security Fund)
# ============================================================

# NFFS API endpoint - configure with the actual NFFS/Laos exchange rate API
# when one is available. Until then, the NFFS rate is maintained manually.
NFFS_EXCHANGE_API_URL = ""

# The day of the month the NFFS rate is applied on.
NFFS_RATE_DAY = 15

# Max number of days to look back from the requested day (the 15th).
NFFS_MAX_LOOKBACK_DAYS = 7

# Hard safety cap on the fetched rate.
NFFS_RATE_MIN = 100.0
NFFS_RATE_MAX = 1_000_000.0

NFFS_REQUEST_TIMEOUT = 10  # seconds
NFFS_CACHE_KEY_PREFIX = "payroll:nffs_exchange:month"
NFFS_CACHE_TIMEOUT = 60 * 60  # 1 hour


def apply_nffs_rate(rate, effective_date=None, source="manual", requested_date=None):
    """Store an NFFS exchange rate and make it active.

    Updates PayrollSettings.nffs_exchange_rate and nffs_effective_date, and
    records the change in the NBCExchangeRate history.

    Returns the created NBCExchangeRate record.
    """
    from payroll.models.tax_models import NBCExchangeRate, PayrollSettings

    if rate is None or rate <= 0:
        raise ValueError("NFFS exchange rate must be greater than zero.")
    if not (NFFS_RATE_MIN <= rate <= NFFS_RATE_MAX):
        raise ValueError(f"NFFS exchange rate {rate} is out of bounds.")

    effective_date = effective_date or date.today()

    settings_row = (
        PayrollSettings._base_manager.order_by("company_id", "id").first()
        or PayrollSettings.objects.create()
    )
    settings_row.nffs_exchange_rate = rate
    settings_row.nffs_effective_date = effective_date
    settings_row.save()

    record = NBCExchangeRate.objects.create(
        rate=rate,
        effective_date=effective_date,
        source=source,
        requested_date=requested_date or date.today(),
    )
    return record


def _fetch_nffs_rates(from_date, to_date, timeout=NFFS_REQUEST_TIMEOUT):
    """Fetch NFFS exchange rates from the configured API.

    Returns a list of (date, rate) tuples. Raises requests.RequestException
    on connection failure or ValueError on invalid response.
    """
    if not NFFS_EXCHANGE_API_URL:
        raise ValueError("NFFS exchange API URL is not configured.")

    params = {"from": from_date.isoformat(), "to": to_date.isoformat()}
    response = requests.get(NFFS_EXCHANGE_API_URL, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    rates = []
    for item in data.get("rates", []):
        try:
            day = date.fromisoformat(item["date"])
            rate = float(item["rate"])
            rates.append((day, rate))
        except (KeyError, ValueError, TypeError):
            continue

    return sorted(rates)


def apply_nffs_rate_for_date(requested=None):
    """Fetch and apply the official NFFS exchange rate for the given date.

    Returns (record, message) tuple, or (None, reason) if no rate could be
    fetched.
    """
    requested = requested or date.today().replace(day=NFFS_RATE_DAY)

    effective = get_working_day_for_date(requested)

    from_date = max(
        effective - timedelta(days=NFFS_MAX_LOOKBACK_DAYS),
        effective.replace(day=1),
    )

    try:
        rates = _fetch_nffs_rates(from_date, requested)
    except requests.RequestException as exc:
        logger.error("NFFS exchange-rate fetch failed: %s", exc)
        return None, _message_nffs_could_not_connect()
    except ValueError as exc:
        logger.error("NFFS exchange-rate response invalid: %s", exc)
        return None, _message_nffs_could_not_connect()

    for day, rate in reversed(rates):
        if _is_weekend(day):
            continue
        if not (NFFS_RATE_MIN <= rate <= NFFS_RATE_MAX):
            continue
        if day > effective:
            continue
        record = apply_nffs_rate(
            rate=rate, effective_date=day, source="nffs", requested_date=requested
        )
        return (
            record,
            (
                f"NFFS exchange rate updated: 1 USD = {rate} NFFS "
                f"(official rate of {day:%d %B %Y})."
            ),
        )

    return None, _message_no_nffs_rate_found(requested)


def _message_nffs_could_not_connect():
    return (
        "Could not connect to the NFFS exchange-rate service. "
        "Please try again later."
    )


def _message_no_nffs_rate_found(requested):
    return (
        "No official NFFS exchange rate was published for the working day "
        f"around {requested:%d %B %Y}. Please try again later."
    )


def ensure_monthly_nffs_rate(today=None):
    """Automatic (scheduler) entrypoint for NFFS exchange rate.

    ONLY runs when HR switched the "Automatic monthly NFFS fetch" toggle ON.
    Returns (record, message) or (None, reason).
    """
    from payroll.models.tax_models import NBCExchangeRate, PayrollSettings

    settings_row = (
        PayrollSettings._base_manager.order_by("company_id", "id").first()
    )
    if settings_row is None or not settings_row.auto_fetch_nffs_rate:
        return None, "automatic NFFS fetch disabled (exchange rate is manual)"

    today = today or date.today()
    effective = get_working_day_for_date(today.replace(day=NFFS_RATE_DAY))

    if today < effective:
        return None, "not due yet"
    if NBCExchangeRate.objects.filter(
        effective_date=effective, source="nffs"
    ).exists():
        return None, "already fetched"

    return apply_nffs_rate_for_date(today.replace(day=NFFS_RATE_DAY))


def ensure_monthly_nbc_rate(today: date = None):
    """
    Automatic (scheduler) entrypoint.

    ONLY runs when HR switched the "Automatic monthly NBC fetch" toggle ON
    (Settings -> General -> Exchange Rate card, PayrollSettings.auto_fetch_nbc_rate).
    By default the toggle is OFF: HR maintains the exchange rate manually and
    this job must NEVER overwrite a manually entered rate.

    When enabled, it only acts when the working day for this month's 15th has
    arrived (or passed) AND no NBC rate has been recorded for that working day
    yet, so it is safe to run it every few hours. Returns the same
    ``(record, message)`` tuple as :func:`apply_nbc_rate_for_date`, or
    ``(None, reason)`` when nothing had to be done.
    """
    from payroll.models.tax_models import NBCExchangeRate, PayrollSettings

    # Manual-mode guard: unless HR explicitly opted in to the automatic
    # monthly fetch, the exchange rate is input manually and the scheduler
    # leaves it untouched.
    settings_row = (
        PayrollSettings._base_manager.order_by("company_id", "id").first()
    )
    if settings_row is None or not settings_row.auto_fetch_nbc_rate:
        return None, "automatic NBC fetch disabled (exchange rate is manual)"

    today = today or date.today()
    effective = get_working_day_for_date(today.replace(day=NBC_RATE_DAY))

    if today < effective:
        return None, "not due yet"
    if NBCExchangeRate.objects.filter(effective_date=effective).exists():
        return None, "already fetched"

    return apply_nbc_rate_for_date(today.replace(day=NBC_RATE_DAY))

