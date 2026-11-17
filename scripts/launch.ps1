param([string]$Python = "$PSScriptRoot\..\.venv\Scripts\python.exe")
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$version = (Get-Content -LiteralPath "$root\VERSION" -Raw).Trim()
$current = Join-Path $root "dist\releases\$version\ATOMVERSE-AI\ATOMVERSE-AI.exe"
$standalone = Join-Path $root "dist\releases\$version\ATOMVERSE-AI-$version-windows-x64.exe"
if (Test-Path -LiteralPath $standalone) {
    Start-Process -FilePath $standalone -WorkingDirectory $root -WindowStyle Hidden
} elseif (Test-Path -LiteralPath $current) {
    Start-Process -FilePath $current -WorkingDirectory $root -WindowStyle Hidden
} else {
    & $Python "$root\SOFTWARE\main.py"
}
