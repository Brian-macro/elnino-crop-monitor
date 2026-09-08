param([string]$Python = 'python', [string]$Time = '14:17')
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pythonPath = (Get-Command $Python -ErrorAction Stop).Source
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument ('"' + (Join-Path $PSScriptRoot 'update_all.py') + '" --group scheduled') -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName 'ElNinoCropMonitor-Update' -Action $action -Trigger $trigger -Settings $settings -Description 'Update official crop and climate evidence; preserve historical vintages.' -Force
