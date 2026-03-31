# CC5 MCP Bridge Plugin Installer
$source = "C:\Users\macka\Projects\cc5-mcp-server\cc5-plugin"
$dest   = "C:\Program Files\Reallusion\Character Creator 5\Bin64\OpenPlugin\CC5_MCP_Bridge"

if (Test-Path $dest) {
    Remove-Item -Recurse -Force $dest
    Write-Host "Removed old plugin." -ForegroundColor Yellow
}

# Copy plugin files (exclude libs — no longer needed)
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item "$source\main.py"    $dest
Copy-Item "$source\server.py"  $dest
Copy-Item "$source\cc5_api.py" $dest
Copy-Item "$source\config.json" $dest
Copy-Item "$source\config.xml"  $dest

Write-Host "Plugin installed to: $dest" -ForegroundColor Green
Write-Host "Please restart Character Creator 5." -ForegroundColor Cyan
