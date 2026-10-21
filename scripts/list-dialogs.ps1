# list-dialogs.ps1 -- list the dialogs / pop-up windows of CC5 and Reallusion Hub.
#
# Works even when CC5's main thread is blocked by a modal dialog (it talks to Windows
# directly, not through the bridge). READ-ONLY: it never clicks, types or closes anything.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/list-dialogs.ps1 [-Screenshot] [-ProcessNames a,b] [-OutDir dir]
# Output: one JSON document on stdout.

param(
    [switch]$Screenshot,
    [string[]]$ProcessNames = @("CharacterCreator", "Reallusion Hub"),
    [string]$OutDir = (Join-Path $env:TEMP "cc5-dialogs"),
    [int]$UiaTimeoutMs = 1500
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, System.Drawing

Add-Type -ReferencedAssemblies System.Drawing, UIAutomationClient, UIAutomationTypes, WindowsBase @"
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Automation;

public class DlgInfo {
    public long Hwnd; public int Pid; public string Title; public string ClassName;
    public bool Visible; public bool Minimized; public bool Foreground; public bool HasOwner;
    public bool Modal; public int X, Y, W, H;
    public List<string> Texts = new List<string>(); public List<string> Buttons = new List<string>();
    public string TextSource = "";
}

public static class DlgProbe {
    delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr h, EnumProc p, IntPtr l);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr h, uint cmd);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out int pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
    [DllImport("user32.dll", EntryPoint = "GetWindowLong")] static extern int GetWindowLong32(IntPtr h, int i);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtr")] static extern IntPtr GetWindowLong64(IntPtr h, int i);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern IntPtr SendMessageTimeout(IntPtr h, uint msg, IntPtr w, IntPtr l, uint flags, uint timeout, out IntPtr res);
    [StructLayout(LayoutKind.Sequential)] struct RECT { public int L, T, R, B; }

    const int GWL_STYLE = -16, GWL_EXSTYLE = -20;
    const long WS_MINIMIZEBOX = 0x20000, WS_EX_TOOLWINDOW = 0x80, WS_EX_NOACTIVATE = 0x08000000, WS_EX_DLGMODALFRAME = 1;

    static long Style(IntPtr h, int idx) {
        return IntPtr.Size == 8 ? GetWindowLong64(h, idx).ToInt64() : GetWindowLong32(h, idx);
    }
    static string Text(IntPtr h) {
        // WM_GETTEXT with a timeout so a hung window cannot block us.
        IntPtr res; var sb = new StringBuilder(1024);
        IntPtr buf = Marshal.AllocHGlobal(2048);
        try {
            IntPtr r = SendMessageTimeout(h, 0x000D, (IntPtr)1000, buf, 0x2, 300, out res);
            if (r == IntPtr.Zero) return "";
            return Marshal.PtrToStringUni(buf) ?? "";
        } finally { Marshal.FreeHGlobal(buf); }
    }
    static string Cls(IntPtr h) { var sb = new StringBuilder(256); GetClassName(h, sb, 256); return sb.ToString(); }

    public static List<DlgInfo> Scan(HashSet<int> pids) {
        var list = new List<DlgInfo>();
        IntPtr fg = GetForegroundWindow();
        EnumWindows((h, l) => {
            int pid; GetWindowThreadProcessId(h, out pid);
            if (!pids.Contains(pid)) return true;
            RECT r; GetWindowRect(h, out r);
            long ex = Style(h, GWL_EXSTYLE);
            var d = new DlgInfo {
                Hwnd = h.ToInt64(), Pid = pid, ClassName = Cls(h), Title = Text(h),
                Visible = IsWindowVisible(h), Minimized = IsIconic(h), Foreground = (h == fg),
                HasOwner = GetWindow(h, 4) != IntPtr.Zero,
                Modal = (ex & WS_EX_DLGMODALFRAME) != 0,
                X = r.L, Y = r.T, W = r.R - r.L, H = r.B - r.T
            };
            // tooltips / hidden helper windows are not interesting
            if ((ex & WS_EX_TOOLWINDOW) != 0 && string.IsNullOrEmpty(d.Title)) return true;
            if ((ex & WS_EX_NOACTIVATE) != 0 && string.IsNullOrEmpty(d.Title)) return true;
            d.TextSource = (Style(h, GWL_STYLE) & WS_MINIMIZEBOX) != 0 ? "minbox" : "";
            list.Add(d);
            return true;
        }, IntPtr.Zero);
        return list;
    }

    // Static / Button text of classic Win32 dialogs.
    public static void ChildTexts(DlgInfo d) {
        EnumChildWindows(new IntPtr(d.Hwnd), (c, l) => {
            if (!IsWindowVisible(c)) return true;
            string cls = Cls(c), t = Text(c);
            if (string.IsNullOrWhiteSpace(t)) return true;
            t = t.Trim();
            if (cls == "Button") { if (d.Buttons.Count < 20) d.Buttons.Add(t.Replace("&", "")); }
            else if (cls == "Static" || cls == "Edit" || cls.StartsWith("Qt")) { if (d.Texts.Count < 30) d.Texts.Add(t); }
            return true;
        }, IntPtr.Zero);
        if (d.Texts.Count > 0 || d.Buttons.Count > 0) d.TextSource = "win32";
    }

    // UI Automation text/buttons (Qt exposes its widgets this way), bounded by a timeout.
    public static void UiaTexts(DlgInfo d, int timeoutMs) {
        var task = Task.Run(() => {
            var texts = new List<string>(); var buttons = new List<string>();
            var root = AutomationElement.FromHandle(new IntPtr(d.Hwnd));
            var all = root.FindAll(TreeScope.Descendants, Condition.TrueCondition);
            int n = 0;
            foreach (AutomationElement e in all) {
                if (++n > 300) break;
                var ct = e.Current.ControlType;
                string name = (e.Current.Name ?? "").Trim();
                if (name.Length == 0 || e.Current.IsOffscreen) continue;
                if (ct == ControlType.Button || ct == ControlType.Hyperlink) { if (buttons.Count < 20) buttons.Add(name.Replace("&", "")); }
                else if (ct == ControlType.Text || ct == ControlType.Edit || ct == ControlType.Document) { if (texts.Count < 30) texts.Add(name); }
            }
            return Tuple.Create(texts, buttons);
        });
        try {
            if (task.Wait(timeoutMs)) {
                foreach (var t in task.Result.Item1) if (!d.Texts.Contains(t)) d.Texts.Add(t);
                foreach (var b in task.Result.Item2) if (!d.Buttons.Contains(b)) d.Buttons.Add(b);
                d.TextSource = (d.TextSource == "win32" ? "win32+uia" : "uia");
            } else { d.TextSource = (d.TextSource + " uia-timeout").Trim(); }
        } catch (Exception) { d.TextSource = (d.TextSource + " uia-error").Trim(); }
    }

    public static bool Shot(DlgInfo d, string path) {
        if (d.W < 10 || d.H < 10 || d.W > 8000 || d.H > 8000) return false;
        IntPtr h = new IntPtr(d.Hwnd);
        using (var bmp = new Bitmap(d.W, d.H)) {
            using (var g = Graphics.FromImage(bmp)) {
                IntPtr dc = g.GetHdc();
                bool ok = false;
                try { ok = PrintWindow(h, dc, 2); } finally { g.ReleaseHdc(dc); }
                // Screen-copy fallback only for the foreground window: otherwise it would capture whatever
                // OTHER app happens to cover that area (privacy), so we return no picture instead.
                if (!ok) { if (d.Foreground) g.CopyFromScreen(d.X, d.Y, 0, 0, new Size(d.W, d.H)); else return false; }
            }
            bmp.Save(path, ImageFormat.Png);
        }
        return true;
    }
}
"@

