"""
Configuration for the daily job alert agent.
Edit the values below — everything else in the script reads from here.
"""

# --- Benchmark criteria ---
# Modeled on: OhmConnect Director of External Communications ($185K-225K, remote US & Canada)
# and Renew Home Senior Manager, Communications ($155K-185K, US-only — used as a near-miss example)
#
# Two parallel tracks per the Sept 30 2026 job-search brief, each with its own
# comp floor (Track A is the primary target; Track B trades comp for equity/
# experience at an early-stage company) and its own sector rule (Track A
# needs an energy/climate/tech signal; Track B is sector-agnostic — see
# filters.py for how the sector gate applies differently per track).

# Track A — senior strategic comms / IR / public affairs / stakeholder relations
TITLE_KEYWORDS_STRATEGIC_COMMS = [
    "communications", "public relations", "pr director", "pr lead",
    "investor relations", "ir director", "corporate affairs",
    "external affairs", "stakeholder relations", "brand and communications",
    "regulatory affairs", "government relations", "government & stakeholder",
    "issues management", "reputation management", "indigenous relations",
    "indigenous & stakeholder", "chief of staff",
]

# Track B — product marketing at startups (comp floor is much lower — see
# MIN_COMP_CAD_PRODUCT_MARKETING — in exchange for equity/experience)
TITLE_KEYWORDS_PRODUCT_MARKETING = [
    "product marketing", "product marketer", "founding marketer",
    "head of marketing", "growth lead", "brand lead",
]

TITLE_KEYWORDS = TITLE_KEYWORDS_STRATEGIC_COMMS + TITLE_KEYWORDS_PRODUCT_MARKETING

SENIORITY_KEYWORDS = [
    "senior", "sr.", "director", "vp", "vice president", "head of", "lead",
]

# "Core" = the original energy/climate signal. "Broad" = tech/apps/commodities
# plus, as of 2026-09-29, fintech/healthtech/infrastructure — the widened
# Track A sector scope from the job-search brief (the storytelling-architect
# thesis applies wherever there's regulatory or stakeholder complexity, not
# just energy/climate). All of it is kept to *specific, meaningful* phrases
# rather than bare generic words — "app" and "technology" alone were removed
# because plain substring matching means "app" matches inside "application",
# "apply", "appropriate", "approach" etc., which appear in virtually every
# job posting and defeated the gate entirely. Both CORE and BROAD are treated
# as equally strong matches (see filters.py) — the split is kept only to
# label which sector a job matched on in the digest.
SECTOR_KEYWORDS_CORE = [
    "energy", "climate", "cleantech", "clean tech", "renewable", "renewables",
    "sustainability", "esg", "decarbonization", "clean energy", "fusion",
    "battery storage", "energy storage",
]

SECTOR_KEYWORDS_BROAD = [
    # tech / apps — qualified phrases, not bare words
    "software company", "technology company", "tech company", "saas",
    "mobile app", "consumer app", "app development", "enterprise software",
    # commodities
    "commodities", "commodity trading", "commodities trading",
    "commodity markets", "physical commodities",
    # fintech — added 2026-09-29, Track A widened beyond pure energy/climate
    "fintech", "financial technology", "digital banking", "payments company",
    "regtech",
    # healthtech
    "healthtech", "health tech", "digital health", "healthcare technology",
    "medtech",
    # infrastructure
    "critical infrastructure", "infrastructure investment", "major projects",
    "capital projects", "public infrastructure",
]

SECTOR_KEYWORDS = SECTOR_KEYWORDS_CORE + SECTOR_KEYWORDS_BROAD

# Phrases that hard auto-reject a listing (dropped from the digest entirely, not
# just flagged). Keep this list to phrases that reliably mean "must be a US person
# / physically US-based" — "no visa sponsorship" is deliberately excluded: it's
# generic boilerplate about not sponsoring US work visas and doesn't disqualify a
# Canadian working remotely from Canada, so including it here would silently drop
# perfectly good remote roles.
LOCATION_REJECT_PHRASES = [
    "must be authorized to work in the united states",
    "us citizens only",
    "us-based candidates only",
    "must reside in the united states",
    # Ruled out for real on a Compass Canada posting: mandatory French/English
    # bilingualism paired with Eastern Canada travel — not a fit regardless of
    # how strong the role otherwise is.
    "fluently bilingual",
    "must be bilingual in french and english",
    "bilingualism (french and english) is required",
]

# Phrases that confirm a listing IS Canada-eligible (used to boost confidence, not required)
LOCATION_ACCEPT_PHRASES = [
    "remote - canada", "remote, canada", "us & canada", "us and canada",
    "canada", "vancouver", "british columbia", "remote - north america",
]

# Sources that are inherently Canada-based by construction (a Canadian jobs board /
# the federal job registry) — their postings rarely say the literal word "Canada"
# (e.g. "Toronto (ON)", "Nova Scotia"), so phrase-matching alone would wrongly leave
# them in the "unclear" bucket. filters.py treats any job from these sources as
# location-confirmed without needing an accept-phrase hit.
CANADA_NATIVE_SOURCES = {"GoodWork.ca", "Job Bank Canada"}

