param(
    [Parameter(Mandatory=$true)][string]$BuildPython
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$version = (Get-Content -LiteralPath (Join-Path $root 'VERSION') -Raw).Trim()
if ($version -notmatch '^\d+\.\d+\.\d+-alpha\.\d+$') { throw 'Unexpected version format' }
$outputRoot = Join-Path $root "dist\candidates\$version"
$artifactTarget = [IO.Path]::GetFullPath((Join-Path $outputRoot 'ATOMVERSE-AI'))
if (-not $artifactTarget.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Build output must stay inside this project.'
}
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYINSTALLER_CONFIG_DIR = "$root\.local\pyinstaller-cache"
& $BuildPython -m PyInstaller --noconfirm --clean --windowed --onedir --name ATOMVERSE-AI --paths "$root\SOFTWARE" --add-data "$root\SOFTWARE\atomverse\worker.py;atomverse" --exclude-module torch --exclude-module numpy --exclude-module tkinter --distpath $outputRoot --workpath "build\$version" --specpath build SOFTWARE/main.py
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
Copy-Item -LiteralPath README.md,LICENSE-DECISION.md,THIRD-PARTY-NOTICES.md -Destination $artifactTarget
Copy-Item -LiteralPath LICENSES -Destination $artifactTarget -Recurse -Force
Write-Output "Built $artifactTarget\ATOMVERSE-AI.exe. Keep the complete folder together. Prior version artifacts were preserved."
