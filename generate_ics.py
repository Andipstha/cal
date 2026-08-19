#!/usr/bin/env python3
"""
Builds cal.ics from offers.json + the Big Wednesday / Antim Budhabar / Big
Saturday rules in nepali_calendar.py. Designed to be run by GitHub Actions
on every push to offers.json AND on a schedule (see workflow file), so the
published feed is always current without anyone needing to run this by hand.
"""

import json
import datetime as dt
import hashlib
from typing import Optional

from nepali_calendar import build_event_schedule, BS_MONTH_TABLE

OFFERS_FILE = "offers.json"
OUTPUT_FILE = "cal.ics"

DEFAULT_CONTENT = {
    "big_wednesday": {
        "summary": "BIG WEDNESDAY \U0001F6D2",
        "offer_title": "Big Wednesday — Storewide Savings",
        "details": "Check in-store and bigmart.com.np for this week's discounts.",
    },
    "antim_budhabar": {
        "summary": "ANTIM BUDHABAR \U0001F534",
        "offer_title": "Antim Budhabar — Month-End Mega Discount",
        "details": "Special month-end discounts. Check bigmart.com.np for details.",
    },
    "big_saturday": {
        "summary": "BIG SATURDAY \U0001F6CD\uFE0F",
        "offer_title": "Big Saturday — Weekend Special",
        "details": "Check in-store and bigmart.com.np for this week's discounts.",
    },
    "special_offer": {
        "summary": "SPECIAL OFFER \U0001F389",
        "offer_title": "Special Offer",
        "details": "Check bigmart.com.np for details.",
    },
}

# Event types that only exist when explicitly added via an override -- they
# have no automatic recurring schedule the way big_wednesday/big_saturday do.
ONE_OFF_EVENT_TYPES = {"special_offer"}

DEFAULT_STORES = "All Bigmart outlets, Kathmandu Valley"
LINK = "https://bigmart.com.np/offers"
TERMS = "T&C apply. While stocks last. See bigmart.com.np/terms for details."
# Fixed epoch used for DTSTAMP on events with no override, so identical
# content always hashes identically between runs (keeps git diffs clean and
# lets subscriber calendar apps see "nothing changed" when nothing changed).
DEFAULT_STAMP = "2026-01-01T00:00:00"


def fold_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def load_overrides():
    try:
        with open(OFFERS_FILE) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    index = {}
    for o in data.get("overrides", []):
        key = (o["event_date"], o["event_type"])
        index[key] = o
    return index


def build_vevent(event: dict, overrides: dict) -> Optional[str]:
    d = event["date"]
    event_type = event["event_type"]
    override = overrides.get((d.isoformat(), event_type))
    default = DEFAULT_CONTENT[event_type]

    if override and override.get("published") is False:
        return None

    offer_title = override["offer_title"] if override else default["offer_title"]
    details = override["details"] if override else default["details"]
    stores = override["stores"] if override else DEFAULT_STORES
    dtstamp_source = DEFAULT_STAMP if not override else override.get("_updated_at", DEFAULT_STAMP)

    uid = f"bigmart-{event_type.replace('_','-')}-{d.strftime('%Y%m%d')}@bigmart.com.np"
    dtstart = d.strftime("%Y%m%d")
    dtend = (d + dt.timedelta(days=1)).strftime("%Y%m%d")
    dtstamp = dt.datetime.fromisoformat(dtstamp_source).strftime("%Y%m%dT%H%M%SZ")

    description = fold_escape("\n".join([
        offer_title,
        f"Nepali date: {event['bs_label']}",
        details,
        f"Valid: {d.strftime('%d %b %Y')} only",
        f"Participating stores: {stores}",
        f"Details: {LINK}",
        TERMS,
    ]))

    return "\n".join([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{dtstart}",
        f"DTEND;VALUE=DATE:{dtend}",
        f"SUMMARY:{default['summary']}",
        f"DESCRIPTION:{description}",
        f"URL:{LINK}",
        f"LOCATION:{fold_escape(stores)}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Bigmart offer tomorrow \u2014 don't miss out!",
        "TRIGGER:-P1D",
        "END:VALARM",
        "END:VEVENT",
    ])


def main():
    overrides = load_overrides()

    all_events = []
    for bs_year, bs_month, _name, _start, _length in BS_MONTH_TABLE:
        all_events.extend(build_event_schedule(bs_year, bs_month))

    # One-off event types (e.g. special_offer) aren't part of any recurring
    # Wed/Sat rule -- they exist purely because an override for that exact
    # date was added, so pull them straight from offers.json instead of
    # from build_event_schedule.
    from nepali_calendar import gregorian_to_bs_label
    for (date_str, event_type), _override in overrides.items():
        if event_type in ONE_OFF_EVENT_TYPES:
            d = dt.date.fromisoformat(date_str)
            all_events.append({
                "date": d,
                "event_type": event_type,
                "bs_label": gregorian_to_bs_label(d),
            })

    vevents = [v for e in all_events if (v := build_vevent(e, overrides))]

    calendar = "\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Bigmart Nepal//Offer Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Bigmart Offer Calendar",
        "X-WR-CALDESC:Big Wednesday\\, Antim Budhabar \\& Big Saturday offers from Bigmart Nepal",
        "X-WR-TIMEZONE:Asia/Kathmandu",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
        *vevents,
        "END:VCALENDAR",
    ])

    with open(OUTPUT_FILE, "w", newline="\r\n") as f:
        f.write(calendar)

    print(f"Wrote {len(vevents)} events to {OUTPUT_FILE}")
    print(f"Content hash: {hashlib.sha256(calendar.encode()).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
