$src = "C:\Users\macka\Projects\cc5-mcp-server\cc5-plugin\cc5_api.py"
$dst = "C:\Program Files\Reallusion\Character Creator 5\Bin64\OpenPlugin\CC5_MCP_Bridge\cc5_api.py"
try {
  Copy-Item -Force -Path $src -Destination $dst -ErrorAction Stop
  $len_src = (Get-Item $src).Length
  $len_dst = (Get-Item $dst).Length
  "OK src=$len_src dst=$len_dst" | Out-File -FilePath "C:\Users\macka\AppData\Local\Temp\copy_result.txt" -Encoding ascii
} catch {
  "ERR: $_" | Out-File -FilePath "C:\Users\macka\AppData\Local\Temp\copy_result.txt" -Encoding ascii
}
