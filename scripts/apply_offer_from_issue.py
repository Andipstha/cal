#!/usr/bin/env python3
"""
Reads the ISSUE_BODY env var (a GitHub Issue Form submission), validates it,
and updates offers.json. Writes result=ok|error and message=... to
$GITHUB_OUTPUT so the workflow can comment on / close the issue accordingly.

GitHub renders issue form submissions as predictable markdown:

    ### <field label>

    <submitted value>

    ### <next field label>
    ...

This parser splits on that pattern rather than guessing at free-form text,
so it's only as fragile as the issue form's own field labels -- if you
rename a label in update-offer.yml, update FIELD_LABELS below to match.
"""

import json
import os
import re
import sys
import datetime as dt

OFFERS_FILE = "offers.json"

FIELD_LABELS = {
    "event_date": "Offer date",
    "event_type": "Which slot is this for?",
    "cancel": "Is this cancelling an offer, or publishing one?",
    "offer_title": "Offer headline",
    "details": "Offer details",
    "stores": "Participating stores",
}

EVENT_TYPE_MAP = {
    "big wednesday": "big_wednesday",
    "antim budhabar (the month's last wednesday)": "antim_budhabar",
    "big saturday": "big_saturday",
    "special one-off offer (any date)": "special_offer",
}

# event_type -> required weekday (Mon=0 ... Sun=6), used to catch staff
# picking a date that doesn't actually match the slot they chose.
# special_offer is intentionally absent -- it can land on any date.
EXPECTED_WEEKDAY = {
    "big_wednesday": 2,
    "antim_budhabar": 2,
    "big_saturday": 5,
}


def parse_issue_body(body: str) -> dict:
    """Split the issue form markdown into {field_label: value}."""
    parts = re.split(r"^### (.+)$", body, flags=re.MULTILINE)
    # parts[0] is anything before the first header (ignored);
    # after that it alternates [label, value, label, value, ...]
    fields = {}
    for i in range(1, len(parts) - 1, 2):
        label = parts[i].strip()
        value = parts[i + 1].strip()
        if value in ("_No response_", ""):
            value = ""
        fields[label] = value
    return fields


def get(fields: dict, key: str) -> str:
    return fields.get(FIELD_LABELS[key], "").strip()


def write_output(result: str, message: str):
    gh_output = os.environ.get("GITHUB_OUTPUT")
    # Message may be multi-line -- use the heredoc-style delimiter form.
    line = f"result={result}\nmessage<<EOM\n{message}\nEOM\n"
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(line)
    else:
        print(line)


def fail(message: str):
    write_output("error", message)
    sys.exit(0)  # exit 0 so the workflow can still comment on the issue


def main():
    body = os.environ.get("ISSUE_BODY", "")
    fields = parse_issue_body(body)

    raw_date = get(fields, "event_date")
    raw_type = get(fields, "event_type").lower()
    raw_cancel = get(fields, "cancel").lower()
    offer_title = get(fields, "offer_title")
    details = get(fields, "details")
    stores = get(fields, "stores") or "All Bigmart outlets, Kathmandu Valley"

    # --- validate date ---
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw_date):
        fail(f"'{raw_date}' isn't in YYYY-MM-DD format. Please edit the issue and fix the date, e.g. 2026-08-29.")
    try:
        event_date = dt.date.fromisoformat(raw_date)
    except ValueError:
        fail(f"'{raw_date}' isn't a real calendar date. Please edit the issue and fix it.")

    # --- validate event type ---
    event_type = EVENT_TYPE_MAP.get(raw_type)
    if not event_type:
        fail(f"Couldn't match '{raw_type}' to a known offer slot. Please re-select from the dropdown.")

    # --- cross-check weekday matches the chosen slot (skipped for one-off types) ---
    expected = EXPECTED_WEEKDAY.get(event_type)
    if expected is not None and event_date.weekday() != expected:
        expected_name = "Wednesday" if expected == 2 else "Saturday"
        fail(
            f"{raw_date} is a {event_date.strftime('%A')}, but you selected a slot that needs a "
            f"{expected_name}. Please fix the date or the slot and re-edit the issue."
        )

    is_cancel = raw_cancel.startswith("cancel")

    if not is_cancel:
        if not offer_title:
            fail("Offer headline is required unless you're cancelling this date. Please edit the issue.")
        if not details:
            fail("Offer details are required unless you're cancelling this date. Please edit the issue.")

    # --- load and update offers.json ---
    with open(OFFERS_FILE) as f:
        data = json.load(f)

    overrides = data.setdefault("overrides", [])
    now = dt.datetime.utcnow().isoformat()

    entry = {
        "event_date": raw_date,
        "event_type": event_type,
        "offer_title": offer_title if not is_cancel else "(cancelled)",
        "details": details if not is_cancel else "This date has been cancelled.",
        "stores": stores,
        "published": not is_cancel,
        "_updated_at": now,
    }

    existing_idx = next(
        (i for i, o in enumerate(overrides)
         if o.get("event_date") == raw_date and o.get("event_type") == event_type),
        None,
    )
    if existing_idx is not None:
        overrides[existing_idx] = entry
        action = "Updated"
    else:
        overrides.append(entry)
        action = "Added"

    with open(OFFERS_FILE, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    slot_name = {
        "big_wednesday": "Big Wednesday",
        "antim_budhabar": "Antim Budhabar",
        "big_saturday": "Big Saturday",
        "special_offer": "Special Offer",
    }[event_type]
    if is_cancel:
        msg = f"{action} — {slot_name} on {raw_date} is now cancelled/hidden."
    else:
        msg = f"{action} — {slot_name} on {raw_date}: \"{offer_title}\""

    write_output("ok", msg)


if __name__ == "__main__":
    main()