function Esc([string]$s) { if ($null -eq $s) { "" } else { $s } }

$pids = New-Object 'System.Collections.Generic.HashSet[int]'
$procNames = @{}
foreach ($n in $ProcessNames) {
    foreach ($p in (Get-Process -Name $n -ErrorAction SilentlyContinue)) {
        [void]$pids.Add($p.Id); $procNames[$p.Id] = $p.ProcessName
    }
}

$result = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    processes = @($procNames.GetEnumerator() | ForEach-Object { [ordered]@{ pid = $_.Key; name = $_.Value } })
    dialogs   = @()
}

if ($pids.Count -gt 0) {
    $wins = [DlgProbe]::Scan($pids)
    # Main window per process = largest visible, unowned window with a minimize box (CC5).
    $mainByPid = @{}
    foreach ($w in ($wins | Where-Object { $_.Visible -and -not $_.HasOwner -and $_.TextSource -eq "minbox" } | Sort-Object { $_.W * $_.H } -Descending)) {
        if (-not $mainByPid.ContainsKey($w.Pid)) { $mainByPid[$w.Pid] = $w.Hwnd }
    }
    if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
    $stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
    $dialogs = @()
    foreach ($w in $wins) {
        if (-not $w.Visible -or $w.Minimized) { continue }
        if ($w.W -lt 80 -or $w.H -lt 40) { continue }
        $isMain = ($mainByPid[$w.Pid] -eq $w.Hwnd)
        if ($isMain) { continue }
        # Windows without title and without any content are noise and get dropped below.
        [DlgProbe]::ChildTexts($w)
        # Classic Win32 dialogs already gave their text; only ask UI Automation (slow) when they did not.
        if ($w.Texts.Count -eq 0 -and $w.Buttons.Count -eq 0) { [DlgProbe]::UiaTexts($w, $UiaTimeoutMs) }
        if ([string]::IsNullOrWhiteSpace($w.Title) -and $w.Texts.Count -eq 0 -and $w.Buttons.Count -eq 0) { continue }
        $shot = $null
        if ($Screenshot) {
            $p = Join-Path $OutDir ("dialog-{0}-{1}-{2}.png" -f $w.Pid, $w.Hwnd, $stamp)
            try { if ([DlgProbe]::Shot($w, $p)) { $shot = $p } } catch { }
        }
        $dialogs += [ordered]@{
            process     = $procNames[$w.Pid]
            pid         = $w.Pid
            hwnd        = $w.Hwnd
            title       = (Esc $w.Title)
            className   = $w.ClassName
            foreground  = [bool]$w.Foreground
            hasOwner    = [bool]$w.HasOwner
            modal       = [bool]$w.Modal
            rect        = @($w.X, $w.Y, $w.W, $w.H)
            texts       = @($w.Texts)
            buttons     = @($w.Buttons)
            textSource  = $w.TextSource
            screenshot  = $shot
        }
    }
    $result.dialogs = $dialogs
}

# Compress + explicit array handling so empty arrays stay arrays.
$result | ConvertTo-Json -Depth 6 -Compress
