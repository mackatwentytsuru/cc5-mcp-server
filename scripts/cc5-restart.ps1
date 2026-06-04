# CC5 Restart Script — full lifecycle: shutdown → start → close dialogs
# Usage: powershell -ExecutionPolicy Bypass -File scripts/cc5-restart.ps1
# Can also be called with -DialogsOnly to just close dialogs on a running CC5

param(
    [switch]$DialogsOnly
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinHelper {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@

function Close-CC5Dialogs {
    $cc5 = Get-Process CharacterCreator -ErrorAction SilentlyContinue
    if (-not $cc5) { return }

    # Send Enter (closes "Unsaved project" dialog if present)
    [WinHelper]::SetForegroundWindow($cc5.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 500
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Write-Host "[CC5] Sent Enter (unsaved dialog)"

    Start-Sleep -Seconds 3

    # Send Escape (closes welcome screen if present)
    $cc5 = Get-Process CharacterCreator -ErrorAction SilentlyContinue
    if ($cc5) {
        [WinHelper]::SetForegroundWindow($cc5.MainWindowHandle) | Out-Null
        Start-Sleep -Milliseconds 500
        [System.Windows.Forms.SendKeys]::SendWait("{ESCAPE}")
        Write-Host "[CC5] Sent Escape (welcome dialog)"
    }
}

# Dialog-only mode
if ($DialogsOnly) {
    Close-CC5Dialogs
    exit 0
}

# Full restart
Write-Host "[CC5] === Full Restart ==="

# 1. Graceful shutdown (no //F to avoid unsaved data dialog on next start)
$proc = Get-Process CharacterCreator -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "[CC5] Stopping CC5 (PID: $($proc.Id))..."
    Stop-Process -Id $proc.Id
    Start-Sleep -Seconds 15

    # Force kill if still alive
    $proc = Get-Process CharacterCreator -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "[CC5] Force killing..."
        Stop-Process -Id $proc.Id -Force
        Start-Sleep -Seconds 5
    }
    Write-Host "[CC5] CC5 stopped."
} else {
    Write-Host "[CC5] CC5 was not running."
}

# 2. Launch CC5
$cc5Path = "C:\Program Files\Reallusion\Character Creator 5\Bin64\CharacterCreator.exe"
Write-Host "[CC5] Launching CC5..."
Start-Process $cc5Path

# 3. Wait for bridge
Write-Host "[CC5] Waiting for bridge..."
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:5101/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) {
            Write-Host "[CC5] Bridge up after $($i * 2)s"
            break
        }
    } catch {}
}

# 4. Close startup dialogs
Start-Sleep -Seconds 5
Close-CC5Dialogs

Write-Host "[CC5] === Restart Complete ==="
