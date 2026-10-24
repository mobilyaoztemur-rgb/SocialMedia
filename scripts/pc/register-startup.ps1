# Optional: register the bridge at THIS user's logon, in their interactive desktop.
# Run from a normal PowerShell session after reviewing this file.
$ErrorActionPreference = 'Stop'
$bridgeLauncher = (Resolve-Path (Join-Path $PSScriptRoot 'start-bridge.cmd')).Path
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument ('/d /c ""{0}""' -f $bridgeLauncher)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $account
$principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
if (Get-ScheduledTask -TaskName 'Woodmood PC Bridge' -ErrorAction SilentlyContinue) {
    throw 'Woodmood PC Bridge task already exists. Inspect it before making changes.'
}
Register-ScheduledTask -TaskName 'Woodmood PC Bridge' -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
Write-Output 'Bridge will start at your next Windows sign-in. No administrator or SYSTEM browser service was created.'
Write-Output 'Quick Tunnel is started separately because its address changes after restart.'
