from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config import Config


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return iso


def _health_color(pct: float) -> str:
    if pct >= 95:
        return "#28a745"
    if pct >= 80:
        return "#ffc107"
    return "#dc3545"


# ---------------------------------------------------------------------------
# HTML report (email body)
# ---------------------------------------------------------------------------

_HTML_STYLE = """
<style>
  body { font-family: Arial, sans-serif; color: #333; }
  h2 { color: #0063B1; }
  .summary { background: #f4f4f4; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; }
  .all-clear { background: #d4edda; color: #155724; padding: 14px 16px; border-radius: 6px;
               font-size: 1.1em; font-weight: bold; }
  table { border-collapse: collapse; width: 100%; font-size: 0.9em; }
  th { background: #0063B1; color: #fff; padding: 8px 10px; text-align: left; }
  td { padding: 7px 10px; border-bottom: 1px solid #ddd; vertical-align: top; }
  tr:nth-child(even) td { background: #f9f9f9; }
  .state-faulted { color: #dc3545; font-weight: bold; }
  .state-failed  { color: #c82333; font-weight: bold; }
  .logs { font-family: monospace; font-size: 0.82em; color: #555;
          white-space: pre-wrap; word-break: break-all; }
</style>
"""


def build_html_report(failed_jobs: list[dict], total_count: int, cfg: Config) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fail_count = len(failed_jobs)
    success_count = max(total_count - fail_count, 0)
    pct = (success_count / total_count * 100) if total_count else 100.0
    color = _health_color(pct)

    html_parts: list[str] = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        _HTML_STYLE,
        "</head><body>",
        f"<h2>UiPath Automation Health Report</h2>",
        f"<p>Tenant: <strong>{cfg.account_name} / {cfg.tenant_name}</strong> &nbsp;|&nbsp; "
        f"Generated: {now} &nbsp;|&nbsp; Window: last {cfg.lookback_hours}h</p>",
        "<div class='summary'>",
        f"<strong>Total jobs:</strong> {total_count} &nbsp;&nbsp; "
        f"<strong>Successful:</strong> {success_count} &nbsp;&nbsp; "
        f"<strong>Faulted/Failed:</strong> {fail_count} &nbsp;&nbsp; "
        f"<strong>Success rate:</strong> <span style='color:{color}'>{pct:.1f}%</span>",
        "</div>",
    ]

    if not failed_jobs:
        html_parts.append(
            "<div class='all-clear'>&#10003; All automations completed successfully in the last "
            f"{cfg.lookback_hours} hours.</div>"
        )
    else:
        html_parts += [
            "<h3>Faulted / Failed Jobs</h3>",
            "<table>",
            "<tr><th>Process</th><th>Folder</th><th>Robot / Machine</th>"
            "<th>Start</th><th>End</th><th>State</th><th>Error</th><th>Exception Logs</th></tr>",
        ]
        for job in failed_jobs:
            state = job.get("State", "")
            state_cls = f"state-{state.lower()}"
            logs_html = ""
            for log in job.get("logs", []):
                ts = _fmt_dt(log.get("TimeStamp"))
                msg = log.get("Message", "").replace("<", "&lt;").replace(">", "&gt;")
                logs_html += f"[{ts}] {msg}\n"
            job_error = job.get("JobError") or {}
            raw_error = (
                job_error.get("message")
                or job_error.get("details")
                or job.get("Info")
                or "—"
            )
            error_msg = raw_error.replace("<", "&lt;").replace(">", "&gt;")

            html_parts.append(
                f"<tr>"
                f"<td>{job.get('ReleaseName', '—')}</td>"
                f"<td>{job.get('folder_name') or job.get('OrganizationUnitFullyQualifiedName', '—')}</td>"
                f"<td>{job.get('HostMachineName', '—')}</td>"
                f"<td>{_fmt_dt(job.get('StartTime'))}</td>"
                f"<td>{_fmt_dt(job.get('EndTime'))}</td>"
                f"<td class='{state_cls}'>{state}</td>"
                f"<td>{error_msg}</td>"
                f"<td><div class='logs'>{logs_html.strip() or '—'}</div></td>"
                f"</tr>"
            )
        html_parts.append("</table>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# Teams Adaptive Card
# ---------------------------------------------------------------------------

def build_teams_card(failed_jobs: list[dict], total_count: int, cfg: Config) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fail_count = len(failed_jobs)
    success_count = max(total_count - fail_count, 0)
    pct = (success_count / total_count * 100) if total_count else 100.0

    if fail_count == 0:
        header_text = f"✅ All Clear — {cfg.tenant_name}"
        header_color = "Good"
        summary_text = (
            f"All **{total_count}** automation(s) completed successfully "
            f"in the last {cfg.lookback_hours} hours."
        )
    else:
        header_text = f"🚨 {fail_count} Automation(s) Failed — {cfg.tenant_name}"
        header_color = "Attention"
        summary_text = (
            f"**{fail_count}** of **{total_count}** job(s) faulted or failed "
            f"(success rate: {pct:.1f}%). Last {cfg.lookback_hours}h window. Generated: {now}"
        )

    body: list[dict] = [
        {
            "type": "TextBlock",
            "text": header_text,
            "size": "Large",
            "weight": "Bolder",
            "color": header_color,
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": summary_text,
            "wrap": True,
        },
    ]

    for job in failed_jobs:
        logs_text = "\n".join(
            f"[{_fmt_dt(l.get('TimeStamp'))}] {l.get('Message', '')}"
            for l in job.get("logs", [])
        )
        job_error = job.get("JobError") or {}
        error_text = (
            job_error.get("message")
            or job_error.get("details")
            or job.get("Info")
            or "—"
        )
        facts = [
            {"title": "Process", "value": job.get("ReleaseName", "—")},
            {"title": "Folder", "value": job.get("folder_name") or job.get("OrganizationUnitFullyQualifiedName", "—")},
            {"title": "Robot/Machine", "value": job.get("HostMachineName", "—")},
            {"title": "State", "value": job.get("State", "—")},
            {"title": "Start", "value": _fmt_dt(job.get("StartTime"))},
            {"title": "End", "value": _fmt_dt(job.get("EndTime"))},
            {"title": "Error", "value": error_text},
        ]
        if logs_text:
            facts.append({"title": "Exception Logs", "value": logs_text})

        body += [
            {"type": "separator"},
            {"type": "FactSet", "facts": facts},
        ]

    # Teams Adaptive Card wrapped in the O365 connector message format
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body,
                },
            }
        ],
    }
