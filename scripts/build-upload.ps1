[CmdletBinding()]
param(
    [string]$BaseUrl = $(if ($env:BASE_URL) { $env:BASE_URL } else { "http://47.93.123.112/" }),
    [string]$DeployUser = $(if ($env:DEPLOY_USER) { $env:DEPLOY_USER } else { "root" }),
    [string]$DeployHost = $(if ($env:DEPLOY_HOST) { $env:DEPLOY_HOST } else { "47.93.123.112" }),
    [string]$DeployPath = $(if ($env:DEPLOY_PATH) { $env:DEPLOY_PATH } else { "/var/www/blog" }),
    [string]$SshKey = $env:SSH_KEY,
    [int]$SshPort = $(if ($env:SSH_PORT) { [int]$env:SSH_PORT } else { 22 })
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$Config = @{}
$ConfigFile = Join-Path $ProjectRoot ".deploy.env"
if (Test-Path -LiteralPath $ConfigFile) {
    foreach ($line in Get-Content -LiteralPath $ConfigFile -Encoding utf8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
        if ($trimmed -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $value = $matches[2].Trim().Trim('"').Trim("'")
            $Config[$matches[1]] = $value
        }
    }
}

if (-not $PSBoundParameters.ContainsKey("BaseUrl") -and -not $env:BASE_URL -and $Config.ContainsKey("BASE_URL")) {
    $BaseUrl = $Config["BASE_URL"]
}
if (-not $PSBoundParameters.ContainsKey("DeployUser") -and -not $env:DEPLOY_USER -and $Config.ContainsKey("DEPLOY_USER")) {
    $DeployUser = $Config["DEPLOY_USER"]
}
if (-not $PSBoundParameters.ContainsKey("DeployHost") -and -not $env:DEPLOY_HOST -and $Config.ContainsKey("DEPLOY_HOST")) {
    $DeployHost = $Config["DEPLOY_HOST"]
}
if (-not $PSBoundParameters.ContainsKey("DeployPath") -and -not $env:DEPLOY_PATH -and $Config.ContainsKey("DEPLOY_PATH")) {
    $DeployPath = $Config["DEPLOY_PATH"]
}
if (-not $PSBoundParameters.ContainsKey("SshKey") -and -not $env:SSH_KEY -and $Config.ContainsKey("SSH_KEY")) {
    $SshKey = $Config["SSH_KEY"]
}
if (-not $PSBoundParameters.ContainsKey("SshPort") -and -not $env:SSH_PORT -and $Config.ContainsKey("SSH_PORT")) {
    $SshPort = [int]$Config["SSH_PORT"]
}

if ($DeployPath -notmatch '^/var/www/[A-Za-z0-9._/-]+$') {
    throw "DeployPath must be a simple absolute path below /var/www"
}

if (-not (Test-Path -LiteralPath "themes/PaperMod")) {
    throw "themes/PaperMod is missing"
}

if ($DeployUser -eq "root") {
    Write-Warning "Deploying as root. Prefer a dedicated low-privilege account via DEPLOY_USER."
}

$Hugo = if ($env:HUGO_BIN) {
    $env:HUGO_BIN
} else {
    (Get-Command hugo -ErrorAction Stop).Source
}
$Python = if ($env:PYTHON_BIN) {
    $env:PYTHON_BIN
} else {
    (Get-Command python -ErrorAction Stop).Source
}

$OpenSsh = Join-Path $env:SystemRoot "System32\OpenSSH"
$Ssh = Join-Path $OpenSsh "ssh.exe"
$Scp = Join-Path $OpenSsh "scp.exe"
if (-not (Test-Path -LiteralPath $Ssh)) { $Ssh = (Get-Command ssh -ErrorAction Stop).Source }
if (-not (Test-Path -LiteralPath $Scp)) { $Scp = (Get-Command scp -ErrorAction Stop).Source }

$Tar = Join-Path $env:SystemRoot "System32\tar.exe"
if (-not (Test-Path -LiteralPath $Tar)) {
    $Tar = (Get-Command tar -ErrorAction Stop).Source
}

Write-Host "[blog] Building with Hugo"
& $Hugo --gc --minify --cleanDestinationDir --baseURL $BaseUrl
if ($LASTEXITCODE -ne 0) { throw "Hugo build failed" }
if (-not (Test-Path -LiteralPath "public/index.html")) {
    throw "public/index.html was not generated"
}

Write-Host "[blog] Checking internal links"
& $Python "scripts/check_links.py"
if ($LASTEXITCODE -ne 0) { throw "Internal link check failed" }

Write-Host "[blog] Checking release quality"
& $Python "scripts/quality_check.py"
if ($LASTEXITCODE -ne 0) { throw "Release quality check failed" }

$SshArgs = @("-o", "StrictHostKeyChecking=accept-new")
$ScpArgs = @("-o", "StrictHostKeyChecking=accept-new")
if ($SshKey) {
    $SshArgs += @("-i", $SshKey)
    $ScpArgs += @("-i", $SshKey)
}
if ($SshPort -ne 22) {
    $SshArgs += @("-p", "$SshPort")
    $ScpArgs += @("-P", "$SshPort")
}

$Remote = "$DeployUser@$DeployHost"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ReleaseId = "$Stamp-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
$ReleasePath = "/var/www/blog-release-$ReleaseId"
$BackupPath = "/var/www/blog-old-$ReleaseId"
$FailedPath = "/var/www/blog-failed-$ReleaseId"
$ArchiveName = "xuanwo-blog-$ReleaseId.tar.gz"
$Archive = Join-Path $env:TEMP $ArchiveName

try {
    Write-Host "[blog] Packaging public/"
    & $Tar -C (Join-Path $ProjectRoot "public") -czf $Archive "."
    if ($LASTEXITCODE -ne 0) { throw "tar packaging failed" }

    Write-Host "[blog] Uploading release archive"
    & $Scp @ScpArgs $Archive "${Remote}:/tmp/$ArchiveName"
    if ($LASTEXITCODE -ne 0) { throw "scp upload failed" }

    Write-Host "[blog] Preparing atomic release at $ReleasePath"
    $RemoteScript = "set -eu`n" +
        "archive='/tmp/$ArchiveName'`n" +
        "release='$ReleasePath'`n" +
        "deploy='$DeployPath'`n" +
        "backup='$BackupPath'`n" +
        "mkdir -p -- `"`$release`"`n" +
        "tar -xzf `"`$archive`" -C `"`$release`"`n" +
        "find `"`$release`" -type d -exec chmod 755 {} +`n" +
        "find `"`$release`" -type f -exec chmod 644 {} +`n" +
        "test -f `"`$release/index.html`"`n" +
        "if [ -e `"`$deploy`" ]; then mv -- `"`$deploy`" `"`$backup`"; fi`n" +
        "if ! mv -- `"`$release`" `"`$deploy`"; then`n" +
        "  if [ -e `"`$backup`" ] && [ ! -e `"`$deploy`" ]; then mv -- `"`$backup`" `"`$deploy`"; fi`n" +
        "  exit 1`n" +
        "fi`n" +
        "rm -f -- `"`$archive`"`n" +
        "printf '%s\n' `"`$backup`""

    & $Ssh @SshArgs $Remote $RemoteScript
    if ($LASTEXITCODE -ne 0) { throw "Remote release swap failed" }

    Write-Host "[blog] Verifying live site"
    $response = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 20
    if ($response.StatusCode -ne 200) {
        throw "Live site returned HTTP $($response.StatusCode)"
    }
    if ($response.Content -notmatch 'class=stat-num[^>]*data-count="?[1-9][0-9]*"?[^>]*>[1-9][0-9]*<') {
        throw "Live homepage does not contain rendered non-zero counters"
    }

    Write-Host "[blog] Deployment finished: $BaseUrl"
    Write-Host "[blog] Rollback directory: $BackupPath"
}
catch {
    Write-Warning "Deployment verification failed; attempting rollback"
    $RollbackScript = "if [ -d '$BackupPath' ]; then " +
        "if [ -e '$DeployPath' ]; then mv -- '$DeployPath' '$FailedPath'; fi; " +
        "mv -- '$BackupPath' '$DeployPath'; fi"
    & $Ssh @SshArgs $Remote $RollbackScript
    throw
}
finally {
    if ([System.IO.File]::Exists($Archive)) {
        [System.IO.File]::Delete($Archive)
    }
}
