"""Composes and sends the daily digest email."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import (
    EMAIL_ENABLED, SMTP_HOST, SMTP_PORT, SMTP_USERNAME,
    SMTP_APP_PASSWORD, EMAIL_TO, EMAIL_FROM_NAME,
)


def compose_digest(strong_matches, imperfect_matches, carried_over_date=None):
    if not strong_matches and not imperfect_matches:
        return None  # nothing to send at all — not even a cached carry-over

    lines = ["<h2>Job Alert Digest</h2>"]

    if carried_over_date:
        lines.append(
            f"<p style='color:#a55'><b>No new matches today.</b> "
            f"These are your matches from {carried_over_date}, resent so you always "
            f"have something to review — ignore or delete freely.</p>"
        )

    if strong_matches:
        lines.append("<h3>Strong matches</h3><ul>")
        for job, score, reasons in strong_matches:
            lines.append(_format_job_html(job, score, reasons))
        lines.append("</ul>")

    if imperfect_matches:
        lines.append("<h3>Imperfect matches (worth a look)</h3><ul>")
        for job, score, reasons in imperfect_matches:
            lines.append(_format_job_html(job, score, reasons))
        lines.append("</ul>")

    return "\n".join(lines)


def _format_job_html(job, score, reasons):
    title = job.get("title", "Untitled")
    company = job.get("company") or "Unknown company"
    url = job.get("url", "")
    source = job.get("source", "")
    stage = job.get("company_stage") or "Unknown"
    reason_str = "; ".join(reasons)
    return (
        f"<li><b>{title}</b> — {company} — <b>{score}/100</b> "
        f"(<a href='{url}'>view posting</a>, via {source})<br>"
        f"<small>Stage: {stage}</small><br>"
        f"<small>{reason_str}</small></li>"
    )


def send_digest(html_body, subject="Your daily job alert digest"):
    if not EMAIL_ENABLED:
        print("EMAIL_ENABLED is False in config.py — printing digest instead of sending:\n")
        print(html_body)
        return

    if not (SMTP_USERNAME and SMTP_APP_PASSWORD and EMAIL_TO):
        raise RuntimeError(
            "Email is enabled but SMTP_USERNAME / SMTP_APP_PASSWORD / EMAIL_TO "
            "aren't all set in config.py."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{EMAIL_FROM_NAME} <{SMTP_USERNAME}>"
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_APP_PASSWORD)
        server.sendmail(SMTP_USERNAME, EMAIL_TO, msg.as_string())

    print(f"Digest sent to {EMAIL_TO}")
