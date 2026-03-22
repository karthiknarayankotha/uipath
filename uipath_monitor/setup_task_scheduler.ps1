# setup_task_scheduler.ps1
# Registers a daily Windows Scheduled Task to run the UiPath health monitor.
# Run this once as Administrator.

param(
    [string]$PythonExe   = "python",       # full path if python not on PATH, e.g. C:\Python311\python.exe
    [string]$ScriptDir   = $PSScriptRoot,  # defaults to the folder this .ps1 lives in
    [string]$RunAt       = "07:00",        # daily trigger time (24h format)
    [string]$TaskName    = "UiPath-Health-Monitor"
)

$ScriptPath = Join-Path $ScriptDir "main.py"
$LogPath    = Join-Path $ScriptDir "logs\monitor.log"

# Ensure logs directory exists
New-Item -ItemType Directory -Force -Path (Join-Path $ScriptDir "logs") | Out-Null

$Action  = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScriptPath`" >> `"$LogPath`" 2>&1" `
    -WorkingDirectory $ScriptDir

$Trigger = New-ScheduledTaskTrigger -Daily -At $RunAt

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 10)

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Force

Write-Host ""
Write-Host "Task '$TaskName' registered successfully." -ForegroundColor Green
Write-Host "It will run daily at $RunAt using: $PythonExe $ScriptPath"
Write-Host ""
Write-Host "To run immediately for testing:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To remove the task:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
