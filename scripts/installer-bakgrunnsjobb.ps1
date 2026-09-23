# Registrerer en Windows-oppgave som sjekker Gmail hvert N. minutt mens du er logget inn.
param([int]$Minutter = 15)

$Root = Split-Path -Parent $PSScriptRoot
$Pythonw = Join-Path $Root ".venv\Scripts\pythonw.exe"
$Script = Join-Path $Root "poll.py"

if (-not (Test-Path $Pythonw)) { throw "Fant ikke $Pythonw. Lag venv først (se README)." }
if (-not (Test-Path (Join-Path $Root "data\token.json"))) { throw "Logg inn først: .venv\Scripts\python.exe login.py" }

$Action = New-ScheduledTaskAction -Execute $Pythonw -Argument "`"$Script`"" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $Minutter)
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask -TaskName "Jobbvarsler" -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Sjekker Gmail for jobbrelaterte tilbakemeldinger og viser Windows-varsel." -Force | Out-Null

Write-Host "Oppgaven 'Jobbvarsler' kjører hvert $Minutter. minutt. Logg: $Root\data\jobbvarsler.log"
