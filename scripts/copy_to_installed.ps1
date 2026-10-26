# Copy the repository's cc5_api.py and the Qt UI helper modules (cc5_ui.py, cc5_skingen.py, cc5_content.py)
# over the installed plugin copy (then GET /reload). Result is written to %TEMP%\copy_result.txt.
$pluginDir = Join-Path $PSScriptRoot "..\cc5-plugin"
$dstDir = "C:\Program Files\Reallusion\Character Creator 5\Bin64\OpenPlugin\CC5_MCP_Bridge"
$result = Join-Path $env:TEMP "copy_result.txt"
try {
  $lines = @()
  foreach ($file in Get-ChildItem -Path $pluginDir -Filter "cc5_*.py") {
    $dst = Join-Path $dstDir $file.Name
    Copy-Item -Force -Path $file.FullName -Destination $dst -ErrorAction Stop
    $lines += "OK $($file.Name) src=$($file.Length) dst=$((Get-Item $dst).Length)"
  }
  $lines | Out-File -FilePath $result -Encoding ascii
} catch {
  "ERR: $_" | Out-File -FilePath $result -Encoding ascii
}
