# One-time setup: grant macka write access to the installed plugin folder
# so future copy_to_installed.ps1 no longer needs UAC elevation.
$target = "C:\Program Files\Reallusion\Character Creator 5\Bin64\OpenPlugin\CC5_MCP_Bridge"
try {
    $output = & icacls $target /grant "macka:(OI)(CI)M" /T 2>&1
    "OK`n$output" | Out-File -FilePath "C:\Users\macka\AppData\Local\Temp\icacls_result.txt" -Encoding utf8
} catch {
    "ERR: $_" | Out-File -FilePath "C:\Users\macka\AppData\Local\Temp\icacls_result.txt" -Encoding utf8
}
