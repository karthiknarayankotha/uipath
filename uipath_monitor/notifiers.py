from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from config import Config

logger = logging.getLogger(__name__)


def send_email(cfg: Config, html_body: str) -> None:
    """Send HTML report via SMTP (STARTTLS)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"UiPath Daily Automation Health Report — {cfg.tenant_name}"
    msg["From"] = cfg.report_from_email
    msg["To"] = ", ".join(cfg.report_to_emails)

    plain_fallback = (
        "Your email client does not support HTML. "
        "Please view this report in an HTML-capable email client."
    )
    msg.attach(MIMEText(plain_fallback, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(cfg.smtp_user, cfg.smtp_password)
        smtp.sendmail(cfg.report_from_email, cfg.report_to_emails, msg.as_string())

    logger.info("Email sent to %s", cfg.report_to_emails)


def send_teams(cfg: Config, card: dict) -> None:
    """Post Adaptive Card to a Teams channel via incoming webhook."""
    resp = requests.post(cfg.teams_webhook_url, json=card, timeout=30)
    if resp.status_code not in (200, 202):
        resp.raise_for_status()
    logger.info("Teams notification sent (HTTP %s)", resp.status_code)
