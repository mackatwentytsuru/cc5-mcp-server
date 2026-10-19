# Copy the repository's cc5_api.py over the installed plugin copy (then GET /reload).
# Result is written to %TEMP%\copy_result.txt.
$src = Join-Path $PSScriptRoot "..\cc5-plugin\cc5_api.py"
$dst = "C:\Program Files\Reallusion\Character Creator 5\Bin64\OpenPlugin\CC5_MCP_Bridge\cc5_api.py"
$result = Join-Path $env:TEMP "copy_result.txt"
try {
  Copy-Item -Force -Path $src -Destination $dst -ErrorAction Stop
  $len_src = (Get-Item $src).Length
  $len_dst = (Get-Item $dst).Length
  "OK src=$len_src dst=$len_dst" | Out-File -FilePath $result -Encoding ascii
} catch {
  "ERR: $_" | Out-File -FilePath $result -Encoding ascii
}
