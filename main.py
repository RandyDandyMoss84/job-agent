"""
Daily job alert agent — entry point.

Usage:
    python3 main.py            # normal run: fetch, filter, email new matches
    python3 main.py --dry-run  # fetch and filter, print results, don't email or mark as seen

Scheduling note: a laptop that's asleep at the scheduled cron time simply
never runs the job — cron doesn't wake the machine and has no catch-up for a
fire it missed while asleep. So instead of a single 8AM fire, the crontab
should list a CATCH-UP WINDOW of several times each weekday morning, e.g.:
    */30 7-10 * * 1-5 cd /path/to/job-agent && /path/to/venv/bin/python3 main.py >> run.log 2>&1
main() below is a no-op (exits immediately) if today's run already completed,
so those extra cron fires cost nothing on a normal day — the window just
means whichever fire happens to land while the Mac is actually awake is the
one that runs, instead of depending on the Mac being awake at one exact minute.
"""

import datetime
import json
import sys
import traceback

from config import SOURCES_ENABLED, WATCHLIST_COMPANIES, JOBBANK_QUERIES
from sources import (
    fetch_remote_rocketship, fetch_goodwork_ca, fetch_jobbank_canada,
    fetch_brookfield_renewable, fetch_wellfound, fetch_fusion_energy_base,
    fetch_climatebase, fetch_pac_org, fetch_odgers_opportunities,
    fetch_workable_company, fetch_greenhouse_company, fetch_bamboohr_company,
)
from filters import evaluate_job
from storage import (
    load_seen, save_seen, load_last_run_date, save_last_run_date,
    load_last_matches, save_last_matches,
)
from emailer import compose_digest, send_digest


def fetch_all_jobs():
    jobs = []

    if SOURCES_ENABLED.get("remote_rocketship"):
        try:
            jobs += fetch_remote_rocketship()
        except Exception:
            print("Remote Rocketship fetch failed:")
            traceback.print_exc()

    if SOURCES_ENABLED.get("goodwork_ca"):
        try:
            jobs += fetch_goodwork_ca()
        except Exception:
            print("GoodWork.ca fetch failed:")
            traceback.print_exc()

    if SOURCES_ENABLED.get("jobbank_canada"):
        for query in JOBBANK_QUERIES:
            try:
                jobs += fetch_jobbank_canada(query)
            except Exception:
                print(f"Job Bank Canada fetch failed (query={query!r}):")
                traceback.print_exc()

    if SOURCES_ENABLED.get("brookfield_renewable"):
        try:
            jobs += fetch_brookfield_renewable()
        except Exception:
            print("Brookfield Renewable fetch failed:")
            traceback.print_exc()

    if SOURCES_ENABLED.get("wellfound"):
        try:
            jobs += fetch_wellfound()
        except Exception:
            print("Wellfound fetch failed:")
            traceback.print_exc()

    if SOURCES_ENABLED.get("fusion_energy_base"):
        try:
            jobs += fetch_fusion_energy_base()
        except Exception:
            print("Fusion Energy Base fetch failed:")
            traceback.print_exc()

    if SOURCES_ENABLED.get("climatebase"):
        try:
            jobs += fetch_climatebase()
        except Exception:
            print("Climatebase fetch failed:")
            traceback.print_exc()

    if SOURCES_ENABLED.get("pac_org"):
        try:
            jobs += fetch_pac_org()
        except Exception:
            print("PAC.org fetch failed:")
            traceback.print_exc()

    if SOURCES_ENABLED.get("odgers_berndtson"):
        try:
            jobs += fetch_odgers_opportunities()
        except Exception:
            print("Odgers Berndtson fetch failed:")
            traceback.print_exc()

    if SOURCES_ENABLED.get("watchlist_companies"):
        for name, (ats_type, slug) in WATCHLIST_COMPANIES.items():
            try:
                if ats_type == "workable":
                    jobs += fetch_workable_company(slug)
                elif ats_type == "greenhouse":
                    jobs += fetch_greenhouse_company(slug)
                elif ats_type == "bamboohr":
                    jobs += fetch_bamboohr_company(slug, company_name=name)
            except Exception:
                print(f"{name} ({ats_type}/{slug}) fetch failed:")
                traceback.print_exc()

    return jobs


def main():
    dry_run = "--dry-run" in sys.argv
    today = datetime.date.today().isoformat()

    if not dry_run and load_last_run_date() == today:
        print(f"Already ran today ({today}) — skipping (catch-up window no-op).")
        return

    print(f"Fetching jobs (dry_run={dry_run})...")
    all_jobs = fetch_all_jobs()
    print(f"Fetched {len(all_jobs)} raw listings.")

    # dedupe within this run — e.g. running Job Bank Canada with multiple query
    # terms can surface the same posting more than once
    deduped_jobs = {}
    for job in all_jobs:
        url = job.get("url", "")
        if url:
            deduped_jobs.setdefault(url, job)
    all_jobs = list(deduped_jobs.values())
    print(f"{len(all_jobs)} unique listings after dedup.")

    if not dry_run:
        # mark today done now, right after the fetch (the fallible part) succeeds —
        # covers both the "no new matches" and "matches sent" paths below in one
        # place, so a later catch-up-window cron fire today is a no-op either way
        save_last_run_date(today)

    seen = load_seen()
    strong_matches = []
    imperfect_matches = []
    newly_seen = set()

    for job in all_jobs:
        url = job.get("url", "")
        if not url or url in seen:
            continue

        is_match, is_strong, score, reasons = evaluate_job(job)
        if not is_match:
            continue

        newly_seen.add(url)
        if is_strong:
            strong_matches.append((job, score, reasons))
        else:
            imperfect_matches.append((job, score, reasons))

    strong_matches.sort(key=lambda entry: entry[1], reverse=True)
    imperfect_matches.sort(key=lambda entry: entry[1], reverse=True)

    print(f"New strong matches: {len(strong_matches)}")
    print(f"New imperfect matches: {len(imperfect_matches)}")

    carried_over_date = None
    if not strong_matches and not imperfect_matches:
        # quiet day — fall back to resending the last non-empty match set
        # rather than sending nothing, so there's always something in the
        # inbox to actively clear/ignore instead of silence you have to
        # trust is correct
        carried_over_date, strong_matches, imperfect_matches = load_last_matches()
        if carried_over_date is None:
            print("No new matches today, and no previous matches cached yet — nothing to send.")
            return
        print(f"No new matches today — resending {len(strong_matches) + len(imperfect_matches)} match(es) from {carried_over_date}.")

    digest = compose_digest(strong_matches, imperfect_matches, carried_over_date=carried_over_date)

    if dry_run:
        print("\n--- DRY RUN: would send this digest ---\n")
        print(digest)
        return

    subject = (
        f"Job alert digest — no new matches, resending {carried_over_date}'s"
        if carried_over_date
        else "Your daily job alert digest"
    )

    # Written regardless of EMAIL_ENABLED so a caller that isn't using smtplib
    # (e.g. the cloud Routine, which sends via the Gmail MCP connector
    # instead) has a reliable, structured place to read today's subject/body
    # from, instead of scraping terminal output. (Restored 2026-09-30 — an
    # earlier commit dropped this write while leaving a comment elsewhere
    # claiming it still happened, which would have silently broken the cloud
    # Routine's email step.)
    with open("pending_digest.json", "w") as f:
        json.dump({"subject": subject, "html": digest}, f)

    send_digest(digest, subject=subject)
    save_seen(seen | newly_seen)
    if carried_over_date is None:
        save_last_matches(today, strong_matches, imperfect_matches)


if __name__ == "__main__":
    main()
