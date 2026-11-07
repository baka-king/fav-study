"""把已经打开的应用窗口叫回最前面（最小化了也能恢复）。

关掉网页不退出程序，所以再次点桌面图标时不能新开一个窗口，
得先把旧的叫出来——VBS 的 AppActivate 对最小化的窗口不管用，这里用 Win32 接口做。
注意：Chrome/Edge 的应用窗口旁边还会有一个同名的小工具窗口（200x40 那种），
要按「还原后的尺寸」把它挑掉，否则会对着那个看不见的窗口 ShowWindow。
"""
import sys


class _RECT:
    pass


def focus(title="收藏学习台"):
    """返回 (找到窗口, 是否还原/激活成功)。"""
    if sys.platform != "win32":
        return False, False
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return False, False

    u = ctypes.windll.user32

    class WINDOWPLACEMENT(ctypes.Structure):
        _fields_ = [("length", ctypes.c_uint), ("flags", ctypes.c_uint), ("showCmd", ctypes.c_uint),
                    ("ptMinPosition", wintypes.POINT), ("ptMaxPosition", wintypes.POINT),
                    ("rcNormalPosition", wintypes.RECT)]

    def normal_size(h):
        wp = WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(WINDOWPLACEMENT)
        try:
            if u.GetWindowPlacement(h, ctypes.byref(wp)):
                r = wp.rcNormalPosition
                return r.right - r.left, r.bottom - r.top, wp.showCmd
        except Exception:
            pass
        return 0, 0, 0

    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _cb(h, _l):
        n = u.GetWindowTextLengthW(h)
        if not n:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, buf, n + 1)
        if buf.value.strip() != title:
            return True
        cls = ctypes.create_unicode_buffer(80)
        u.GetClassNameW(h, cls, 80)
        if not cls.value.startswith("Chrome_WidgetWin"):
            return True
        w, ht, cmd = normal_size(h)
        if w >= 600 and ht >= 400:      # 真正的应用窗口，那个小工具窗口会被过滤掉
            found.append((h, w * ht, cmd))
        return True

    try:
        u.EnumWindows(_cb, 0)
    except Exception:
        return False, False
    if not found:
        return False, False

    found.sort(key=lambda x: -x[1])     # 面积最大的那个就是应用窗口
    h = found[0][0]
    try:
        if u.IsIconic(h):
            u.ShowWindow(h, 9)          # SW_RESTORE
        if u.IsIconic(h):
            # 有些 Edge 窗口对 ShowWindow 不理不睬，这个 API 能把它拽回来
            u.SwitchToThisWindow(h, True)
        u.ShowWindow(h, 5)              # SW_SHOW
        u.SetForegroundWindow(h)
        u.BringWindowToTop(h)
        import time
        time.sleep(0.4)                 # SwitchToThisWindow 是异步的，等一下再判断
        return True, not bool(u.IsIconic(h))
    except Exception:
        return True, False


def _pids_on_port(port):
    """谁在监听某个端口（用 netstat 解析，够快）。"""
    import subprocess
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             errors="ignore", timeout=10, creationflags=0x08000000).stdout or ""
    except Exception:
        return []
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5 or "LISTENING" not in line.upper():
            continue
        if parts[1].rsplit(":", 1)[-1] == str(port) and parts[-1].isdigit():
            pids.add(int(parts[-1]))
    return sorted(pids)


def hide_browser_taskbar(port=9333):
    """把后台浏览器从任务栏 / Alt-Tab 里藏起来（窗口本身仍在屏幕外跑）。

    通过 CDP 端口找到浏览器进程，再给它所有可见窗口加 WS_EX_TOOLWINDOW。
    返回藏了几个窗口。
    """
    if sys.platform != "win32":
        return 0
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return 0
    pids = set(_pids_on_port(port))
    if not pids:
        return 0

    u = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER, SWP_FRAMECHANGED = 0x2, 0x1, 0x4, 0x20

    targets = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _cb(h, _l):
        pid = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids:
            cls = ctypes.create_unicode_buffer(80)
            u.GetClassNameW(h, cls, 80)
            if cls.value.startswith("Chrome_WidgetWin"):
                targets.append(h)
        return True

    try:
        u.EnumWindows(_cb, 0)
    except Exception:
        return 0

    n = 0
    for h in targets:
        try:
            style = u.GetWindowLongW(h, GWL_EXSTYLE)
            new = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
            if new != style:
                u.SetWindowLongW(h, GWL_EXSTYLE, new)
                u.SetWindowPos(h, 0, 0, 0, 0, 0,
                               SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
                n += 1
        except Exception:
            pass
    return n
