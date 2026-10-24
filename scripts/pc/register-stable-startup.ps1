# Run only after BOTH the bridge and named tunnel work manually.
# User desktop login is required for visible Chrome; no SYSTEM browser service.
$ErrorActionPreference = 'Stop'
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$privateConfig = Join-Path $env:LOCALAPPDATA 'WoodmoodSocial\tunnel.yml'
if (-not (Test-Path $privateConfig)) { throw 'Named tunnel is not configured yet.' }
$definitions = @(
    @{ Name = 'Woodmood PC Bridge'; File = 'start-bridge.cmd' },
    @{ Name = 'Woodmood Stable Tunnel'; File = 'start-stable-tunnel.cmd' }
)
# Check every prerequisite before creating either task. Never overwrite existing tasks.
foreach ($item in $definitions) {
    $item.Path = (Resolve-Path (Join-Path $PSScriptRoot $item.File)).Path
    if (Get-ScheduledTask -TaskName $item.Name -ErrorAction SilentlyContinue) {
        throw ('Task already exists: ' + $item.Name + '. Inspect it before changing startup settings.')
    }
}
$created = @()
try {
    foreach ($item in $definitions) {
        $action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument ('/d /c ""{0}""' -f $item.Path)
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $account
        $principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
        Register-ScheduledTask -TaskName $item.Name -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
        $created += $item.Name
    }
} catch {
    foreach ($name in $created) { Unregister-ScheduledTask -TaskName $name -Confirm:$false }
    throw
}
Write-Output 'Bridge and named tunnel will start at this user''s next Windows sign-in.'
Write-Output 'The fixed hostname remains the same while the PC is offline; requests cannot complete until it reconnects.'
