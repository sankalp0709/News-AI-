param(
    [string]$PythonPath = "python",
    [string]$WorkingDir = (Resolve-Path "$(Split-Path $PSScriptRoot)\news-ai").Path,
    [string]$TaskName = "NewsAI_Pipeline_Hourly"
)
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument "scripts/run_pipeline.py" -WorkingDirectory $WorkingDir
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date)).Repetition
$trigger.Repetition.Interval = "PT1H"
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName $TaskName -Description "Run News-AI pipeline hourly" -Force | Out-Null
Write-Output "Registered task $TaskName to run hourly"