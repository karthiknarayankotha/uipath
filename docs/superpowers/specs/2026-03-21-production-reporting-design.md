# Design: Production-Scoped Reporting

**Date:** 2026-03-21
**Status:** Approved

---

## Overview

Extend the existing UiPath Automation Health Report with two new Production-specific sections:

1. **Production Faulted Jobs** — all faulted/stopped jobs scoped to Production subfolders only
2. **Production System Exceptions** — all jobs (any state) from Production subfolders in the last 24h that resulted in a system exception (non-business exception)

Both sections are appended to the existing HTML report and delivered via the same email/Teams notification.

---

## Scope

- "Production subfolders" = any folder where `FullyQualifiedName` starts with `"Production"` (e.g. `Production\CHOP_Auth`, `Production\CHOP_CaseManagement`)
- The existing all-folders faulted jobs section remains unchanged
- No new config variables or files are introduced

---

## Architecture

### Files changed

| File | Change |
|------|--------|
| `api_client.py` | Add `get_all_jobs(folder)` method |
| `main.py` | Filter Production folders, call new method, pass data to report builder |
| `report_builder.py` | Add two new HTML table sections |

### No new files needed.

---

## Data Flow

```
get_folders()
    └─► filter where FullyQualifiedName.startswith("Production")
            └─► production_folders

existing loop (all folders)
    └─► failed_jobs (unchanged)

filter failed_jobs where folder_name starts with "Production"
    └─► production_faulted_jobs  [Req 1]

for each production_folder:
    get_all_jobs(folder)
        └─► filter where JobError present AND type not "BusinessRuleException"
                └─► production_sys_exceptions  [Req 2]

build_html_report(failed_jobs, production_faulted_jobs, production_sys_exceptions, ...)
```

---

## Component Details

### `api_client.py` — `get_all_jobs(folder)`

- Calls `GET /odata/Jobs` with no state filter
- Filter: `EndTime ge {since}` (last 24h)
- Selects: `Id, Key, ReleaseName, State, StartTime, EndTime, HostMachineName, Info, JobError, OrganizationUnitFullyQualifiedName`
- Returns all jobs regardless of state (Successful, Faulted, Stopped, etc.)
- `$top`: 500

### `main.py`

- After `get_folders()`, derive `production_folders` by filtering on `FullyQualifiedName.startswith("Production")`
- After existing loop, filter `failed_jobs` into `production_faulted_jobs`
- Loop over `production_folders`, call `get_all_jobs()`, collect those where:
  - `job.get("JobError")` is not empty/null
  - Exception type does not contain `"BusinessRuleException"`
- Pass both lists to `build_html_report()`

### `report_builder.py` — new HTML sections

**Section 1 — Production Faulted Jobs**
- Header: `"Production — Faulted Jobs"`
- Columns: Process, Folder, Robot/Machine, Start, End, State, Error
- Styled identically to existing faulted jobs table
- Shows "All clear" message if empty

**Section 2 — Production System Exceptions (Last 24h)**
- Header: `"Production — System Exceptions (Last 24h)"`
- Columns: Process, Folder, Robot/Machine, Start, End, State, Exception Type, Error Message
- Exception Type extracted from `JobError.type` if present, else `"Unknown"`
- Shows "None detected" message if empty

---

## Error Handling

- `get_all_jobs()` follows the same retry/rate-limit/404 pattern as `get_failed_jobs()`
- If a folder returns no data, it is skipped silently (consistent with existing behaviour)
- System exception filtering is done client-side after API response — no additional API calls

---

## Testing

- Manually run against the tenant and verify:
  - Section 1 only shows Production subfolder jobs (not Shared, UAT, Testing)
  - Section 2 only shows jobs with a non-business `JobError`
  - Existing all-folders section is unaffected
  - "All clear" / "None detected" messages appear correctly when no data
