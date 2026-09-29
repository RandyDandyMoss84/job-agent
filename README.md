# Daily Job Alert Agent

Filters job postings against Jared's benchmark (senior/director communications,
PR, or IR roles in energy/climate/cleantech, $150K+, Canada-eligible) and emails
a daily digest of new matches.

## Status: filter logic tested and working. Source scrapers are untested (see below).

## Setup
1. `pip install -r requirements.txt`
2. Edit `config.py`:
   - Fill in SMTP_USERNAME / SMTP_APP_PASSWORD / EMAIL_TO (Gmail App Password:
     Google Account > Security > App Passwords)
   - Set EMAIL_ENABLED = True once ready to actually send
   - Adjust WATCHLIST_COMPANIES slugs — the ones in there now are guesses and
     need to be verified against each company's real Greenhouse/Workable board
3. Run once manually first: `python3 main.py --dry-run`
   - This prints what it would send without emailing or marking jobs as seen.
   - Check the output makes sense before turning on real sends.
4. Once satisfied: `python3 main.py` for a real run.
5. Schedule it (cron example, runs daily at 7am):
   `0 7 * * * cd /path/to/job-agent && /path/to/python3 main.py >> run.log 2>&1`

## What's tested vs. what's not
- **filters.py** — tested against sample data, logic confirmed correct
  (see test in chat history / rerun manually with sample jobs).
- **sources.py** — NOT tested against live sites. This sandbox's network
  access doesn't reach climatetechlist.com, remoterocketship.com, goodwork.ca,
  or workable.com, so the scraping selectors are best-guess placeholders.
  **Before relying on this daily:** run each fetch_* function individually,
  print its output, and fix the CSS selectors / JSON paths against what the
  live site actually returns. Expect this step to take the most time.
- **emailer.py** — SMTP logic is standard and should work once real
  credentials are in config.py; not tested with real credentials here.

## Known gaps / next steps
- ClimateTechList is JS-rendered — fetch_remote_rocketship-style scraping
  won't work on it. Either find an API/RSS, or add Playwright/Selenium if
  it turns out to be worth the extra dependency.
- WATCHLIST_COMPANIES slugs for General Fusion and Moment Energy are guesses —
  confirm their actual Greenhouse/Workable org slugs (visible in their
  careers page URL) before relying on those two.
- Consider adding more watchlist companies as they come up (Foresight Canada,
  CICE, etc. — check what ATS each uses).
