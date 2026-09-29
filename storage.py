"""Tracks which job URLs have already been sent, so re-runs only surface new ones.
Also tracks the last date a run actually completed, so a cron fire that finds
the Mac was asleep for its scheduled time isn't just silently lost forever —
see LAST_RUN_FILE / main.py's catch-up window.
Also caches the last non-empty match set, so a quiet day (no genuinely new
matches) still sends an email — resending the last real matches instead of
silence, per request: always get something to actively clear/ignore rather
than wonder if the tool is still working. See LAST_MATCHES_FILE.
"""

import json
import os
from config import SEEN_JOBS_FILE, LAST_RUN_FILE, LAST_MATCHES_FILE


def load_seen():
    if not os.path.exists(SEEN_JOBS_FILE):
        return set()
    with open(SEEN_JOBS_FILE, "r") as f:
        return set(json.load(f))


def save_seen(seen_urls):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(sorted(seen_urls), f, indent=2)


def load_last_run_date():
    if not os.path.exists(LAST_RUN_FILE):
        return None
    with open(LAST_RUN_FILE, "r") as f:
        return json.load(f).get("date")


def save_last_run_date(date_str):
    with open(LAST_RUN_FILE, "w") as f:
        json.dump({"date": date_str}, f)


def load_last_matches():
    """Returns (date_str, strong_matches, imperfect_matches) from the last
    non-empty run, or (None, [], []) if there's no cache yet. Each match is
    restored as (job_dict, score, reasons_list), same shape main.py works with."""
    if not os.path.exists(LAST_MATCHES_FILE):
        return None, [], []
    with open(LAST_MATCHES_FILE, "r") as f:
        data = json.load(f)
    to_tuples = lambda entries: [(e["job"], e["score"], e["reasons"]) for e in entries]
    return data.get("date"), to_tuples(data.get("strong_matches", [])), to_tuples(data.get("imperfect_matches", []))


def save_last_matches(date_str, strong_matches, imperfect_matches):
    to_dicts = lambda matches: [{"job": job, "score": score, "reasons": reasons} for job, score, reasons in matches]
    with open(LAST_MATCHES_FILE, "w") as f:
        json.dump({
            "date": date_str,
            "strong_matches": to_dicts(strong_matches),
            "imperfect_matches": to_dicts(imperfect_matches),
        }, f, indent=2)
