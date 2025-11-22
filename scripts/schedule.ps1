param(
    [string]$PythonPath = "python",
    [string]$WorkingDir = (Split-Path $PSScriptRoot -Parent),
    [string]$TaskName = "NewsAI_Pipeline_Hourly"
)
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument "scripts/run_pipeline.py" -WorkingDirectory $WorkingDir
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName $TaskName -Description "Run News-AI pipeline hourly" -Force | Out-Null
Write-Output "Registered task $TaskName to run hourly"