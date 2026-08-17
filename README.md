# Bigmart Offer Calendar — GitHub Pages version

Same live-feed concept as before, adapted to fit your existing GitHub Pages
site instead of running a Flask server. GitHub Pages only serves static
files, so "live" here means: **GitHub Actions rebuilds `cal.ics` automatically
whenever `offers.json` changes (or every 15 min on a schedule), and commits
it back to the repo — Pages then serves the new version at your existing URL.**

```
offers.json  (you edit this — the source of truth)
      │  git push
      ▼
GitHub Actions runs generate_ics.py
      │  commits cal.ics back to the repo
      ▼
GitHub Pages serves the updated cal.ics
      │
      ▼
https://www.sandipshrestha0.com.np/cal.ics
```

## Setup (one-time)

1. Copy these 4 files into the root of the repo that publishes
   `sandipshrestha0.com.np` (same place your current `cal.ics` lives):
   - `offers.json`
   - `generate_ics.py`
   - `nepali_calendar.py`
   - `.github/workflows/update-calendar.yml`
2. Go to **Settings → Actions → General** in your repo and make sure
   "Workflow permissions" is set to **Read and write permissions** — the
   workflow needs to `git push` the regenerated file back.
3. Push. The workflow runs immediately (since it triggers on push to
   `offers.json`/`generate_ics.py`/`nepali_calendar.py`) and every 15
   minutes afterward, and you can also trigger it manually from the
   **Actions** tab (`Run workflow` button).

## Updating an offer (your day-to-day workflow)

Edit `offers.json` directly on GitHub (or locally + `git push`):

```json
{
  "overrides": [
    {
      "event_date": "2026-08-22",
      "event_type": "big_saturday",
      "offer_title": "Big Saturday — Up to 25% Off!",
      "details": "Up to 25% off selected items. Extra 5% for app users.",
      "stores": "All Bigmart outlets, Kathmandu Valley",
      "published": true
    }
  ]
}
```

- `event_type`: `big_wednesday`, `antim_budhabar`, or `big_saturday`
- Set `"published": false` to cancel one specific date (e.g. public holiday
  closure) without touching the recurring rule
- Any Wednesday/Saturday with **no** entry here still appears, using the
  default offer text inside `generate_ics.py` — you only need an entry when
  the offer differs from the default

The commit itself triggers the rebuild — no need to run anything locally.

## Verified locally before handing this over

- `python generate_ics.py` produced 9 events (4 Big Wednesday, 1 Antim
  Budhabar on the correct last-Wednesday date, 4 Big Saturday) for Bhadra
  2083 BS.
- The `offers.json` override for Aug 22 Big Saturday applied correctly.
- Running the generator twice with no changes produces an **identical
  output hash** — meaning the scheduled 15-min run won't create a noisy
  commit unless something actually changed.

## Subscription link for the QR code / landing page

Use the `webcal://` form so phones offer "Subscribe" rather than "Download":

```
webcal://www.sandipshrestha0.com.np/cal.ics
```

## Real-world refresh speed (same limits as any .ics feed, GitHub Pages or not)

This part is identical regardless of hosting — it's the calendar app, not
the server, that decides how often to re-check:

| Platform | How often it re-checks the URL |
|---|---|
| Apple Calendar | ~hourly by default; subscriber can set as low as 5–15 min |
| Google Calendar | 8–24 hours, no user control |
| Outlook | 1–4 hours |

For anything time-critical (e.g. "sale starts in 2 hours"), don't rely on
the calendar alone — that's what the Phase 3 push/SMS/WhatsApp layer is for.

## Extending beyond Bhadra 2083

`nepali_calendar.py`'s `BS_MONTH_TABLE` only has verified data for one
month. Before the calendar needs to show a different Nepali month, add a
verified entry (from a maintained source, not a guess — BS month lengths
aren't computable by formula, they vary year to year).
