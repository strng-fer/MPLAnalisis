param(
    [string]$Obscura = "C:\Users\HP 14\AppData\Local\Temp\opencode\obscura\target\release\obscura.exe",
    [string]$OutDir = "$env:TEMP\mpl-out",
    [int]$Season = 0,
    [switch]$Refresh,
    [int]$MaxMatches = 0
)

# Thin wrapper around the Python pipeline. The pages are server rendered, so
# plain HTTP is used first; Obscura stays available as the JS fallback.
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $here
try {
    $env:OBSCURA_BIN = $Obscura
    $cliArgs = @("-m", "mplid", "--out", $OutDir)
    if ($Season -gt 0) { $cliArgs += @("--season", $Season) }
    if ($Refresh) { $cliArgs += "--refresh" }
    if ($MaxMatches -gt 0) { $cliArgs += @("--max-matches", $MaxMatches) }
    & python @cliArgs
    if ($LASTEXITCODE -ne 0) { throw "pipeline failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}
