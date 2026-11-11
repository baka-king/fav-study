# 收藏变笔记 · 打开界面（PowerShell 版，比 VBS 的 Run 稳）
# 逻辑：服务没跑就拉起来 → 已有窗口且还活着就聚焦 → 否则开一个 --app 窗口
param([int]$Port = 8765)

$Root = "E:\AI\DouyinFavStudy"
$Py = Join-Path $Root "python\python.exe"
$Base = "http://127.0.0.1:$Port"
$Chrome = "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $Chrome)) { $Chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe" }
if (-not (Test-Path $Chrome)) { $Chrome = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" }
$ProfileDir = Join-Path $Root "data\uiwindow"

function Test-Up {
    try { Invoke-RestMethod -Uri "$Base/api/ping" -TimeoutSec 2 | Out-Null; return $true } catch { return $false }
}
function Test-Focused {
    try { return (Invoke-RestMethod -Uri "$Base/api/focus" -TimeoutSec 2).focused } catch { return $false }
}

if (-not (Test-Up)) {
    Start-Process -FilePath $Py -ArgumentList "-X", "utf8", "-m", "app", "--tray" -WorkingDirectory $Root -WindowStyle Hidden
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-Up) { break }
    }
    if (-not (Test-Up)) {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show("后台服务没能启动。`n`n先看日志：$Root\data\app.log", "收藏变笔记 打不开") | Out-Null
        exit 1
    }
}

# 已经有窗口且页面还活着：叫到前面就行，不再开第二个
if (Test-Focused) {
    $shell = New-Object -ComObject WScript.Shell
    if ($shell.AppActivate("收藏变笔记")) { exit 0 }
}

Start-Process -FilePath $Chrome -ArgumentList @(
    "--app=$Base/",
    "--window-size=1400,940",
    "--window-position=120,80",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "--hide-crash-restore-bubble"
)
