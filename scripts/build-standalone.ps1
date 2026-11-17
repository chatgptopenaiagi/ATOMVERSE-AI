param([Parameter(Mandatory=$true)][string]$BuildPython)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$version = (Get-Content -LiteralPath "$root\VERSION" -Raw).Trim()
if ($version -notmatch '^\d+\.\d+\.\d+-alpha\.\d+$') { throw 'Invalid version' }
$output = Join-Path $root "dist\multiplatform\$version"
$env:PYINSTALLER_CONFIG_DIR = Join-Path $root '.local\pyinstaller-cache'
$env:PYTHONDONTWRITEBYTECODE = '1'
& $BuildPython -m PyInstaller --noconfirm --clean --windowed --onefile --name "ATOMVERSE-AI-$version-windows-x64" --paths "$root\SOFTWARE" --add-data "$root\SOFTWARE\atomverse\worker.py;atomverse" --add-data "$root\LICENSES;LICENSES" --add-data "$root\THIRD-PARTY-NOTICES.md;." --add-data "$root\LICENSE-DECISION.md;." --exclude-module torch --exclude-module numpy --exclude-module tkinter --distpath $output --workpath "$root\build\standalone-$version" --specpath "$root\build" "$root\SOFTWARE\main.py"
if ($LASTEXITCODE -ne 0) { throw 'Standalone build failed' }
