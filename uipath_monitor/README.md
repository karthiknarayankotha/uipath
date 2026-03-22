# UiPath Cloud Daily Health Monitor

A Python script that queries UiPath Cloud Orchestrator daily for faulted/failed automation jobs and sends a formatted HTML report to **Microsoft Teams** and **Email (SMTP)**.

---

## Setup

### 1. Install dependencies

```bash
cd uipath_monitor
pip install -r requirements.txt
```

### 2. Configure credentials

Copy `.env.example` to `.env` and fill in your values:

```bash
copy .env.example .env   # Windows
cp .env.example .env     # Mac/Linux
```

| Variable | Description |
|---|---|
| `UIPATH_ACCOUNT_NAME` | Your UiPath Cloud organization name (visible in the cloud.uipath.com URL) |
| `UIPATH_TENANT_NAME` | Tenant name (e.g. `DefaultTenant`) |
| `UIPATH_USERNAME` | Your UiPath Cloud login email |
| `UIPATH_PASSWORD` | Your UiPath Cloud password |
| `TEAMS_WEBHOOK_URL` | Incoming webhook URL from your Teams channel |
| `SMTP_HOST` | SMTP server (e.g. `smtp.office365.com`) |
| `SMTP_PORT` | SMTP port (587 for STARTTLS) |
| `SMTP_USER` | SMTP login username |
| `SMTP_PASSWORD` | SMTP login password |
| `REPORT_TO_EMAILS` | Comma-separated list of recipient emails |
| `REPORT_FROM_EMAIL` | Sender email address |
| `LOOKBACK_HOURS` | How far back to look (default: `24`) |

### 3. Test manually

```bash
python main.py
```

Check `logs/monitor.log` if something goes wrong.

### 4. Schedule (Windows Task Scheduler)

Run **PowerShell as Administrator**, then:

```powershell
.\setup_task_scheduler.ps1 -PythonExe "C:\Python311\python.exe" -RunAt "07:00"
```

This registers a task that fires daily at 07:00 and logs to `logs\monitor.log`.

---

## Troubleshooting

### Authentication fails

**Symptom:** `Authentication failed (400)` or `401 Unauthorized`

**Cause 1 — MFA is enabled** on your UiPath account. The username+password (ROPC) flow does not support MFA.

**Fix:** Create an External Application in UiPath Cloud:
1. Go to **cloud.uipath.com → Admin → External Applications → Add**
2. Choose **Confidential application**, grant scopes: `OR.Jobs OR.Robots OR.Folders OR.Monitoring`
3. Copy the **Client ID** and **Client Secret**
4. In `auth.py`, replace the `authenticate()` function body with:
   ```python
   payload = {
       "grant_type": "client_credentials",
       "client_id": cfg.username,      # store Client ID in UIPATH_USERNAME
       "client_secret": cfg.password,  # store Client Secret in UIPATH_PASSWORD
       "scope": "OR.Jobs OR.Robots OR.Folders OR.Monitoring",
   }
   ```

**Cause 2 — Wrong account/tenant name.** Check the URL when logged into cloud.uipath.com:
`https://cloud.uipath.com/{ACCOUNT_NAME}/{TENANT_NAME}/orchestrator_`

### Teams card not displaying

Make sure the webhook URL is an **Incoming Webhook** connector URL (from Teams channel settings → Connectors), not a Power Automate URL.

### Jobs not appearing

- Verify `LOOKBACK_HOURS` — set to `720` temporarily to see 30 days of history.
- Confirm the Orchestrator user has at least **View** permission on Jobs and Robot Logs in every folder.

---

## Report Samples

**Email** — HTML table with color-coded success rate, one row per failed job, exception log snippet in the last column.

**Teams** — Adaptive Card with red header on failures, green "All Clear" header when everything is healthy, facts block per failed job.
