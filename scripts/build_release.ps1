param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Proje Python ortamı bulunamadı: $Python"
}

Push-Location $RepoRoot
try {
    $Version = (& $Python -c "from thermal_app import __version__; print(__version__)").Trim()
    $StageRoot = Join-Path $RepoRoot "dist\$Version"
    $BuildRoot = Join-Path $RepoRoot "build\$Version"
    $PackageRoot = Join-Path $StageRoot "ZebraWriter"
    if (-not $SkipTests) {
        & $Python -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw "Testler başarısız oldu." }
    }

    & $Python -m PyInstaller --noconfirm --clean --distpath $StageRoot --workpath $BuildRoot "ZebraWriter.spec"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build başarısız oldu." }
    Copy-Item -LiteralPath (Join-Path $RepoRoot "README.md") -Destination (Join-Path $PackageRoot "README.md") -Force
    Copy-Item -LiteralPath (Join-Path $RepoRoot "LICENSE") -Destination (Join-Path $PackageRoot "LICENSE") -Force
    Copy-Item -LiteralPath (Join-Path $RepoRoot "THIRD_PARTY_NOTICES.md") -Destination (Join-Path $PackageRoot "THIRD_PARTY_NOTICES.md") -Force

    $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $SmokeRoot = Join-Path $RepoRoot "output\package-smoke-$Stamp"
    New-Item -ItemType Directory -Path $SmokeRoot -Force | Out-Null
    $Executable = Join-Path $PackageRoot "ZebraWriter.exe"
    $SmokeProcess = Start-Process -FilePath $Executable -ArgumentList @(
        "--smoke-test",
        "--data-dir",
        "`"$SmokeRoot`""
    ) -WindowStyle Hidden -PassThru -Wait
    if ($SmokeProcess.ExitCode -ne 0) { throw "Paket exe smoke testi başarısız oldu." }

    $SmokeResult = Join-Path $SmokeRoot "smoke-result.json"
    & $Python "scripts\verify_release.py" $PackageRoot $SmokeResult
    if ($LASTEXITCODE -ne 0) { throw "Release doğrulaması başarısız oldu." }

    $ReleaseRoot = Join-Path $RepoRoot "release"
    New-Item -ItemType Directory -Path $ReleaseRoot -Force | Out-Null
    $Archive = Join-Path $ReleaseRoot "ZebraWriter-$Version-windows-x64-onedir.zip"
    if (Test-Path -LiteralPath $Archive) { Remove-Item -LiteralPath $Archive -Force }
    Compress-Archive -Path (Join-Path $PackageRoot "*") -DestinationPath $Archive -CompressionLevel Optimal
    $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Archive).Hash.ToLowerInvariant()
    $Checksum = Join-Path $ReleaseRoot "SHA256SUMS.txt"
    Set-Content -LiteralPath $Checksum -Value "$Hash *$(Split-Path -Leaf $Archive)" -Encoding ascii
    Write-Host "RELEASE_OK version=$Version archive=$Archive sha256=$Hash smoke=$SmokeResult"
}
finally {
    Pop-Location
}
