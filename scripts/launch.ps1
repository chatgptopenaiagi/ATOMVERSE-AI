param([string]$Python = "$PSScriptRoot\..\.venv\Scripts\python.exe")
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (Test-Path -LiteralPath "$root\dist\ATOMVERSE-AI\ATOMVERSE-AI.exe") {
    Start-Process -FilePath "$root\dist\ATOMVERSE-AI\ATOMVERSE-AI.exe" -WorkingDirectory $root -WindowStyle Hidden
} else {
    & $Python "$root\SOFTWARE\main.py"
}
