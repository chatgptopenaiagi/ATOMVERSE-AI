param(
    [Parameter(Mandatory=$true)][string]$BuildPython
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$artifactTarget = [IO.Path]::GetFullPath((Join-Path $root 'dist\ATOMVERSE-AI'))
if (-not $artifactTarget.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Build output must stay inside this project.'
}
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYINSTALLER_CONFIG_DIR = "$root\.local\pyinstaller-cache"
& $BuildPython -m PyInstaller --noconfirm --clean --windowed --onedir --name ATOMVERSE-AI --paths "$root\SOFTWARE" --add-data "$root\SOFTWARE\atomverse\worker.py;atomverse" --exclude-module torch --exclude-module numpy --exclude-module tkinter --distpath dist --workpath build --specpath build SOFTWARE/main.py
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
Copy-Item -LiteralPath README.md,LICENSE-DECISION.md,THIRD-PARTY-NOTICES.md -Destination dist/ATOMVERSE-AI
Copy-Item -LiteralPath LICENSES -Destination dist/ATOMVERSE-AI -Recurse -Force
Write-Output 'Built dist/ATOMVERSE-AI/ATOMVERSE-AI.exe. Keep the complete folder together.'
