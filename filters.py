"""
Applies the benchmark filter and match score to a raw job listing dict
(see sources.py for shape).

evaluate_job(job) -> (is_match, is_strong_match, score, reasons)

is_match = passes enough criteria to include in the digest at all
is_strong_match = a full match on the benchmark, vs. an "imperfect but worth seeing" one
score = 0-100 fit estimate built from the same signals as is_match/is_strong_match
    (sector alignment, seniority, Canada/remote eligibility, comp) — a keyword-rule
    proxy for fit, not a substitute for actually reading the posting
reasons = human-readable notes shown in the digest (e.g. "comp unknown")

Note: explicit US-citizens-only / must-be-US-authorized language is a hard reject
(is_match=False, score=0) — those listings never reach the digest, not even as imperfect.
"""

import re
from config import (
    TITLE_KEYWORDS_STRATEGIC_COMMS, TITLE_KEYWORDS_PRODUCT_MARKETING,
    SENIORITY_KEYWORDS, SECTOR_KEYWORDS_CORE, SECTOR_KEYWORDS_BROAD,
    LOCATION_REJECT_PHRASES, LOCATION_ACCEPT_PHRASES, CANADA_NATIVE_SOURCES,
    LOCAL_BC_PHRASES, REMOTE_SIGNAL_PHRASES, REMOTE_NATIVE_SOURCES,
    FX_USD_TO_CAD, MIN_COMP_CAD, IDEAL_COMP_CAD_LOW, IDEAL_COMP_CAD_HIGH,
    MIN_COMP_CAD_PRODUCT_MARKETING,
)


def _contains_any(text, phrases):
    """
    Phrases that start/end with a letter or digit must match whole words —
    plain substring matching made "mining" hit "determining", "app" hit
    "application", and "canada" hit "canadian". Phrases that start/end with
    punctuation (", bc", "(bc)", "sr.") skip the boundary on that side, since
    the neighbouring character is naturally a letter or digit.
    """
    text = text.lower()
    hits = []
    for phrase in phrases:
        p = phrase.lower()
        left = r"(?<![a-z0-9])" if p[0].isalnum() else ""
        right = r"(?![a-z0-9])" if p[-1].isalnum() else ""
        if re.search(left + re.escape(p) + right, text):
            hits.append(phrase)
    return hits


