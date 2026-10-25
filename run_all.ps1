# run_all.ps1
# PowerShell entry point for ClimateAdapt-Comfort

param (
    [switch]$Smoke,
    [string]$Stage = "",
    [string]$EnergyPlus = "C:\EnergyPlusV26-2-0\energyplus.exe"
)

$env:ENERGYPLUS_EXE = $EnergyPlus

$PyExe = "python"
if (Test-Path ".\.venv\Scripts\python.exe") {
    $PyExe = ".\.venv\Scripts\python.exe"
}

if ($Smoke) {
    & $PyExe src/run_all.py --smoke --energyplus $EnergyPlus
} elseif ($Stage -ne "") {
    & $PyExe src/run_all.py --stage $Stage --energyplus $EnergyPlus
} else {
    & $PyExe src/run_all.py --energyplus $EnergyPlus
}