# Comp is judged in CAD. Scraped comp strings (Workable/Greenhouse/Remote Rocketship)
# are almost always USD since the employers are US entities; a string is only
# treated as already-CAD if "CAD"/"CDN"/"C$" appears in it or in the job's full
# text (e.g. a GoodWork.ca Canadian listing). USD amounts are converted to CAD
# with FX_USD_TO_CAD below — approximate, revisit periodically.
FX_USD_TO_CAD = 1.38
MIN_COMP_CAD = 120_000       # Track A hard floor — below this (when comp IS listed), the job is dropped
IDEAL_COMP_CAD_LOW = 150_000
IDEAL_COMP_CAD_HIGH = 180_000
# Track B (product marketing) trades comp for equity/flexibility/experience —
# a much lower floor, per the brief ("as low as $80,000 CAD, not below").
MIN_COMP_CAD_PRODUCT_MARKETING = 80_000
# Listings with no comp listed at all are kept (can't apply the floor to an unknown
# number) but flagged "comp unknown" and scored as a partial/unclear match.

# --- Sources ---
# Each source needs its own fetch function in sources.py.
# Watchlist companies use their ATS's public job-board JSON/HTML endpoint directly —
# more reliable than scraping aggregator sites.
WATCHLIST_COMPANIES = {
    # company_name: (ats_type, ats_slug)
    # Confirmed live against each company's public ATS API 2026-09-11.
    "Renew Home": ("workable", "renewhome"),
    "Moment Energy": ("greenhouse", "momentenergy"),
    # General Fusion recruits via ADP Workforce Now, not Greenhouse — "generalfusion"
    # 404s against the Greenhouse API. ADP's careers page is a JS SPA with no static
    # job data (https://workforcenow.adp.com/.../recruitment.html?cid=3196ba6f-d49c-4493-9290-3d91489bdfa9&ccId=19000101_000001),
    # so it needs its own fetcher (sources.py has no "adp" handler yet) — left out of
    # the watchlist until that's built rather than silently 404ing every run.
    #
    # Foresight Canada (cleantech accelerator, Track C source) confirmed 2026-09-29
    # to run its careers page on Rise People, not Greenhouse/Workable either —
    # https://careers.risepeople.com/foresightcanada/en/... (e.g. job ids 16130,
    # 7360). sources.py has no "risepeople" fetcher yet — same documented-gap
    # pattern as General Fusion above, left out until that's built.
}

SOURCES_ENABLED = {
    "remote_rocketship": True,
    "goodwork_ca": True,
    "jobbank_canada": True,   # Canada's official job board — confirmed live 2026-09-11
    "brookfield_renewable": True,  # UltiPro board, reverse-engineered — confirmed live 2026-09-11
    "wellfound": True,  # startup job board, Vancouver — confirmed live 2026-09-11
    "fusion_energy_base": True,  # fusion-sector jobs directory — confirmed live 2026-09-11
    "climatebase": False,  # started returning 403 Forbidden as of 2026-09-29 (bot-blocked) —
    # disabled rather than left erroring every run; re-enable if/when it's worth
    # building around (an API key, or a headless-browser fetch) instead of a
    # plain requests.get().
    "climatetechlist": False,  # JS-rendered; needs Playwright/Selenium or an API — off by default
    "pac_org": True,  # Public Affairs Council jobs board — confirmed live 2026-09-29
    # Not added: CIRI's Career Hub is member-login-gated (not scraping around
    # that); Product Marketing Alliance's jobs.* subdomain from the brief no
    # longer resolves (site restructured); Hill Times Careers and Foresight's
    # Rise People board are both AJAX/SPA-driven with no listings in the
    # initial HTML — same class of work as Brookfield's UltiPro reverse-
    # engineering, not done yet.
    "watchlist_companies": True,
}

# Search terms tried against Job Bank Canada each run — each is a separate
# session-bound search+RSS round trip (see fetch_jobbank_canada in sources.py).
JOBBANK_QUERIES = [
    "communications director", "director of communications", "investor relations",
    "government relations", "stakeholder relations", "chief of staff",
    "product marketing",
]

# --- Storage ---
SEEN_JOBS_FILE = "seen_jobs.json"
LAST_RUN_FILE = "last_run.json"  # date of the last completed run — see main.py's catch-up window
LAST_MATCHES_FILE = "last_matches.json"  # cache of the last non-empty match set, resent on a quiet day

# --- Email ---
# Deliberately EMAIL_ENABLED = False in this cloud copy — no SMTP password is
# stored here at all. With it False, main.py prints the digest to stdout
# instead of emailing (see emailer.py's send_digest). The cloud Routine's own
# prompt is responsible for reading that stdout output and sending it via the
# user's Gmail MCP connector instead of smtplib — no credential to leak.
# The LOCAL copy of this repo (~/job-agent, not this one) is the one with
# real SMTP settings, used by the local cron job; never merge that version's
# email block back into what gets pushed here.
EMAIL_ENABLED = False
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "jared.fisk@gmail.com"
SMTP_APP_PASSWORD = ""
EMAIL_TO = "jared.fisk@gmail.com"
EMAIL_FROM_NAME = "Job Alert Agent"
