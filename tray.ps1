# 收藏变笔记 · 托盘（PowerShell WinForms，零依赖）
# 由「后台运行.vbs」拉起；关掉这个进程就等于退出菜单，但服务仍会在后台跑
param([int]$Port = 8765)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$Root = "E:\AI\DouyinFavStudy"
$Base = "http://127.0.0.1:$Port"

function Call-Api([string]$Path) {
    try { Invoke-RestMethod -Uri "$Base$Path" -Method Post -ContentType "application/json" -Body "{}" -TimeoutSec 8 | Out-Null; return $true }
    catch { return $false }
}

$iconPath = Join-Path $Root "app.ico"
$icon = if (Test-Path $iconPath) { New-Object System.Drawing.Icon($iconPath) } else { [System.Drawing.SystemIcons]::Application }

# 单实例：已经有一个托盘在跑就直接退出，避免叠出两个图标
$lock = Join-Path $Root "data/tray.lock"
if (Test-Path $lock) {
    $oldPid = Get-Content $lock -ErrorAction SilentlyContinue
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) { exit 0 }
}
Set-Content -Path $lock -Value $PID -Encoding ASCII
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -SupportEvent -Action {
    Remove-Item (Join-Path $Root "data/tray.lock") -ErrorAction SilentlyContinue
} | Out-Null

$ni = New-Object System.Windows.Forms.NotifyIcon
$ni.Icon = $icon
$ni.Text = "收藏变笔记 · 后台运行中"
$ni.Visible = $true

$menu = New-Object System.Windows.Forms.ContextMenuStrip

$miOpen = $menu.Items.Add("打开界面")
$miOpen.add_Click({
    Start-Process "wscript.exe" -ArgumentList (Join-Path $Root "launch.vbs")
})

$miPause = $menu.Items.Add("暂停同步")
$paused = $false
$miPause.add_Click({
    if ($script:paused) { Call-Api "/api/resume" | Out-Null; $script:paused = $false; $miPause.Text = "暂停同步"; $ni.ShowBalloonTip(1500, "收藏变笔记", "已继续同步", [System.Windows.Forms.ToolTipIcon]::Info) }
    else { Call-Api "/api/pause" | Out-Null; $script:paused = $true; $miPause.Text = "继续同步"; $ni.ShowBalloonTip(1500, "收藏变笔记", "已暂停同步", [System.Windows.Forms.ToolTipIcon]::Info) }
})

$miLog = $menu.Items.Add("打开日志")
$miLog.add_Click({ Start-Process (Join-Path $Root "data\app.log") })

$menu.Items.Add("-") | Out-Null

$miQuit = $menu.Items.Add("退出")
$miQuit.add_Click({
    Call-Api "/api/quit" | Out-Null
    Remove-Item $lock -ErrorAction SilentlyContinue
    $ni.Visible = $false
    $ni.Dispose()
    [System.Windows.Forms.Application]::Exit()
})

$ni.ContextMenuStrip = $menu
# 第一次挂上时提示一句，免得以为没启动（Win11 新图标默认会折叠进「隐藏的图标」）
try {
    $ni.ShowBalloonTip(4000, "收藏变笔记", "已在后台运行。右键托盘图标可打开界面、暂停或退出。", [System.Windows.Forms.ToolTipIcon]::Info)
} catch { }
$ni.add_DoubleClick({
    Start-Process "wscript.exe" -ArgumentList (Join-Path $Root "launch.vbs")
})

# 服务已经退出了就自己收摊，别留一个死图标
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 15000
$timer.add_Tick({
    try { Invoke-RestMethod -Uri "$Base/api/ping" -TimeoutSec 3 | Out-Null }
    catch {
        $ni.Visible = $false
        $ni.Dispose()
        [System.Windows.Forms.Application]::Exit()
    }
})
$timer.Start()

[System.Windows.Forms.Application]::Run()
