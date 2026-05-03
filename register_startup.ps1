# Run this once in an Admin PowerShell to register the startup task.
# To remove the task: schtasks /delete /tn "DesktopWorkspaces" /f

$action = New-ScheduledTaskAction `
    -Execute "D:\DesktopProject\.venv\Scripts\pythonw.exe" `
    -Argument '"D:\DesktopProject\main.py" --startup' `
    -WorkingDirectory "D:\DesktopProject"

$trigger  = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest

Register-ScheduledTask `
    -TaskName "DesktopWorkspaces" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force

Write-Host ""
Write-Host "Verifying task..." -ForegroundColor Cyan
schtasks /query /tn "DesktopWorkspaces" /fo LIST
