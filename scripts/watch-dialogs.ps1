# Watch for pop-up windows of Unreal Editor, Character Creator 5, Reallusion Hub and
# Windows error boxes (csrss "entry point not found" etc.). Prints one line per NEW window,
# so it can feed a Claude Code Monitor. Read-only: it never clicks anything.
# Usage: pwsh -NoProfile -File watch-dialogs.ps1 [-IntervalSec 3]
param([int]$IntervalSec = 3)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Add-Type @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public static class DlgWatch {
    delegate bool EnumProc(IntPtr h, IntPtr p);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    static string Text(IntPtr h) { var s = new StringBuilder(512); GetWindowText(h, s, 512); return s.ToString(); }
    static string Cls(IntPtr h) { var s = new StringBuilder(256); GetClassName(h, s, 256); return s.ToString(); }
    public static List<string[]> List() {
        var outList = new List<string[]>();
        EnumWindows((h, p) => {
            if (!IsWindowVisible(h)) return true;
            uint pid; GetWindowThreadProcessId(h, out pid);
            var body = new StringBuilder();
            EnumChildWindows(h, (c, q) => {
                var t = Text(c);
                if (t.Length > 0 && body.Length < 400) body.Append(t.Replace("\r", " ").Replace("\n", " ")).Append(" | ");
                return true;
            }, IntPtr.Zero);
            outList.Add(new[] { h.ToString(), pid.ToString(), Cls(h), Text(h), body.ToString() });
            return true;
        }, IntPtr.Zero);
        return outList;
    }
}
'@

$watched = 'UnrealEditor', 'CharacterCreator', 'CrashReportClientEditor', 'CrashReportClient', 'Reallusion Hub', 'csrss', 'WerFault', 'EpicGamesLauncher'
# Main windows and known harmless tool panels are not reported.
$ignoreTitle = '^(Unreal Editor - .*|.* - Unreal Editor|Character Creator 5 - .*|Headshot 3|Epic Games Launcher|コンテンツブラウザ|Content Browser|)$'
$seen = @{}
while ($true) {
    $now = @{}
    foreach ($w in [DlgWatch]::List()) {
        $proc = (Get-Process -Id ([int]$w[1]) -ErrorAction SilentlyContinue).ProcessName
        if (-not $proc -or $watched -notcontains $proc) { continue }
        $title = $w[3]
        # csrss/WerFault boxes are named after the failing exe; keep only UE/CC ones.
        if ($proc -in 'csrss', 'WerFault' -and $title -notmatch 'Unreal|CharacterCreator|Character Creator') { continue }
        if ($title -match $ignoreTitle -and $w[2] -ne '#32770') { continue }
        if ($title -eq '' -and $w[4] -eq '') { continue }
        $key = $w[0] + '|' + $title
        $now[$key] = $true
        if (-not $seen.ContainsKey($key)) {
            $stamp = Get-Date -Format 'HH:mm:ss'
            Write-Output ("{0} DIALOG [{1}] hwnd={2} class={3} title=""{4}"" text=""{5}""" -f $stamp, $proc, $w[0], $w[2], $title, $w[4].TrimEnd(' ', '|'))
        }
    }
    foreach ($k in @($seen.Keys)) {
        if (-not $now.ContainsKey($k)) { Write-Output ("{0} CLOSED {1}" -f (Get-Date -Format 'HH:mm:ss'), $k) }
    }
    $seen = $now
    Start-Sleep -Seconds $IntervalSec
}