def evaluate_job(job):
    title = (job.get("title") or "").lower()
    desc = (job.get("raw_description") or "").lower()
    location = (job.get("location") or "").lower()
    company = (job.get("company") or "").lower()
    # company is included so a watchlist entry like "Moment Energy" gets sector
    # credit for its own name even when the job title itself doesn't say "energy"
    full_text = f"{title} {desc} {location} {company}"

    reasons = []

    # 1. Title relevance — two parallel tracks (see config.py): Track A is the
    # primary strategic-comms/IR/public-affairs target, Track B is product
    # marketing at startups (much lower comp floor, sector-agnostic — see the
    # TODO below). A title can only belong to one track for this job.
    strategic_hits = _contains_any(title, TITLE_KEYWORDS_STRATEGIC_COMMS)
    pm_hits = _contains_any(title, TITLE_KEYWORDS_PRODUCT_MARKETING)
    if not strategic_hits and not pm_hits:
        return False, False, 0, ["title doesn't match either track's keywords"]
    track = "strategic_comms" if strategic_hits else "product_marketing"
    reasons.append(f"track: {track} (matched {(strategic_hits or pm_hits)[0]!r})")

    # 2. Seniority
    seniority_hits = _contains_any(title, SENIORITY_KEYWORDS)
    if not seniority_hits:
        reasons.append("no explicit seniority keyword in title — check manually")

    # 3. Sector gate, track-dependent (implemented 2026-09-29 — this was a
    # TODO(human) that had been left unfinished, which crashed every run
    # with NameError: core_hits/broad_hits were referenced later in this
    # function but never actually set. Also folds in the widened Track A
    # sector scope from the 2026-09 job-search brief: fintech, healthtech,
    # and infrastructure phrases were added to SECTOR_KEYWORDS_BROAD in
    # config.py, alongside the original energy/climate/tech/commodities set.
    core_hits = _contains_any(full_text, SECTOR_KEYWORDS_CORE)
    broad_hits = _contains_any(full_text, SECTOR_KEYWORDS_BROAD)
    local_hits = _contains_any(f"{location} {title} {company} {desc}", LOCAL_BC_PHRASES)
    sector_unknown = False

    # Sector is a scoring signal for both tracks (cloud decision 2026-09-30: a
    # hard sector gate was dropping legitimate senior comms/gov-relations roles
    # whose listing text just doesn't literally say "energy"/"climate"/etc.).
    # A sector match boosts the score via _score_job; no match is kept, scored lower.
    if core_hits or broad_hits:
        reasons.append(f"sector match: {(core_hits or broad_hits)[0]!r}")
    elif track == "strategic_comms":
        sector_unknown = True
        reasons.append("no target-sector signal found in the posting text — kept anyway, scored lower; check what the employer does")
    else:
        reasons.append("Track B — sector not required")

    # 4. Location — hard reject on explicit US-only/visa-required language
    reject_hits = _contains_any(full_text, LOCATION_REJECT_PHRASES)
    accept_hits = _contains_any(full_text, LOCATION_ACCEPT_PHRASES)
    is_canada_native = job.get("source") in CANADA_NATIVE_SOURCES

    if reject_hits:
        # Explicit US-only / must-be-US-authorized / visa-required language
        return False, False, 0, [f"location restriction found ({reject_hits[0]}) — not Canada-eligible"]

    # Geography tiers — Jared lives in Vancouver, so the target is Vancouver/BC
    # work OR Canada-eligible remote. Canada roles that are neither local nor
    # remote (e.g. onsite in Toronto) are kept but flagged, not rejected.
    remote_signal = (
        job.get("source") in REMOTE_NATIVE_SOURCES
        or bool(_contains_any(f"{location} {title} {desc}", REMOTE_SIGNAL_PHRASES))
    )
    canada_confirmed = bool(accept_hits) or is_canada_native

    is_strong_match = True
    if local_hits:
        geo_tier = "local_bc"
        reasons.append(f"local: Vancouver/BC ({local_hits[0]})")
    elif canada_confirmed and remote_signal:
        geo_tier = "canada_remote"
        reasons.append(f"Canada-eligible remote ({(accept_hits or [job.get('source')])[0]})")
    elif canada_confirmed:
        geo_tier = "canada_other"
        reasons.append(
            "Canada, but outside BC and not marked remote — likely onsite elsewhere, "
            "verify relocation/remote before applying"
        )
        is_strong_match = False
    else:
        # Hard requirement (cloud decision 2026-09-30): must be confirmed
        # remote-eligible or Canada/Vancouver/BC-based — an ambiguous listing is
        # dropped rather than kept for manual verification.
        return False, False, 0, [
            "not confirmed remote-eligible or Vancouver/BC/Canada-based — "
            "required, so dropped rather than kept as ambiguous"
        ]

    # 5. Comp — judged in CAD; the floor depends on track (Track B trades comp
    # for equity/experience, so its floor is much lower — see config.py). An
    # unknown comp can't be measured against a floor, so it's kept and flagged
    # instead of rejected.
    min_comp = MIN_COMP_CAD if track == "strategic_comms" else MIN_COMP_CAD_PRODUCT_MARKETING
    comp = job.get("comp")
    comp_cad = _extract_comp_cad(comp, full_text, is_canada_native) if comp else None
    if comp_cad is None:
        reasons.append("comp not listed — flagged as unknown, kept in digest")
        is_strong_match = False
    elif comp_cad < min_comp:
        return False, False, 0, [f"comp (~${comp_cad:,.0f} CAD) below the ${min_comp:,} CAD floor for {track}"]
    elif track == "strategic_comms" and comp_cad < IDEAL_COMP_CAD_LOW:
        reasons.append(f"comp meets the ${min_comp:,} CAD floor but below the ${IDEAL_COMP_CAD_LOW:,}+ ideal (~${comp_cad:,.0f} CAD)")
        is_strong_match = False
    elif track == "strategic_comms":
        above = " — above your ceiling, still shown" if comp_cad > IDEAL_COMP_CAD_HIGH else ""
        reasons.append(f"comp in your ${IDEAL_COMP_CAD_LOW:,}-${IDEAL_COMP_CAD_HIGH:,} CAD target band (~${comp_cad:,.0f} CAD){above}")
    else:
        reasons.append(f"comp meets the ${min_comp:,} CAD Track B floor (~${comp_cad:,.0f} CAD) — no upper target, comp is a trade-off vs. equity here")

    score = _score_job(
        sector_is_core=bool(core_hits),
        sector_unknown=sector_unknown,
        seniority_hit=bool(seniority_hits),
        geo_tier=geo_tier,
        comp_cad=comp_cad,
    )
    reasons.append(f"match score: {score}/100")

    return True, is_strong_match, score, reasons


