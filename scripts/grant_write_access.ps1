# One-time setup: grant the current Windows user write access to the installed
# plugin folder so future copy_to_installed.ps1 runs no longer need UAC elevation.
# Run from an elevated PowerShell. Result is written to %TEMP%\icacls_result.txt.
$target = "C:\Program Files\Reallusion\Character Creator 5\Bin64\OpenPlugin\CC5_MCP_Bridge"
$result = Join-Path $env:TEMP "icacls_result.txt"
try {
    $output = & icacls $target /grant "$($env:USERNAME):(OI)(CI)M" /T 2>&1
    "OK`n$output" | Out-File -FilePath $result -Encoding utf8
} catch {
    "ERR: $_" | Out-File -FilePath $result -Encoding utf8
}
