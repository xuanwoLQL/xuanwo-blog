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

if ($DeployPath -notmatch '^/var/www/[A-Za-z0-9._/-]+$') {
    throw "DeployPath must be a simple absolute path below /var/www"
}

if (-not (Test-Path -LiteralPath "themes/PaperMod")) {
    throw "themes/PaperMod is missing"
}

$Hugo = if ($env:HUGO_BIN) {
    $env:HUGO_BIN
} else {
    (Get-Command hugo -ErrorAction Stop).Source
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
Write-Host "[blog] Preparing remote directory $Remote`:$DeployPath"
& $Ssh @SshArgs $Remote "mkdir -p -- '$DeployPath'"
if ($LASTEXITCODE -ne 0) { throw "Remote mkdir failed" }

$ArchiveName = "xuanwo-blog-$([guid]::NewGuid().ToString('N')).tar.gz"
$Archive = Join-Path $env:TEMP $ArchiveName

try {
    Write-Host "[blog] Packaging public/"
    & $Tar -C (Join-Path $ProjectRoot "public") -czf $Archive "."
    if ($LASTEXITCODE -ne 0) { throw "tar packaging failed" }

    Write-Host "[blog] Uploading release archive"
    & $Scp @ScpArgs $Archive "${Remote}:/tmp/$ArchiveName"
    if ($LASTEXITCODE -ne 0) { throw "scp upload failed" }

    Write-Host "[blog] Extracting release and fixing permissions"
    $RemoteCommand = "tar -xzf '/tmp/$ArchiveName' -C '$DeployPath' && " +
        "find '$DeployPath' -type d -exec chmod 755 {} + && " +
        "find '$DeployPath' -type f -exec chmod 644 {} + && " +
        "test -f '$DeployPath/index.html' && rm -f '/tmp/$ArchiveName'"
    & $Ssh @SshArgs $Remote $RemoteCommand
    if ($LASTEXITCODE -ne 0) { throw "Remote extraction failed" }

    Write-Host "[blog] Deployment finished: $BaseUrl"
}
finally {
    if ([System.IO.File]::Exists($Archive)) {
        [System.IO.File]::Delete($Archive)
    }
}