LOCATION_POINTS = {
    "local_bc": 30,        # Vancouver/BC — where Jared lives
    "canada_remote": 30,   # remote and Canada-eligible — equally wanted
    "canada_other": 18,    # Canada but onsite elsewhere — needs relocation
    "unclear": 15,
}


def _score_job(sector_is_core, seniority_hit, geo_tier, comp_cad, sector_unknown=False):
    """
    0-100 fit estimate from the same signals evaluate_job already checked.
    Weights: sector 35 (core) / 20 (broad), seniority 15 (5 if absent — a
    soft signal, not a hard gate), location per LOCATION_POINTS (local BC and
    Canada-remote tie at 30), comp (CAD) 20 at/above the $150-180K ideal / 12
    between the floor and the ideal / 10 unknown. Below-floor comp never
    reaches this function (hard rejected earlier). Max is 100 for a
    core-sector, senior-titled, local-or-remote listing at/above the comp ideal.
    """
    score = 12 if sector_unknown else (35 if sector_is_core else 20)
    score += 15 if seniority_hit else 5
    score += LOCATION_POINTS[geo_tier]
    if comp_cad is None:
        score += 10
    elif comp_cad >= IDEAL_COMP_CAD_LOW:
        score += 20
    else:
        score += 12
    return min(score, 100)


def _extract_comp_value(comp_str):
    """
    Highest figure in a comp string, as a whole number. Handles "$155,000 -
    $185,000", "$60,000.00 annually" and the "k" shorthand ("$70k - $96k CAD").
    Anything under $10,000 (hourly rates, equity percentages) is ignored, so an
    hourly-only posting still reads as "comp unknown" rather than as a tiny salary.
    """
    if not comp_str:
        return None
    values = []
    for number, k in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([kK])?\b", comp_str):
        value = float(number.replace(",", ""))
        if k:
            value *= 1000
        if value >= 10_000:
            values.append(value)
    return int(max(values)) if values else None


def _extract_comp_cad(comp_str, full_text, is_canada_native=False):
    """
    Numeric comp value converted to CAD, assuming USD unless the text says
    otherwise OR the job is from a Canada-native source (job.gc.ca, GoodWork.ca)
    — those list comp in CAD without ever saying "CAD" (e.g. Job Bank's
    "$60,000.00 annually"), so source alone is enough to skip the FX conversion.
    """
    value = _extract_comp_value(comp_str)
    if value is None:
        return None
    # whole-word match only: a bare substring test treated "academic" and
    # "decade" as "cad". The comp string itself is checked too — Remote
    # Rocketship and Wellfound write "CAD" right in the salary.
    cad_marker = r"\b(cad|cdn)\b|c\$|ca\$"
    is_cad = (
        is_canada_native
        or bool(re.search(cad_marker, comp_str.lower()))
        or bool(re.search(cad_marker, full_text))
    )
    return float(value) if is_cad else value * FX_USD_TO_CAD
