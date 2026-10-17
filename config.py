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
    # added 2026-10-16 — public affairs is in the brief but was never matched
    # (e.g. "Director, Government & External Relations" was silently dropped)
    "public affairs", "government affairs", "external relations",
    "stakeholder engagement", "community relations", "community engagement",
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
#
# Matching is whole-word (see _contains_any in filters.py), which is what makes
# short words like "mining", "tech", and "software" safe to use here: "mining"
# no longer hits "determining". Updated 2026-10-16 to add mining, industrial,
# construction, tech and startups on request; the comp floors in filters.py
# apply to every sector equally, so none of these loosen the salary rules.
SECTOR_KEYWORDS_CORE = [
    # energy / cleantech
    "energy", "climate", "cleantech", "clean tech", "clean technology",
    "climate tech", "climatetech", "renewable", "renewables", "sustainability",
    "esg", "decarbonization", "decarbonisation", "clean energy", "green energy",
    "sustainable energy", "energy transition", "net zero", "net-zero",
    "low carbon", "low-carbon", "carbon capture", "carbon credits", "fusion",
    "battery", "battery storage", "energy storage", "hydrogen", "nuclear",
    "solar", "wind energy", "wind power", "hydroelectric", "hydropower",
    "geothermal", "electrification", "oil and gas", "lng", "power generation",
    "electric utility",
    # mining and resources
    "mining", "mineral", "minerals", "critical minerals", "mineral exploration",
    "metals", "copper", "lithium", "uranium", "nickel", "zinc", "rare earth",
    "rare earths", "natural resources", "resource sector", "mine site",
    # industrial
    "industrial", "manufacturing", "heavy industry", "skilled trades",
]

SECTOR_KEYWORDS_BROAD = [
    # tech / apps
    "tech", "technology sector", "technology industry", "software",
    "artificial intelligence", "machine learning", "cybersecurity",
    "semiconductor", "quantum", "data centre", "data center", "tech startup",
    "software company", "technology company", "tech company", "saas",
    "mobile app", "consumer app", "app development", "enterprise software",
    # construction
    "construction", "engineering and construction", "general contractor",
    "civil engineering", "building products", "real estate development",
    "infrastructure",
    # startups
    "startup", "start-up", "scale-up", "scaleup", "early-stage", "early stage",
    "venture-backed", "seed-funded", "series a", "series b", "series c",
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
    "canada", "canadian", "vancouver", "british columbia", "remote - north america",
    "remote (canada)", "canada remote", "canada (remote)", "canada-wide",
    "anywhere in canada", "across canada", "pan-canadian",
]

# Vancouver/BC — Jared lives in Vancouver, so these get the "local" tier and
# the top location score (tied with Canada-eligible remote). City names that
# collide with other places (Richmond VA, Surrey UK, Victoria AU, Delta, Langley
# VA) are only listed with a BC qualifier.
LOCAL_BC_PHRASES = [
    "vancouver", "burnaby", "british columbia", ", bc", "(bc)", "b.c.",
    "lower mainland", "metro vancouver", "greater vancouver", "north vancouver",
    "west vancouver", "coquitlam", "new westminster", "richmond, bc",
    "surrey, bc", "langley, bc", "delta, bc", "victoria, bc", "kelowna",
    "abbotsford", "nanaimo", "kamloops", "bc-based",
]

# Any of these in a job's title/location/description counts as "remote" for the
# Canada-remote tier; boards that are remote-only by definition are listed in
# REMOTE_NATIVE_SOURCES instead so their postings don't need to say it.
REMOTE_SIGNAL_PHRASES = [
    "remote", "work from home", "work from anywhere", "work remotely",
    "fully remote", "telecommute", "distributed team", "wfh",
]
REMOTE_NATIVE_SOURCES = {"Remote Rocketship", "Remote Rocketship (CA)"}

# Sources that are inherently Canada-based by construction (a Canadian jobs board /
# the federal job registry) — their postings rarely say the literal word "Canada"
# (e.g. "Toronto (ON)", "Nova Scotia"), so phrase-matching alone would wrongly leave
# them in the "unclear" bucket. filters.py treats any job from these sources as
# location-confirmed without needing an accept-phrase hit.
CANADA_NATIVE_SOURCES = {"GoodWork.ca", "Job Bank Canada", "BCjobs.ca"}

