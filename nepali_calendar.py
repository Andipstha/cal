"""
Nepali (Bikram Sambat) calendar mapping + Bigmart event rules.

IMPORTANT — production note:
This module ships with an ACCURATE, verified mapping for ONE month only
(Bhadra 2083 BS = Aug 17 - Sep 16, 2026 AD), which is enough to prove the
end-to-end system. BS month lengths vary year to year and are NOT computable
by a simple formula (they follow astronomical calculations published yearly
by Nepal's Panchang authorities). For full multi-year coverage, swap
BS_MONTH_TABLE below for real data from a maintained source, e.g.:
  - the `nepali_datetime` PyPI package (covers ~1970-2100 BS), or
  - a data table pulled from a maintained Nepali Patro API.
Do NOT hand-extend BS_MONTH_TABLE by guessing lengths — get it from a
verified source, since a wrong month length silently shifts every event
after it.
"""

import datetime as dt

# Each entry: (bs_year, bs_month, bs_month_name, gregorian_start_date, day_count)
BS_MONTH_TABLE = [
    (2083, 5, "Bhadra", dt.date(2026, 8, 17), 31),
]


def get_bs_month_window(bs_year: int, bs_month: int):
    """Return (month_name, gregorian_start, gregorian_end_inclusive) for a BS month."""
    for year, month, name, start, length in BS_MONTH_TABLE:
        if year == bs_year and month == bs_month:
            end = start + dt.timedelta(days=length - 1)
            return name, start, end
    raise ValueError(
        f"No BS month data for {bs_year}-{bs_month}. "
        "Extend BS_MONTH_TABLE with verified data (see module docstring)."
    )


def gregorian_to_bs_label(g_date: dt.date) -> str:
    """Best-effort BS date label for a Gregorian date, using loaded table entries."""
    for year, month, name, start, length in BS_MONTH_TABLE:
        end = start + dt.timedelta(days=length - 1)
        if start <= g_date <= end:
            bs_day = (g_date - start).days + 1
            return f"{name} {bs_day}, {year} BS"
    return g_date.strftime("%d %b %Y")  # fallback: just show the Gregorian date


def known_coverage():
    """Which Gregorian date ranges we can currently generate events for."""
    out = []
    for year, month, name, start, length in BS_MONTH_TABLE:
        end = start + dt.timedelta(days=length - 1)
        out.append((f"{name} {year} BS", start, end))
    return out


# ---------------------------------------------------------------------------
# Event rules (operate on Gregorian weekdays; BS is used only for labelling
# and for finding "last Wednesday of the BS month" per Bigmart's convention)
# ---------------------------------------------------------------------------

def build_event_schedule(bs_year: int, bs_month: int):
    """
    Returns a list of dicts: {date, event_type, bs_label}
    event_type in {big_wednesday, antim_budhabar, big_saturday}
    """
    _, start, end = get_bs_month_window(bs_year, bs_month)
    days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]

    wednesdays = [d for d in days if d.weekday() == 2]
    saturdays = [d for d in days if d.weekday() == 5]
    last_wednesday = max(wednesdays) if wednesdays else None

    schedule = []
    for d in wednesdays:
        event_type = "antim_budhabar" if d == last_wednesday else "big_wednesday"
        schedule.append({"date": d, "event_type": event_type, "bs_label": gregorian_to_bs_label(d)})
    for d in saturdays:
        schedule.append({"date": d, "event_type": "big_saturday", "bs_label": gregorian_to_bs_label(d)})

    schedule.sort(key=lambda e: e["date"])
    return schedule
