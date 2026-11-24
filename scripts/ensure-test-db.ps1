#requires -Version 5.1
<#
.SYNOPSIS
    Prepares the MiniRag_26 PostgreSQL integration-test connection.

.DESCRIPTION
    Run this AFTER the normal Docker stack has started:
        . .\scripts\ensure-test-db.ps1

    Dot-sourcing is intentional: it leaves PGVECTOR_TEST_DATABASE_URL
    available in the current PowerShell session.

    This script:
      - verifies the existing pgvector container and docker_bakend network;
      - waits for PostgreSQL readiness;
      - creates minirag26test if it does not exist;
      - enables the vector extension in the test database;
      - starts (or creates) a temporary localhost TCP proxy on port 15432;
      - sets PGVECTOR_TEST_DATABASE_URL in the current shell;
      - runs the PostgreSQL connection preflight test.

    It does NOT restart, recreate, or modify the existing pgvector container,
    its volume, or the application's minirag26 database.
#>

$ErrorActionPreference = "Stop"

$containerName = "pgvector"
$networkName = "docker_bakend"
$proxyName = "pgvector-test-proxy"
$proxyImage = "alpine/socat"
$hostAddress = "127.0.0.1"
$hostPort = 15432
$testDatabase = "minirag26test"

function Invoke-DockerChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $DockerArgs,

        [Parameter(Mandatory = $true)]
        [string] $FailureMessage
    )

    $result = & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
    return $result
}

# Confirm Docker CLI and daemon.
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI was not found. Start Docker Desktop and try again."
}
Invoke-DockerChecked -DockerArgs @("info", "--format", "{{.ServerVersion}}") `
    -FailureMessage "Docker daemon is not available. Start Docker Desktop first." | Out-Null

# The main database container must already be running from the normal stack.
$pgJson = Invoke-DockerChecked -DockerArgs @("inspect", $containerName) `
    -FailureMessage "Container '$containerName' was not found. Start the normal Docker stack first."
$pg = ($pgJson | ConvertFrom-Json)[0]

if (-not $pg.State.Running) {
    throw "Container '$containerName' exists but is not running. Start the normal Docker stack first."
}

$networks = @($pg.NetworkSettings.Networks.PSObject.Properties.Name)
if ($networks -notcontains $networkName) {
    throw "Container '$containerName' is not attached to '$networkName'. Found: $($networks -join ', ')"
}

# Read the configured PostgreSQL credentials without printing the password.
$pgEnv = @{}
foreach ($entry in $pg.Config.Env) {
    $separator = $entry.IndexOf("=")
    if ($separator -gt 0) {
        $key = $entry.Substring(0, $separator)
        $value = $entry.Substring($separator + 1)
        $pgEnv[$key] = $value
    }
}

$pgUser = if ($pgEnv.ContainsKey("POSTGRES_USER")) { $pgEnv["POSTGRES_USER"] } else { "postgres" }
$pgPassword = $pgEnv["POSTGRES_PASSWORD"]
$appDatabase = if ($pgEnv.ContainsKey("POSTGRES_DB")) { $pgEnv["POSTGRES_DB"] } else { "postgres" }

if ([string]::IsNullOrWhiteSpace($pgPassword)) {
    throw "POSTGRES_PASSWORD was not found in the '$containerName' container configuration. Configure credentials without hardcoding them in this script."
}

# Wait for PostgreSQL inside its own container.
Write-Host "Checking PostgreSQL readiness in '$containerName'..."
$ready = $false
for ($attempt = 1; $attempt -le 20; $attempt++) {
    & docker exec $containerName pg_isready -U $pgUser -d $appDatabase *> $null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    throw "PostgreSQL did not become ready in '$containerName' within 20 seconds."
}

# Create the isolated test database only when absent.
Write-Host "Checking test database '$testDatabase'..."
$dbExistsOutput = Invoke-DockerChecked -DockerArgs @(
    "exec", $containerName, "psql", "-U", $pgUser, "-d", "postgres",
    "-tAc", "SELECT 1 FROM pg_database WHERE datname = '$testDatabase';"
) -FailureMessage "Could not query PostgreSQL databases."

