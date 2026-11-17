param(
    [Parameter(Mandatory=$true)][string]$Gradle,
    [Parameter(Mandatory=$true)][string]$JavaHome,
    [Parameter(Mandatory=$true)][string]$BuildPython,
    [switch]$Tests
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$private = Join-Path $root '.local\android-signing'
New-Item -ItemType Directory -Force -Path $private | Out-Null
$passwordFile = Join-Path $private 'password.txt'
$keyFile = Join-Path $private 'atomverse-release.jks'
if (-not (Test-Path -LiteralPath $passwordFile)) {
    if (Test-Path -LiteralPath $keyFile) { throw 'Existing signing key requires its original password; never replace it.' }
    [IO.File]::WriteAllText($passwordFile,[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)))
}
$env:JAVA_HOME = $JavaHome
$env:ATOMVERSE_KEY_PASSWORD = [IO.File]::ReadAllText($passwordFile)
$env:ATOMVERSE_KEYSTORE = $keyFile
$env:ATOMVERSE_BUILD_PYTHON = (Resolve-Path -LiteralPath $BuildPython).Path
$env:GRADLE_USER_HOME = Join-Path $root '.local\mission002a\gradle'
try {
    if (-not (Test-Path -LiteralPath $keyFile)) {
        & "$JavaHome\bin\keytool.exe" -genkeypair -keystore $keyFile -storepass:env ATOMVERSE_KEY_PASSWORD -keypass:env ATOMVERSE_KEY_PASSWORD -alias atomverse -keyalg RSA -keysize 3072 -validity 10000 -dname 'CN=ATOMVERSE AI, O=ATOMVERSE AI'
        if ($LASTEXITCODE -ne 0) { throw 'Signing key creation failed' }
    }
    Push-Location (Join-Path $root 'SOFTWARE\android')
    try {
        $tasks = @('assembleRelease')
        if ($Tests) { $tasks += 'assembleReleaseAndroidTest' }
        & $Gradle @tasks --console=plain
        if ($LASTEXITCODE -ne 0) { throw 'Android build failed' }
    } finally { Pop-Location }
} finally { Remove-Item Env:ATOMVERSE_KEY_PASSWORD -ErrorAction SilentlyContinue }
