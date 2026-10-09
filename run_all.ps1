# run_all.ps1
# PowerShell entry point for ClimateAdapt-Comfort

param (
    [switch]$Smoke,
    [string]$Stage = "",
    [string]$EnergyPlus = "C:\EnergyPlusV26-2-0\energyplus.exe"
)

$env:ENERGYPLUS_EXE = $EnergyPlus

if ($Smoke) {
    python src/run_all.py --smoke --energyplus $EnergyPlus
} elseif ($Stage -ne "") {
    python src/run_all.py --stage $Stage --energyplus $EnergyPlus
} else {
    python src/run_all.py --energyplus $EnergyPlus
}
