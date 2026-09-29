"""
Fetch functions for each job source. Each returns a list of dicts:
{
    "title": str,
    "company": str,
    "location": str,
    "comp": str | None,
    "url": str,
    "source": str,
    "raw_description": str,   # used for keyword/location filtering
    "company_stage": str,     # see company_stage.py — best-effort, often "Unknown"
}

Confirmed against the live sites 2026-09-11 (see each function's docstring
for specifics and known limitations). Sites change their HTML/markup
without notice — re-verify if a source silently starts returning nothing.
"""

import json
import re

import requests
from bs4 import BeautifulSoup

from company_stage import classify_stage

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobAlertAgent/1.0; personal use)"
}


def fetch_remote_rocketship(query="senior-communications", max_pages=10):
    """
    Remote Rocketship is a Next.js app: the listing page's rendered HTML is
    useless for scraping, but each page embeds a <script id="__NEXT_DATA__">
    with the full job list as JSON (props.pageProps.initialJobOpenings) —
    confirmed live 2026-09-11 against https://www.remoterocketship.com/us/jobs/senior-communications/
    (149 results, 20 jobs per page). Pagination is a plain ?page=N query
    param on the same URL; props.pageProps.initialTotalJobCount gives the
    total so we know when to stop. Each job entry already includes company
    name, human-readable location/salary, a description summary, and —
    usefully — the *direct* posting URL (e.g. the underlying Greenhouse/
    Workable link), not a remoterocketship.com redirect.
    """
    base_url = f"https://www.remoterocketship.com/us/jobs/{query}/"
    jobs = []
    total_job_count = None
    page = 1

    while page <= max_pages:
        resp = requests.get(base_url, params={"page": page}, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag or not script_tag.string:
            break

        data = json.loads(script_tag.string)
        page_props = data.get("props", {}).get("pageProps", {})
        openings = page_props.get("initialJobOpenings", [])
        if total_job_count is None:
            total_job_count = page_props.get("initialTotalJobCount", 0)
        if not openings:
            break

        for job in openings:
            company = job.get("company") or {}
            salary = job.get("salaryRange") or {}
            jobs.append({
                "title": job.get("roleTitle", ""),
                "company": company.get("name"),
                "location": job.get("location"),
                "comp": salary.get("salaryHumanReadableText"),
                "url": job.get("url", ""),
                "source": "Remote Rocketship",
                "raw_description": job.get("twoLineJobDescriptionSummary")
                or job.get("jobDescriptionSummary")
                or job.get("roleTitle", ""),
                "company_stage": classify_stage(
                    company.get("name"),
                    founded_year=company.get("foundedYear"),
                    funding_data=company.get("fundingData"),
                    employee_range=company.get("employeeRange"),
                ),
            })

        if len(jobs) >= total_job_count:
            break
        page += 1

    return jobs


def fetch_goodwork_ca():
    """
    GoodWork.ca — Canadian environmental/climate jobs board.
    Confirmed live 2026-09-11: https://www.goodwork.ca/rss (redirects to
    /rss/) is real RSS covering the whole site's newest postings (not
    filterable by category/remote via the feed itself). The server mislabels
    it as Content-Type: text/html, so do NOT gate on the content-type header
    — check the body instead. Items have no <description>, and the title is
    a single packed string like "Role, employment_type,,, Company, Location"
    with inconsistent comma counts (job titles can themselves contain
    commas), too unreliable to split into separate company/location fields.
    filters.py keyword-matches against the full title anyway, so this is
    fine — company/location are left None here rather than guessed at.
    """
    resp = requests.get("https://www.goodwork.ca/rss", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    if not resp.text.lstrip().startswith("<?xml"):
        return []
    return _parse_goodwork_rss(resp.text)


def _parse_goodwork_rss(xml_text):
    soup = BeautifulSoup(xml_text, "xml")
    jobs = []
    for item in soup.find_all("item"):
        title = item.title.get_text(strip=True) if item.title else ""
        jobs.append({
            "title": title,
            "company": None,
            "location": None,
            "comp": None,
            "url": item.link.get_text(strip=True) if item.link else "",
            "source": "GoodWork.ca",
            "raw_description": item.description.get_text(strip=True) if item.description else title,
            "company_stage": "Unknown — GoodWork.ca doesn't expose company name separately",
        })
    return jobs


def fetch_workable_company(slug):
    """
    Many companies expose a public JSON endpoint for their Workable board:
    https://apply.workable.com/api/v1/widget/accounts/{slug}
    Confirmed live against slug "renewhome" 2026-09-11. Each job has flat
    "city"/"state"/"country" fields (frequently blank for remote-only roles)
    plus a "locations" list with the same fields per office; there is no
    "location"/"location_str" key. There's also no per-job prose description
    in this widget response, but there IS a per-job "industry" field (e.g.
    "Renewables & Environment") and "function"/"department" — worth folding
    into raw_description, since filters.py's sector check is a plain keyword
    search over title+raw_description+location: without it, a job titled
    just "Senior Manager, Communications (Remote, US)" carries no textual
    signal at all that the employer is an energy company, and would wrongly
    fail the sector gate.
    """
    url = f"https://apply.workable.com/api/v1/widget/accounts/{slug}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for job in data.get("jobs", []):
        location = ", ".join(
            part for part in (job.get("city"), job.get("state"), job.get("country"))
            if part
        )
        title = job.get("title", "")
        context_bits = [job.get("industry"), job.get("function"), job.get("department")]
        raw_description = ". ".join([title] + [b for b in context_bits if b])
        jobs.append({
            "title": title,
            "company": slug,
            "location": location,
            "comp": None,  # Workable's public widget doesn't expose salary
            "url": job.get("url", ""),
            "source": f"Workable/{slug}",
            "raw_description": raw_description,
            "company_stage": classify_stage(slug),
        })
    return jobs


def fetch_greenhouse_company(slug):
    """
    Greenhouse public job board API:
    https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for job in data.get("jobs", []):
        jobs.append({
            "title": job.get("title", ""),
            "company": slug,
            "location": job.get("location", {}).get("name", ""),
            "comp": None,
            "url": job.get("absolute_url", ""),
            "source": f"Greenhouse/{slug}",
            "raw_description": job.get("title", ""),
            "company_stage": classify_stage(slug),
        })
    return jobs


def fetch_jobbank_canada(query="communications director"):
    """
    Canada's official Job Bank (jobbank.gc.ca). Confirmed live 2026-09-11.
    Gotcha: the RSS/Atom feed at /jobsearch/feed/jobSearchRSSfeed silently
    IGNORES query params (term/searchstring/etc.) unless requested through
    the same session (jsessionid) that generated them — hit it cold with a
    fresh session and you get an unfiltered firehose of unrelated postings
    (health care aide, truck driver, ...), no error, just wrong data. The
    working flow is two requests sharing one session: (1) GET the human
    search page with ?searchstring={query}, which both establishes the
    session and embeds the correctly-scoped RSS link (jsessionid + category
    codes) in the page HTML; (2) GET that embedded RSS link with the same
    session. Each entry's <summary> packs "Job number"/"Location"/
    "Employer"/"Salary" as labeled inline HTML rather than separate fields,
    parsed out below.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    search_resp = session.get(
        "https://www.jobbank.gc.ca/jobsearch/jobsearch",
        params={"searchstring": query, "sort": "D"},
        timeout=15,
    )
    search_resp.raise_for_status()

    link_match = re.search(r'href="(/jobsearch/feed/jobSearchRSSfeed[^"]*)"', search_resp.text)
    if not link_match:
        return []
    # rows is already baked into the extracted link (Job Bank sets it from the
    # search page's own default), so it isn't passed again here.
    rss_url = "https://www.jobbank.gc.ca" + link_match.group(1).replace("&amp;", "&")

    rss_resp = session.get(rss_url, timeout=15)
    rss_resp.raise_for_status()

    soup = BeautifulSoup(rss_resp.text, "xml")
    jobs = []
    for entry in soup.find_all("entry"):
        title = entry.title.get_text(strip=True) if entry.title else ""
        link_tag = entry.find("link")
        url = link_tag.get("href", "") if link_tag else ""
        summary_html = entry.summary.get_text() if entry.summary else ""
        location = _jobbank_field(summary_html, "Location")
        employer = _jobbank_field(summary_html, "Employer")
        jobs.append({
            "title": title,
            "company": employer,
            "location": "" if location == "Not Available" else location,
            "comp": _jobbank_field(summary_html, "Salary"),
            "url": url,
            "source": "Job Bank Canada",
            "raw_description": title,
            "company_stage": classify_stage(employer),
        })
    return jobs


def _jobbank_field(summary_html, label):
    match = re.search(rf"{label}:</strong>\s*([^<]*)", summary_html)
    return match.group(1).strip() if match else None


def fetch_brookfield_renewable():
    """
    Brookfield Renewable's job board runs on UltiPro (recruiting.ultipro.com)
    — a knockout.js SPA with nothing in the initial HTML. Confirmed live
    2026-09-11 via a two-step flow found by intercepting the page's own
    network calls in a real browser (UltiPro has no documented public API):
    (1) GET the board's landing page to establish a session cookie, (2) POST
    to .../JobBoardView/LoadSearchResults with the exact JSON body the page
    itself sends. UltiPro's own QueryString search is unreliable — searching
    "communications" server-side returned mostly unrelated titles (Supervisor,
    River Steward, ...) — so this pulls the FULL unfiltered listing instead
    (QueryString="", Top=200; confirmed all 67 open jobs fit in one page) and
    lets filters.py's own title-keyword matching do the real filtering, the
    same approach used for GoodWork.ca's firehose feed. No salary field
    exists in this API. Detail URLs follow UltiPro's standard
    OpportunityDetail?opportunityId= convention (200s, but the page is a
    knockout.js SPA so its rendered content can't be verified by a plain
    HTTP fetch — only confirmed working in an actual browser).
    """
    base = "https://recruiting.ultipro.com/BRO5000/JobBoard/ed800086-1d62-5572-f313-3794fce12c2f"
    session = requests.Session()
    session.headers.update(HEADERS)

    session.get(f"{base}/?q=&o=postedDateDesc", timeout=15)

    body = {
        "opportunitySearch": {
            "Top": 200,
            "Skip": 0,
            "QueryString": "",
            "OrderBy": [{"Value": "relevance", "PropertyName": "MatchScore", "Ascending": False}],
            "Filters": [
                {"t": "TermsSearchFilterDto", "fieldName": n, "extra": None, "values": []}
                for n in (4, 5, 6, 37)
            ],
        },
        "matchCriteria": {
            "PreferredJobs": [], "Educations": [], "LicenseAndCertifications": [],
            "Skills": [], "hasNoLicenses": False, "SkippedSkills": [],
        },
    }
    resp = session.post(
        f"{base}/JobBoardView/LoadSearchResults",
        json=body,
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for opp in data.get("opportunities", []):
        location = _brookfield_location(opp.get("Locations") or [])
        title = opp.get("Title", "")
        jobs.append({
            "title": title,
            "company": "Brookfield Renewable",
            "location": location,
            "comp": None,  # UltiPro's public board doesn't expose salary
            "url": f"{base}/OpportunityDetail?opportunityId={opp.get('Id', '')}",
            "source": "Brookfield Renewable",
            "raw_description": f"{title}. {opp.get('BriefDescription', '')}",
            "company_stage": classify_stage("brookfield renewable"),
        })
    return jobs


def _brookfield_location(locations):
    parts = []
    for loc in locations:
        name = loc.get("LocalizedName")
        addr = loc.get("Address") or {}
        city = addr.get("City")
        state = (addr.get("State") or {}).get("Name")
        country = (addr.get("Country") or {}).get("Name")
        parts.append(name or ", ".join(p for p in (city, state, country) if p))
    return "; ".join(p for p in parts if p)


def fetch_wellfound(location="vancouver", max_pages=6):
    """
    Wellfound (formerly AngelList Talent) startup job board. Confirmed live
    2026-09-11 at https://wellfound.com/location/{location} — a real browser
    sometimes shows a Cloudflare challenge here, but a plain requests GET
    with a normal User-Agent returns the actual server-rendered page
    directly, no JS execution needed. Data lives in the standard Next.js
    __NEXT_DATA__ blob, structured as an Apollo Client normalized cache
    (props.pageProps.apolloState.data): a "seoLandingPageJobSearchResults"
    entry under ROOT_QUERY.talent lists StartupResult refs, each with a
    name, a COMPANY_STAGE badge (Wellfound's OWN stage label — used directly
    here instead of our own inference), and highlightedJobListings refs
    pointing to JobListingSearchResult entries with the full job
    description, locationNames, and — usefully — acceptedRemoteLocationNames,
    which explicitly lists "Canada" when a remote role is Canada-eligible;
    that's folded into raw_description so filters.py's existing "canada"
    phrase match picks it up without guessing. Pagination is a plain ?page=N
    (confirmed live: page 2 returns different startups than page 1);
    pageCount in the response says how many pages exist.
    """
    jobs = []
    page = 1
    total_pages = None

    while page <= max_pages:
        resp = requests.get(
            f"https://wellfound.com/location/{location}",
            params={"page": page},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag or not script_tag.string:
            break

        data = json.loads(script_tag.string)
        cache = data.get("props", {}).get("pageProps", {}).get("apolloState", {}).get("data", {})
        talent = cache.get("ROOT_QUERY", {}).get("talent", {})
        results_key = next(
            (k for k in talent if k.startswith("seoLandingPageJobSearchResults")), None
        )
        if not results_key:
            break
        results = talent[results_key]
        if total_pages is None:
            total_pages = results.get("pageCount", 1)

        for startup_ref in results.get("startups", []):
            startup = cache.get(startup_ref.get("__ref"))
            if not startup:
                continue
            company_name = startup.get("name")
            stage_label = _wellfound_stage(cache, startup.get("badges") or [])

            for job_ref in startup.get("highlightedJobListings") or []:
                job = cache.get(job_ref.get("__ref"))
                if not job:
                    continue
                accepted_remote = job.get("acceptedRemoteLocationNames") or []
                locations = job.get("locationNames") or []
                remote_note = (
                    f" Remote-eligible: {', '.join(accepted_remote)}." if accepted_remote else ""
                )
                jobs.append({
                    "title": job.get("title", ""),
                    "company": company_name,
                    "location": "; ".join(locations),
                    "comp": job.get("compensation") or None,
                    "url": f"https://wellfound.com/jobs/{job.get('id')}-{job.get('slug')}",
                    "source": "Wellfound",
                    "raw_description": f"{job.get('title', '')}. {job.get('description', '')}{remote_note}",
                    "company_stage": stage_label or classify_stage(company_name),
                })

        if total_pages is None or page >= total_pages:
            break
        page += 1

    return jobs


def fetch_fusion_energy_base(tags=("communications",)):
    """
    Fusion Energy Base (fusionenergybase.com) — a directory of jobs across
    fusion-energy organizations worldwide, with a real tag-filterable REST
    API. Confirmed live 2026-09-11 by intercepting the live site's own
    filter-click network call: GET /api/v1/jobs/?tag={tag}&sort=date_added,
    no auth needed, works from a cold session via plain requests. Each
    result's "website_url" is a tracking-redirect path
    (/api/v1/jobs/{id}/click/) that 302s to the real external posting —
    confirmed resolving correctly (e.g. to an Ashby-hosted posting) — used
    as-is here rather than following every redirect ourselves.
    """
    jobs = []
    seen_ids = set()
    for tag in tags:
        resp = requests.get(
            "https://www.fusionenergybase.com/api/v1/jobs/",
            params={"tag": tag, "sort": "date_added"},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        for job in data.get("results", []):
            job_id = job.get("id")
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            org = job.get("organization") or {}
            title = job.get("title", "")
            org_desc = org.get("description") or ""
            jobs.append({
                "title": title,
                "company": org.get("display_name"),
                "location": job.get("locations", ""),
                "comp": job.get("salary") or None,
                "url": f"https://www.fusionenergybase.com{job.get('website_url', '')}",
                "source": "Fusion Energy Base",
                "raw_description": f"{title}. {org_desc}".strip(),
                "company_stage": classify_stage(org.get("display_name")),
            })
    return jobs


def fetch_climatebase():
    """
    Climatebase.org — large general climate-jobs board. Confirmed live
    2026-09-11: real search is client-side Algolia (the page's own ?keyword=
    param does NOT filter server-side — verified identical results with and
    without it), but the /jobs page's server-rendered __NEXT_DATA__ blob
    (props.pageProps.jobs) already ships a batch of ~100 current postings
    with no auth or Algolia key needed, works from a cold plain-requests GET.
    Since keyword filtering isn't available this way, this pulls that same
    batch every run and lets filters.py's own title-keyword matching do the
    real filtering — same firehose approach as GoodWork.ca/Brookfield. No
    direct job URL in the JSON; constructed from id + a slugified title,
    matching the pattern confirmed in the live page's actual rendered links
    (https://climatebase.org/job/{id}/{slug}).
    """
    resp = requests.get("https://climatebase.org/jobs", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if not script_tag or not script_tag.string:
        return []

    data = json.loads(script_tag.string)
    raw_jobs = data.get("props", {}).get("pageProps", {}).get("jobs", [])

    jobs = []
    for job in raw_jobs:
        title = job.get("title", "")
        salary_from = job.get("salary_from")
        salary_to = job.get("salary_to")
        comp = None
        if salary_from or salary_to:
            comp = f"{salary_from or '?'}-{salary_to or '?'} {job.get('salary_period', '')}".strip()
        locations = job.get("locations") or []
        remote_prefs = job.get("remote_preferences") or []
        location = ", ".join(locations) if locations else "; ".join(remote_prefs)
        sectors = ", ".join(job.get("sectors") or [])
        employer = job.get("name_of_employer")
        employer_desc = job.get("employer_short_description") or ""
        jobs.append({
            "title": title,
            "company": employer,
            "location": location,
            "comp": comp,
            "url": f"https://climatebase.org/job/{job.get('id')}/{_slugify(title)}",
            "source": "Climatebase",
            "raw_description": f"{title}. Sectors: {sectors}. {employer_desc}".strip(),
            "company_stage": classify_stage(employer),
        })
    return jobs


def _slugify(text):
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _wellfound_stage(cache, badge_refs):
    for ref in badge_refs:
        badge = cache.get(ref.get("__ref"))
        if badge and badge.get("name") == "COMPANY_STAGE_BADGE":
            return badge.get("label")
    return None


def fetch_pac_org():
    """
    Public Affairs Council (pac.org/jobs) — a US public-affairs/government-
    relations professional association's job board, flagged in the Sept 2026
    brief as the best find so far for senior remote roles. Confirmed live
    2026-09-29. Server-rendered HTML (WordPress + the FacetWP filter plugin,
    but the base /jobs page lists results without needing JS) — no API, and
    no salary data anywhere (checked both the list page and a job detail
    page; comp is always None here). Structure: each posting is a
    .job-container with an a.job-title (title text + URL) followed by a
    .job-row holding company (.job-column-1) and location (.job-column-2).
    Despite being US-focused, worth including — some listings are explicitly
    remote/Canada-eligible, and filters.py's existing US-only reject phrases
    and Canada-accept phrases apply the same as any other source; the rest
    get correctly caught by the same location logic every other US-heavy
    source already goes through.
    """
    resp = requests.get("https://pac.org/jobs", headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    jobs = []
    for container in soup.select(".job-container"):
        title_link = container.select_one("a.job-title")
        if not title_link:
            continue
        title = title_link.get_text(strip=True)
        url = title_link.get("href", "")
        job_row = container.select_one(".job-row")
        company = job_row.select_one(".job-column-1").get_text(strip=True) if job_row else None
        location = job_row.select_one(".job-column-2").get_text(strip=True) if job_row else ""
        jobs.append({
            "title": title,
            "company": company,
            "location": location,
            "comp": None,  # no salary data anywhere on this board
            "url": url,
            "source": "PAC.org",
            "raw_description": title,
            "company_stage": classify_stage(company),
        })
    return jobs
