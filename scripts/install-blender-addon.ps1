# Install CC/iC Blender Tools (Reallusion's add-on for Blender) — REQUIRED.
# The custom-shoe / high-heel boot workflow and every CC5 <-> Blender round trip depend on it
# (it reads CC's FbxKey + json export and writes the FbxKey FBX that CC5 can load back).
# Downloads the pinned release from GitHub (soupday/cc_blender_tools), copies it into Blender's
# user add-on folder as "cc_blender_tools" and enables it.
#
#   powershell -ExecutionPolicy Bypass -File scripts\install-blender-addon.ps1
#   (optional) -Version 2_4_4 -Blender "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
param(
  [string]$Version = "2_4_4",
  [string]$Blender = ""
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # the progress bar makes Invoke-WebRequest very slow

if (-not $Blender) {
  $Blender = Get-ChildItem "C:\Program Files\Blender Foundation\*\blender.exe" |
    Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $Blender -or -not (Test-Path $Blender)) { throw "Blender not found; pass -Blender <path to blender.exe>" }
$bver = Split-Path (Split-Path $Blender -Parent) -Leaf          # "Blender 5.2"
$bver = $bver -replace "^Blender\s*", ""
$addons = Join-Path $env:APPDATA "Blender Foundation\Blender\$bver\scripts\addons"
New-Item -ItemType Directory -Force -Path $addons | Out-Null

$work = Join-Path $env:TEMP "cc_blender_tools_$Version"
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Force -Path $work | Out-Null
$zip = Join-Path $work "addon.zip"
$url = "https://github.com/soupday/cc_blender_tools/archive/refs/tags/$Version.zip"
Write-Host "Downloading $url"
Invoke-WebRequest -Uri $url -OutFile $zip
Expand-Archive -Path $zip -DestinationPath $work
$src = Get-ChildItem $work -Directory | Where-Object { Test-Path (Join-Path $_.FullName "__init__.py") } | Select-Object -First 1
if (-not $src) { throw "add-on folder with __init__.py not found in the zip" }

$dst = Join-Path $addons "cc_blender_tools"
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
Copy-Item -Recurse -Path $src.FullName -Destination $dst

$py = "import addon_utils, bpy; m = addon_utils.enable('cc_blender_tools', default_set=True, persistent=True); bpy.ops.wm.save_userpref(); print('CC_TOOLS_ENABLED', bool(m), hasattr(bpy.ops.cc3, 'importer'))"
# stdout only: the add-on prints harmless SyntaxWarnings on stderr, which Windows PowerShell
# would turn into a terminating error under "Stop"
$ErrorActionPreference = "Continue"
$out = & $Blender -b --python-expr $py 2>$null | Select-String "CC_TOOLS_ENABLED"
$ErrorActionPreference = "Stop"
Write-Host $out
if ("$out" -notmatch "CC_TOOLS_ENABLED True True") { throw "add-on did not enable: $out" }
Write-Host "CC/iC Blender Tools $Version installed in $dst"
