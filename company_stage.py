"""
Best-effort company stage/maturity classification for a job listing.

This is NOT a valuation lookup — none of sources.py's fetch functions expose
real valuation figures, and this module never invents one for a specific
company. What it does: infer a stage label from whatever signal a source
actually provides (funding round type, employee count, founding year), and
attach a *typical* valuation range for that stage as rough context — framed
as "companies at this stage are typically worth X", never as a claim about
the specific company. Only Remote Rocketship's data (company.foundedYear /
fundingData / employeeRange) supports funding-based inference; everything
else falls back to KNOWN_STAGE_OVERRIDES (hand-verified, kept deliberately
small) or "Unknown".
"""

CURRENT_YEAR = 2026

# Remote Rocketship's fundingData list is newest-first, so the first entry
# present is treated as the most authoritative signal of current stage.
_FUNDING_STAGE_LABELS = [
    (("post-ipo equity", "post-ipo debt", "ipo"), "Public / Post-IPO (typically $1B+)"),
    (("private equity round", "private equity"), "Private Equity / Late Growth (typically $500M-$1B+)"),
    (("secondary market",), "Late-Stage / Secondary Market Activity (typically $500M+)"),
    (("series g", "series f", "series e"), "Series E+ / Late-Stage Venture (typically $250M-$1B)"),
    (("series d",), "Series D / Growth Stage (typically $100M-$500M)"),
    (("series c",), "Series C / Growth Stage (typically $50M-$250M)"),
    (("series b",), "Series B / Early Growth (typically $25M-$100M)"),
    (("series a",), "Series A / Early Stage (typically $5M-$50M)"),
    (("seed round", "seed"), "Seed Stage (typically <$20M)"),
    (("angel round", "angel"), "Angel / Pre-Seed (typically <$10M)"),
    (("venture round",), "Early-Stage Venture (round type doesn't pin down stage)"),
    (("grant round", "grant"), "Grant-Funded (non-dilutive, stage varies)"),
    (("debt financing", "convertible note"), "Debt/Bridge Financing (stage varies)"),
]

# Companies whose public/maturity status is well-established, verifiable fact
# (ticker, IPO date) — for sources that expose no funding data at all. Keep
# this list small and only add companies we're confident about; the fallback
# for everyone else is "Unknown", not a guess.
KNOWN_STAGE_OVERRIDES = {
    "brookfield renewable": "Public / Established (TSX & NYSE: BEP, multi-billion-dollar market cap)",
    "innergex": "Public / Established (TSX: INE, publicly traded since 2010)",
    "innergex renewable energy": "Public / Established (TSX: INE, publicly traded since 2010)",
    "ballard power": "Public / Established (TSX & NASDAQ: BLDP, publicly traded since 1993)",
    "ballard power systems": "Public / Established (TSX & NASDAQ: BLDP, publicly traded since 1993)",
    "nano one": "Public / Established (TSX: NANO, publicly traded since 2016)",
    "nano one materials": "Public / Established (TSX: NANO, publicly traded since 2016)",
    "renewhome": "Growth Stage (2023 spinout of Google Nest's energy business, well-funded, valuation not publicly disclosed)",
    "renew home": "Growth Stage (2023 spinout of Google Nest's energy business, well-funded, valuation not publicly disclosed)",
    "momentenergy": "Early Stage (BC battery-storage startup, est. 2018, Seed/Series A range — not publicly disclosed)",
    "moment energy": "Early Stage (BC battery-storage startup, est. 2018, Seed/Series A range — not publicly disclosed)",
}


def classify_stage(company_name, founded_year=None, funding_data=None, employee_range=None):
    """
    Priority: known override > latest funding round type > employee-count/
    age fallback > "Unknown". `funding_data` is the raw list of
    {"fundingType": ...} dicts as returned by Remote Rocketship.
    """
    key = (company_name or "").strip().lower()
    if key in KNOWN_STAGE_OVERRIDES:
        return KNOWN_STAGE_OVERRIDES[key]

    if funding_data:
        latest_type = (funding_data[0].get("fundingType") or "").strip().lower()
        for markers, label in _FUNDING_STAGE_LABELS:
            if latest_type in markers:
                return label
        if latest_type:
            return f"Funded ({funding_data[0].get('fundingType')}) — stage unclear from round type"

    if employee_range:
        try:
            low = int(str(employee_range).split(",")[0])
        except (ValueError, TypeError):
            low = None
        if low is not None and low >= 1000:
            return "Established / Large Enterprise (1000+ employees, funding stage unknown)"

    if founded_year:
        try:
            age = CURRENT_YEAR - int(founded_year)
        except (ValueError, TypeError):
            age = None
        if age is not None:
            if age <= 2:
                return f"Early Stage (founded ~{founded_year}, <2 yrs old, funding stage unknown)"
            if age <= 5:
                return f"Growth Stage (founded ~{founded_year}, {age} yrs old, funding stage unknown)"
            if age <= 10:
                return f"Established Growth (founded ~{founded_year}, {age} yrs old, funding stage unknown)"
            return f"Established (founded ~{founded_year}, {age}+ yrs old)"

    return "Unknown — no company-stage data available from this source"