# Comp is judged in CAD. Scraped comp strings (Workable/Greenhouse/Remote Rocketship)
# are almost always USD since the employers are US entities; a string is only
# treated as already-CAD if "CAD"/"CDN"/"C$" appears in it or in the job's full
# text (e.g. a GoodWork.ca Canadian listing). USD amounts are converted to CAD
# with FX_USD_TO_CAD below — approximate, revisit periodically.
FX_USD_TO_CAD = 1.38
# Updated 2026-10-16: floor $100K CAD, ceiling $150K CAD. The $100K-$150K band
# is the target, so anything inside it gets full comp credit (IDEAL_LOW equals
# the floor). Comp ABOVE the ceiling is never dropped — more money isn't a
# problem — it's just noted in the digest as above the ceiling.
MIN_COMP_CAD = 100_000       # hard floor — below this (when comp IS listed), the job is dropped
IDEAL_COMP_CAD_LOW = 100_000
IDEAL_COMP_CAD_HIGH = 150_000
# Track B (product marketing) used to have its own lower $80K floor (the Sept
# 2026 brief's equity trade-off). The 2026-10-16 instruction was a single
# "floor needs to be 100K", so both tracks share it; set this back to 80_000 to
# restore the Track B exception.
MIN_COMP_CAD_PRODUCT_MARKETING = 100_000
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
    # Track B target company from the Sept 2026 brief — confirmed live 2026-09-30
    # via its careers page's embed script (clir.bamboohr.com/js/embed.js).
    "Clir Renewables": ("bamboohr", "clir"),
    # BC-based tech companies added 2026-10-16 to broaden Canadian/British Columbia
    # coverage — confirmed live against each company's public Greenhouse board API.
    # "company" field in the resulting job dicts is the ats_slug (lowercase), which
    # is enough for filters.py's sector/keyword matching against full_text.
    "Later": ("greenhouse", "later"),  # Vancouver — has had Track A titles (e.g. "Senior Manager, PR")
    "Hootsuite": ("greenhouse", "hootsuite"),  # Vancouver
    "Thinkific": ("greenhouse", "thinkific"),  # Vancouver
    "Unbounce": ("greenhouse", "unbounce"),  # Vancouver
    "MetaLab": ("greenhouse", "metalab"),  # Victoria, BC
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
    #
    # Checked against the brief's other named targets 2026-09-30, none added:
    # Voltus, Loopio, Climatiq, Pani Energy — no company-run ATS found (search-
    # engine-indexable job boards only, e.g. Indeed/Glassdoor, not scrapable
    # the way a direct ATS is). [Correction 2026-10-16: Voltus actually does have
    # a public Lever board — api.lever.co/v0/postings/voltus — confirmed live,
    # 20 jobs returned. Not wired up: sources.py has no Lever fetcher yet, same
    # documented-gap pattern as ADP/Rise People above. Also not BC-based (US),
    # so left out of this round, which focused on Canadian/BC coverage.]
    # Teck Resources, Ivanhoe Mines, Lithium Americas,
    # D-Wave Quantum, Hill+Knowlton Canada — each confirmed to exist but on a
    # different complex ATS per company (Workday, Rippling, a custom "Simplify
    # HR" portal, iCIMS) that would each need its own UltiPro-style reverse-
    # engineering effort, not done yet.
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
    "remote_rocketship_ca": True,  # Remote Rocketship's /ca/ feed — Canada-eligible remote, 2026-10-16
    "bcjobs": True,  # BC-focused board, robots.txt allows crawling — added 2026-10-16
    "odgers_berndtson": True,  # exec search firm's public opportunities board — confirmed live 2026-09-30
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

# Vancouver/BC/Canada focus, added 2026-10-16. Each list is looped in main.py.
# Remote Rocketship /ca/ slugs were each checked live (communications,
# senior-communications, product-marketing return Canada-eligible results;
# government-relations and corporate-communications 404). Only the first ~20
# jobs per slug are reachable — its ?page=N pagination doesn't actually page.
RR_CA_QUERIES = ["senior-communications", "communications", "product-marketing"]
# Wellfound location pages fetched each run (see fetch_wellfound in sources.py).
# "vancouver" is the city page; "british-columbia" is the province page — confirmed
# 2026-10-16 to return a broader set of startups than "vancouver" alone (5 pages vs.
# 4, including companies outside Vancouver proper e.g. Victoria/Burnaby-based ones).
# Overlap between the two is expected and harmless — main.py dedupes by job URL.
WELLFOUND_LOCATIONS = ["vancouver", "british-columbia"]
JOBBANK_VANCOUVER_QUERIES = [
    "communications director", "director of communications", "government relations",
    "investor relations", "stakeholder relations", "external affairs",
    "corporate affairs", "product marketing", "chief of staff",
]
BCJOBS_QUERIES = [
    "communications director", "director communications", "investor relations",
    "government relations", "stakeholder relations", "external affairs",
    "corporate affairs", "product marketing", "chief of staff",
]

# --- Storage ---
SEEN_JOBS_FILE = "seen_jobs.json"
LAST_RUN_FILE = "last_run.json"  # date of the last completed run — see main.py's catch-up window
LAST_MATCHES_FILE = "last_matches.json"  # cache of the last non-empty match set, resent on a quiet day

# --- Email ---
# Deliberately EMAIL_ENABLED = False in this cloud copy — no SMTP password is
# stored here at all. With it False, main.py prints the digest to stdout
# instead of emailing (see emailer.py's send_digest), and writes it to
# pending_digest.json too — the cloud Routine's own prompt reads that file
# and sends it via the Gmail MCP connector instead of smtplib, no credential
# to leak. The LOCAL copy of this repo (~/job-agent, not this one) is the one
# with real SMTP settings, used by the local cron job; never copy that
# version's email block back into what gets pushed here.
EMAIL_ENABLED = False
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "jared.fisk@gmail.com"
SMTP_APP_PASSWORD = ""
EMAIL_TO = "jared.fisk@gmail.com"
EMAIL_FROM_NAME = "Job Alert Agent"
