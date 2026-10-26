"""Dynamic Indian public holiday calendar used by attendance and reports.

Sundays are handled separately as weekly offs. The ``holidays`` package supplies
India-wide public holidays for the selected year, including movable observances.
The small fallback list keeps the three fixed national holidays available if the
package has not been installed yet.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict

try:
    import holidays as holiday_library
except ImportError:  # pragma: no cover - exercised only in incomplete installations
    holiday_library = None

FIXED_NATIONAL_HOLIDAYS = {
    (1, 26): "Republic Day",
    (8, 15): "Independence Day",
    (10, 2): "Mahatma Gandhi's Birthday",
}

# Government of India's 2026 gazetted holiday dates used as a fallback when the
# optional calendar dependency is unavailable. Movable dates for other years
# come from ``holidays`` rather than being hardcoded here.
INDIA_2026_FALLBACK = {
    date(2026, 1, 26): "Republic Day",
    date(2026, 3, 4): "Holi",
    date(2026, 3, 21): "Id-ul-Fitr",
    date(2026, 3, 26): "Ram Navami",
    date(2026, 3, 31): "Mahavir Jayanti",
    date(2026, 4, 3): "Good Friday",
    date(2026, 5, 1): "Buddha Purnima",
    date(2026, 5, 27): "Id-ul-Zuha (Bakrid)",
    date(2026, 6, 26): "Muharram",
    date(2026, 8, 15): "Independence Day",
    date(2026, 8, 26): "Milad-un-Nabi / Id-e-Milad",
    date(2026, 9, 4): "Janmashtami",
    date(2026, 10, 2): "Mahatma Gandhi's Birthday",
    date(2026, 10, 20): "Dussehra",
    date(2026, 11, 8): "Diwali (Deepavali)",
    date(2026, 11, 24): "Guru Nanak's Birthday",
    date(2026, 12, 25): "Christmas Day",
}


def _subdivision() -> str | None:
    value = os.getenv("HOLIDAY_SUBDIV", "").strip().upper()
    return value or None


@lru_cache(maxsize=128)
def india_public_holidays(year: int, subdivision: str | None = None) -> Dict[date, str]:
    """Return public holidays for a year, keyed by Gregorian date.

    Defaults to the India-wide calendar. Set ``HOLIDAY_SUBDIV=MH`` in ``.env``
    if PAZO wants to include Maharashtra-specific holidays as well.
    """
    if subdivision is None:
        subdivision = _subdivision()

    result: Dict[date, str] = {
        date(year, month, day): name
        for (month, day), name in FIXED_NATIONAL_HOLIDAYS.items()
    }
    if year == 2026 and not subdivision:
        result.update(INDIA_2026_FALLBACK)

    if holiday_library is not None:
        try:
            kwargs = {"years": [year], "observed": False, "language": "en"}
            if subdivision:
                kwargs["subdiv"] = subdivision
            country_calendar = holiday_library.country_holidays("IN", **kwargs)
            for holiday_date, name in country_calendar.items():
                if isinstance(holiday_date, datetime):
                    holiday_date = holiday_date.date()
                if isinstance(holiday_date, date) and holiday_date.year == year:
                    result[holiday_date] = str(name)
        except (TypeError, ValueError, NotImplementedError, OverflowError):
            # Preserve at least the fixed national holidays for an unsupported year.
            pass

    # PAZO-specific dates in app/custom_holidays.json override the generic list.
    # The supplied spreadsheet explicitly marks 31-Oct-2026 as PH.
    custom_file = Path(__file__).with_name("custom_holidays.json")
    try:
        custom_rows = json.loads(custom_file.read_text(encoding="utf-8"))
        for date_text, name in custom_rows.items():
            custom_date = date.fromisoformat(date_text)
            if custom_date.year == year:
                result[custom_date] = str(name)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass

    return dict(sorted(result.items()))


def is_week_off(day: date) -> bool:
    """Sundays are the weekly off day for every month and every year."""
    return day.weekday() == 6


def is_working_date(day: date) -> bool:
    """Whether an attendance mark is allowed for this date."""
    if is_week_off(day):
        return False
    return day not in india_public_holidays(day.year, _subdivision())


def day_type_map(days: list[date]) -> dict[date, str]:
    """Map dates to working, weekoff, or public_holiday for the monthly grid."""
    holidays_for_year = india_public_holidays(days[0].year, _subdivision()) if days else {}
    result = {}
    for day in days:
        if is_week_off(day):
            result[day] = "weekoff"
        elif day in holidays_for_year:
            result[day] = "public_holiday"
        else:
            result[day] = "working"
    return result
