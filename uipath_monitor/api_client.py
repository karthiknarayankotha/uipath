from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import Config

logger = logging.getLogger(__name__)


class OrchestratorClient:
    def __init__(self, cfg: Config, token: str) -> None:
        self._base = cfg.base_url
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )
        self._lookback_hours = cfg.lookback_hours

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, folder_id: int | None = None, **params: Any) -> dict:
        headers = {}
        if folder_id is not None:
            headers["X-UIPATH-OrganizationUnitId"] = str(folder_id)

        url = f"{self._base}{path}"

        for attempt in range(3):
            resp = self._session.get(url, params=params, headers=headers, timeout=30, verify=False)

            if resp.status_code == 429:
                # Parse wait time from response message, default to 15s
                wait = 15
                try:
                    msg = resp.json().get("message", "")
                    match = re.search(r"(\d+)\s*second", msg)
                    if match:
                        wait = int(match.group(1)) + 2
                except Exception:
                    pass
                logger.info("Rate limited — waiting %ds (attempt %d/3)", wait, attempt + 1)
                time.sleep(wait)
                continue

            if resp.status_code == 404:
                logger.warning("404 for %s — skipping", url)
                return {}
            if not resp.ok:
                # 400 with errorCode 1100 = no access to folder — skip silently
                try:
                    body = resp.json()
                    if body.get("errorCode") == 1100:
                        logger.debug("No access to folder for %s — skipping", url)
                        return {}
                except Exception:
                    pass
                raise RuntimeError(
                    f"API error {resp.status_code} for {url}\nBody: {resp.text}"
                )
            return resp.json()

        raise RuntimeError(f"Rate limit exceeded after 3 retries for {url}")

    def _since_timestamp(self) -> str:
        """ISO 8601 UTC timestamp for lookback window."""
        since = datetime.now(timezone.utc) - timedelta(hours=self._lookback_hours)
        return since.strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_folders(self) -> list[dict]:
        """Return all Orchestrator folders in the tenant."""
        data = self._get("/odata/Folders", **{"$select": "Id,FullyQualifiedName", "$top": 200})
        return data.get("value", [])

    def get_failed_jobs(self, folder: dict) -> list[dict]:
        """Return faulted or failed jobs in the given folder for the lookback window."""
        since = self._since_timestamp()
        data = self._get(
            "/odata/Jobs",
            folder_id=folder["Id"],
            **{
                "$filter": f"(State eq 'Faulted' or State eq 'Stopped') and EndTime ge {since}",
                "$select": "Id,Key,ReleaseName,State,StartTime,EndTime,HostMachineName,Info,JobError,OrganizationUnitFullyQualifiedName",
                "$orderby": "EndTime desc",
                "$top": 200,
            },
        )
        return data.get("value", [])

    def get_total_job_count(self, folder: dict) -> int:
        """Return total number of jobs (any state) in the lookback window for the folder."""
        since = self._since_timestamp()
        data = self._get(
            "/odata/Jobs",
            folder_id=folder["Id"],
            **{
                "$filter": f"EndTime ge {since}",
                "$count": "true",
                "$top": 0,
            },
        )
        return data.get("@odata.count", 0)

    def get_job_logs(self, job_key: str, folder_id: int) -> list[dict]:
        """Return the most recent error-level log entries for a job."""
        data = self._get(
            "/odata/RobotLogs",
            folder_id=folder_id,
            **{
                "$filter": f"JobKey eq {job_key} and Level eq 'Error'",
                "$orderby": "TimeStamp desc",
                "$select": "TimeStamp,Message,Level",
                "$top": 5,
            },
        )
        return data.get("value", [])
