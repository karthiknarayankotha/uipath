"""
UiPath Cloud Daily Automation Health Monitor
============================================
Run manually:   python main.py
Schedule:       Use setup_task_scheduler.ps1 to register a daily Windows Task
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=Warning, module="urllib3")

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/monitor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main() -> None:
    from config import load_config
    from auth import authenticate
    from api_client import OrchestratorClient
    from report_builder import build_html_report, build_teams_card
    from notifiers import send_email, send_teams

    logger.info("Starting UiPath health check")
    cfg = load_config()
    token = authenticate(cfg)
    client = OrchestratorClient(cfg, token)

    folders = client.get_folders()
    logger.info("Found %d folder(s)", len(folders))

    production_folders = [
        f for f in folders
        if f.get("FullyQualifiedName", "").startswith("Production")
    ]
    logger.info("Found %d Production subfolder(s)", len(production_folders))

    failed_jobs: list[dict] = []
    total_count = 0

    for folder in folders:
        folder_name = folder.get("FullyQualifiedName", folder["Id"])
        folder_id = folder["Id"]

        jobs = client.get_failed_jobs(folder)
        logger.info("Folder '%s': %d failed/faulted job(s)", folder_name, len(jobs))

        for job in jobs:
            job["logs"] = client.get_job_logs(job["Key"], folder_id)
            job["folder_name"] = folder_name

        failed_jobs.extend(jobs)
        total_count += client.get_total_job_count(folder)

    logger.info(
        "Summary: %d total jobs, %d faulted/failed",
        total_count,
        len(failed_jobs),
    )

    # Production-scoped: faulted jobs only
    production_faulted_jobs = [
        j for j in failed_jobs
        if j.get("folder_name", "").startswith("Production")
    ]

    # Production-scoped: system exceptions from all jobs
    production_sys_exceptions: list[dict] = []
    for folder in production_folders:
        folder_name = folder.get("FullyQualifiedName", str(folder["Id"]))
        jobs = client.get_all_jobs(folder)
        for job in jobs:
            job_error = job.get("JobError") or {}
            if not job_error:
                continue
            error_type = job_error.get("type", "")
            if "BusinessRuleException" not in error_type:
                job["folder_name"] = folder_name
                production_sys_exceptions.append(job)
    logger.info("Production system exceptions: %d", len(production_sys_exceptions))

    html = build_html_report(failed_jobs, total_count, cfg,
                             production_faulted_jobs, production_sys_exceptions)

    report_path = Path("logs/report_latest.html")
    report_path.write_text(html, encoding="utf-8")

    try:
        send_email(cfg, html)
        logger.info("Email sent to %s", cfg.report_to_emails)
    except Exception:
        logger.debug("Email skipped (not configured or failed)")

    try:
        card = build_teams_card(failed_jobs, total_count, cfg)
        send_teams(cfg, card)
        logger.info("Teams notification sent")
    except Exception:
        logger.debug("Teams skipped (not configured or failed)")

    logger.info("Report saved → %s", report_path.resolve())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)
