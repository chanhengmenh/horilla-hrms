"""
cambodia_calendar.py

Cambodian (Khmer) public-holiday calendar used by the Settings -> General
"Exchange Rate Calendar" (see
``payroll.views.tax_views._build_exchange_rate_calendar``).

Cambodia's public holidays are announced by Royal / Sub-decree every year and
the lunar festivals (Khmer New Year, Visak Bochea, Pchum Ben, Bon Om Touk ...)
move with the Buddhist calendar, so they cannot be derived from a fixed rule -
they are kept here as an explicit ``year -> [(date, name), ...]`` table.

Only the weekend rule (Saturday / Sunday) is fixed; everything else is data:

- Years absent from the table simply contribute no built-in holiday - the
  holidays configured in Settings -> Holidays (``base.Holidays``) are merged
  in on top by the calendar view, so company holidays always show up too.
- Dates were cross-checked against two independent 2025 - 2027 calendars
  (the lunar ones are announced yearly and marked tentative until then).
"""

from datetime import date

# Official Cambodian public holidays per year. Lunar festivals move every
# year, so each year is listed explicitly. Two names on the same day are two
# entries (e.g. 1 May 2026 is both Visak Bochea Day and Labour Day).
CAMBODIA_PUBLIC_HOLIDAYS = {
    2025: [
        (date(2025, 1, 1), "New Year"),
        (date(2025, 1, 7), "Victory over Genocide Day"),
        (date(2025, 3, 8), "International Women's Day"),
        (date(2025, 4, 14), "Khmer New Year Day (Day 1)"),
        (date(2025, 4, 15), "Khmer New Year Day (Day 2)"),
        (date(2025, 4, 16), "Khmer New Year Day (Day 3)"),
        (date(2025, 5, 1), "Labour Day"),
        (date(2025, 5, 11), "Visak Bochea Day"),
        (date(2025, 5, 14), "King's Birthday"),
        (date(2025, 5, 15), "Royal Plowing Ceremony"),
        (date(2025, 6, 18), "King's Mother's Birthday"),
        (date(2025, 9, 21), "Pchum Ben Festival"),
        (date(2025, 9, 22), "Pchum Ben Festival"),
        (date(2025, 9, 23), "Pchum Ben Festival"),
        (date(2025, 9, 24), "Constitutional Day"),
        (date(2025, 10, 15), "Commemoration Day of King's Father"),
        (date(2025, 10, 29), "King's Coronation Day"),
        (date(2025, 11, 4), "Water Festival Ceremony (Day 1)"),
        (date(2025, 11, 5), "Water Festival Ceremony (Day 2)"),
        (date(2025, 11, 6), "Water Festival Ceremony (Day 3)"),
        (date(2025, 11, 9), "Independence Day"),
        (date(2025, 12, 29), "Peace Day"),
    ],
    2026: [
        (date(2026, 1, 1), "New Year"),
        (date(2026, 1, 7), "Victory over Genocide Day"),
        (date(2026, 3, 8), "International Women's Day"),
        (date(2026, 4, 14), "Khmer New Year Day (Day 1)"),
        (date(2026, 4, 15), "Khmer New Year Day (Day 2)"),
        (date(2026, 4, 16), "Khmer New Year Day (Day 3)"),
        (date(2026, 5, 1), "Visak Bochea Day"),
        (date(2026, 5, 1), "Labour Day"),
        (date(2026, 5, 5), "Royal Plowing Ceremony"),
        (date(2026, 5, 14), "King's Birthday"),
        (date(2026, 6, 18), "King's Mother's Birthday"),
        (date(2026, 9, 24), "Constitutional Day"),
        (date(2026, 10, 10), "Pchum Ben Festival"),
        (date(2026, 10, 11), "Pchum Ben Festival"),
        (date(2026, 10, 12), "Pchum Ben Festival"),
        (date(2026, 10, 15), "Commemoration Day of King's Father"),
        (date(2026, 10, 29), "King's Coronation Day"),
        (date(2026, 11, 9), "Independence Day"),
        (date(2026, 11, 23), "Water Festival Ceremony (Day 1)"),
        (date(2026, 11, 24), "Water Festival Ceremony (Day 2)"),
        (date(2026, 11, 25), "Water Festival Ceremony (Day 3)"),
        (date(2026, 12, 29), "Peace Day"),
    ],
    2027: [
        (date(2027, 1, 1), "New Year"),
        (date(2027, 1, 7), "Victory over Genocide Day"),
        (date(2027, 3, 8), "International Women's Day"),
        # Lunar dates below are tentative until officially announced.
        (date(2027, 4, 14), "Khmer New Year Day (Day 1)"),
        (date(2027, 4, 15), "Khmer New Year Day (Day 2)"),
        (date(2027, 4, 16), "Khmer New Year Day (Day 3)"),
        (date(2027, 5, 1), "Labour Day"),
        (date(2027, 5, 14), "King's Birthday"),
        (date(2027, 6, 18), "King's Mother's Birthday"),
        (date(2027, 9, 24), "Constitutional Day"),
        (date(2027, 10, 15), "Commemoration Day of King's Father"),
        (date(2027, 10, 29), "King's Coronation Day"),
        (date(2027, 11, 9), "Independence Day"),
        (date(2027, 12, 29), "Peace Day"),
    ],
}


def get_cambodia_public_holidays(year: int) -> list:
    """
    All built-in Cambodian public holidays of ``year``.

    Returns:
        list: ``[(date, name), ...]`` sorted by date, empty when the year is
        not in :data:`CAMBODIA_PUBLIC_HOLIDAYS`.
    """
    return sorted(CAMBODIA_PUBLIC_HOLIDAYS.get(year, ()))


def get_cambodia_holiday_names(day: date) -> list:
    """
    Public-holiday names falling exactly on ``day``.

    Returns:
        list: e.g. ``["Pchum Ben Festival"]`` or ``[]`` when ``day`` is not a
        national public holiday.
    """
    return [name for holiday_date, name in CAMBODIA_PUBLIC_HOLIDAYS.get(day.year, ()) if holiday_date == day]


def is_cambodia_public_holiday(day: date) -> bool:
    """Whether ``day`` is a Cambodian national public holiday."""
    return bool(get_cambodia_holiday_names(day))