$dbExists = (($dbExistsOutput -join "").Trim() -eq "1")
if (-not $dbExists) {
    Write-Host "Creating '$testDatabase'..."
    Invoke-DockerChecked -DockerArgs @(
        "exec", $containerName, "createdb", "-U", $pgUser, $testDatabase
    ) -FailureMessage "Could not create '$testDatabase'."
} else {
    Write-Host "Test database already exists."
}

# Ensure pgvector is available in the isolated test database.
Invoke-DockerChecked -DockerArgs @(
    "exec", $containerName, "psql", "-U", $pgUser, "-d", $testDatabase,
    "-v", "ON_ERROR_STOP=1", "-c", "CREATE EXTENSION IF NOT EXISTS vector;"
) -FailureMessage "Could not enable the vector extension in '$testDatabase'." | Out-Null

# Ensure the proxy exists with the expected network and host-port mapping.
$proxyExists = $true
$proxyJson = & docker inspect $proxyName 2>$null
if ($LASTEXITCODE -ne 0) {
    $proxyExists = $false
}

if (-not $proxyExists) {
    Write-Host "Creating temporary PostgreSQL TCP proxy on ${hostAddress}:${hostPort}..."
    Invoke-DockerChecked -DockerArgs @(
        "run", "-d",
        "--name", $proxyName,
        "--restart", "no",
        "--network", $networkName,
        "-p", "${hostAddress}:${hostPort}:5432",
        $proxyImage,
        "TCP-LISTEN:5432,fork,reuseaddr", "TCP:${containerName}:5432"
    ) -FailureMessage "Could not create the temporary proxy. Check whether host port $hostPort is available." | Out-Null
} else {
    $proxy = ($proxyJson | ConvertFrom-Json)[0]
    $proxyNetworks = @($proxy.NetworkSettings.Networks.PSObject.Properties.Name)
    $proxyBindings = @($proxy.NetworkSettings.Ports.'5432/tcp')
    $correctBinding = $false
    foreach ($binding in $proxyBindings) {
        if ($binding.HostIp -eq $hostAddress -and $binding.HostPort -eq "$hostPort") {
            $correctBinding = $true
        }
    }

    if (($proxyNetworks -notcontains $networkName) -or (-not $correctBinding)) {
        throw "An existing '$proxyName' container has a different network or port configuration. It was left unchanged. Inspect it before replacing it."
    }

    if (-not $proxy.State.Running) {
        Write-Host "Starting existing temporary proxy..."
        Invoke-DockerChecked -DockerArgs @("start", $proxyName) `
            -FailureMessage "Could not start the existing proxy container." | Out-Null
    } else {
        Write-Host "Temporary proxy is already running."
    }
}

# Wait for the Windows host port to accept connections.
Write-Host "Waiting for ${hostAddress}:${hostPort}..."
$portReady = $false
for ($attempt = 1; $attempt -le 20; $attempt++) {
    if (Test-NetConnection -ComputerName $hostAddress -Port $hostPort `
            -InformationLevel Quiet -WarningAction SilentlyContinue) {
        $portReady = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $portReady) {
    throw "The proxy is running, but ${hostAddress}:${hostPort} is not accepting connections. Check Docker port publishing and Windows port restrictions."
}

# Build the SQLAlchemy async URL. URL-encode the password but never print it.
$encodedPassword = [System.Uri]::EscapeDataString($pgPassword)
$env:PGVECTOR_TEST_DATABASE_URL = "postgresql+asyncpg://${pgUser}:${encodedPassword}@${hostAddress}:${hostPort}/${testDatabase}"

Write-Host "Test database connection configured (password hidden): ${hostAddress}:${hostPort}/${testDatabase}"

# Run the existing connectivity preflight from the repository root.
$repoRoot = Split-Path -Parent $PSScriptRoot
$preflightTest = Join-Path $repoRoot "tests\integration\test_postgres_connection.py"
if (-not (Test-Path $preflightTest)) {
    throw "Could not find the connection preflight test at '$preflightTest'."
}

Push-Location $repoRoot
try {
    Write-Host "Running PostgreSQL connection preflight..."
    & uv run pytest $preflightTest -v
    if ($LASTEXITCODE -ne 0) {
        throw "The PostgreSQL connection preflight failed. PGVECTOR_TEST_DATABASE_URL remains set in this PowerShell session for diagnosis."
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Ready: PGVECTOR_TEST_DATABASE_URL is set for this PowerShell session."
Write-Host "Use this same session to run the PostgreSQL integration tests."
