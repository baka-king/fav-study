"""启动入口：双击后只出现一个应用窗口，不显示命令行窗口。

要点：
- 先把控制台关掉，日志改写进 data/app.log（出问题可以翻这个文件）
- 用文件锁保证只有一个实例在启动，连点多次也只会开一个窗口
- 已经有一个实例在跑，就不再起第二个服务，直接把窗口叫出来
- 关掉窗口不会退出：后台继续跑处理队列，只有「设置 → 退出程序」才真的停
"""
import argparse
import atexit
import os
import sys
import time
from pathlib import Path


def _detach_console():
    """双击启动时立刻收掉控制台窗口；如果是从已有的命令行里运行，就别动它。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        arr = (ctypes.c_uint * 8)()
        n = k32.GetConsoleProcessList(arr, 8)
        if n > 1:  # 共用别人的控制台，不能关
            return
        hwnd = k32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
        k32.FreeConsole()
    except Exception:
        pass


def _setup_log():
    """没有控制台了，把输出接到 data/app.log，方便以后排查。"""
    try:
        data = Path(__file__).resolve().parent.parent / "data"
        data.mkdir(parents=True, exist_ok=True)
        f = open(data / "app.log", "a", encoding="utf-8", buffering=1)
        f.write("\n===== " + time.strftime("%Y-%m-%d %H:%M:%S") + " 启动 =====\n")
        sys.stdout = f
        sys.stderr = f
    except Exception:
        pass


def _msgbox(text, title="收藏学习台"):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(text), title, 0x10)
    except Exception:
        pass


def _pid_alive(pid):
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
        if h:
            k32.CloseHandle(h)
            return True
    except Exception:
        pass
    return False


def _acquire_lock(lockfile: Path, wait=15.0):
    """抢一个独占的文件锁，保证同一时间只有一个实例在启动。"""
    deadline = time.time() + wait
    while True:
        try:
            fd = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            pid = 0
            try:
                pid = int((lockfile.read_text() or "0").strip())
            except Exception:
                pid = 0
            if pid and not _pid_alive(pid):  # 上次异常退出留下的，清掉
                try:
                    lockfile.unlink()
                except Exception:
                    pass
                continue
            if time.time() > deadline:
                return False
            time.sleep(0.4)
        except Exception:
            return True


def _running_port(start, span=20):
    """已经有实例在跑的话，返回它占用的端口；没有就返回 None。

    注意：必须绕开系统代理，否则开着代理的机器上会误判成「没在跑」。
    """
    import json
    import urllib.request
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for i, p in enumerate(range(start, start + span)):
        try:
            # 第一个端口（自己平时用的那个）多等一会，机器忙的时候 0.4 秒不够，
            # 会误判成「没在跑」然后重复起服务
            # 先用 ping（秒回，不受数据库忙闲影响）；老版本没有 ping 再退回 state
            try:
                with opener.open(f"http://127.0.0.1:{p}/api/ping", timeout=1.5 if i == 0 else 0.3) as r:
                    if r.status == 200:
                        return p
            except Exception:
                pass
            with opener.open(f"http://127.0.0.1:{p}/api/state", timeout=2.5 if i == 0 else 0.4) as r:
                if r.status != 200:
                    continue
                d = json.loads(r.read().decode("utf-8", "ignore"))
                if isinstance(d, dict) and "version" in d and "worker" in d:
                    return p
        except Exception:
            continue
    return None


def _open_only(port):
    """已经有一个实例在跑：只把窗口叫出来。

    返回 True 表示窗口开完、那个实例还活着；False 说明它其实已经死了
    （之前遇到过：端口探测那一瞬间还通，等去开窗口时服务已经退出，
    这个进程就只开个窗口挂着、还占着锁——双击图标就「打不开」了）。
    """
    from .server import open_app_window
    print(f"已有实例在 {port}，只打开窗口", flush=True)
    ok, how = open_app_window(f"http://127.0.0.1:{port}/")
    print(f"  打开方式：{how}", flush=True)
    if not ok:
        _msgbox(f"窗口没能打开。\n\n请手动在浏览器访问 http://127.0.0.1:{port}/\n"
                "详细记录见 data\\app.log", "收藏学习台")
    time.sleep(1.5)
    return _probe(port, 2.5)


def _low_priority():
    """把本进程降到「低于正常」优先级：转文字很吃 CPU，别跟界面、游戏抢。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS
    except Exception:
        pass


def _port_pids(port):
    """谁在监听这个端口（Windows 下解析 netstat）。"""
    if sys.platform != "win32":
        return []
    import subprocess
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                             errors="ignore", timeout=10, creationflags=0x08000000).stdout or ""
    except Exception:
        return []
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[1].rsplit(":", 1)[-1] != str(port):
            continue
        if "LISTENING" not in line.upper():
            continue
        if parts[-1].isdigit():
            pids.add(int(parts[-1]))
    return sorted(pids)


def _is_python(pid):
    import subprocess
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, errors="ignore", timeout=10,
                             creationflags=0x08000000).stdout or ""
        return "python" in out
    except Exception:
        return False


def _probe(port, timeout=5.0):
    """端口上到底有没有「活着」的实例（慢也算活着）。"""
    import json
    import urllib.request
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port}/api/state", timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "ignore"))
            return isinstance(d, dict) and "version" in d
    except Exception:
        return False


def _free_stale_port(port, log=print):
    """端口被「活着但不响应」的旧实例占着时，把它收掉，保证地址还是 8765。

    这台机器上出现过这种死锁：旧进程还挂着 8765，但已经不回应任何请求，
    启动器探活失败 → 再起一个实例 → 它只能绑到 8766 → 点桌面图标永远打不开。
    """
    if sys.platform != "win32" or not _port_pids(port):
        return
    if _probe(port, 5.0):
        return  # 其实还活着，只是慢
    import subprocess
    for pid in _port_pids(port):
        if not _is_python(pid):
            continue
        log(f"端口 {port} 被卡死的旧进程 {pid} 占着，先收掉它")
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=10,
                           creationflags=0x08000000)
        except Exception:
            pass
    time.sleep(1.5)


def main():
    ap = argparse.ArgumentParser(description="抖音收藏学习平台")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true", help="启动后不自动打开窗口")
    a = ap.parse_args()

    _detach_console()
    _setup_log()
    _low_priority()

    from .config import DATA
    from .server import serve

    lockfile = DATA / "app.lock"

    def release():
        try:
            if lockfile.exists() and lockfile.read_text().strip() == str(os.getpid()):
                lockfile.unlink()
        except Exception:
            pass

    if not _acquire_lock(lockfile):
        # 另一个实例正在启动或已经在跑：等它把端口开起来，然后只开窗口
        port = None
        for _ in range(40):
            port = _running_port(a.port)
            if port:
                break
            time.sleep(0.5)
        if port and _open_only(port):
            return
        if port:
            print("那个实例其实已经退出了，我自己起服务", flush=True)
        # 等了 20 秒端口还是没起来：锁的持有者其实已经卡死了（上次被杀/卡在启动），
        # 这时候不能傻等，把锁接管过来自己起服务，否则每次双击都只会开出一个空窗口。
        print("锁的持有者没有响应，接管并重新启动", flush=True)
        try:
            lockfile.unlink()
        except Exception:
            pass
        if not _acquire_lock(lockfile, wait=3.0):
            _open_only(a.port)
            return

    atexit.register(release)

    # 拿到锁了，但可能还有别的实例在跑（锁刚被清掉的情况）
    port = _running_port(a.port)
    if port and _open_only(port):
        return
    if port:
        print("那个实例其实已经退出了，我自己起服务", flush=True)

    # 端口被「还在、但不回应」的旧实例占着：先收掉，免得自己只能绑到 8766
    _free_stale_port(a.port)

    try:
        serve(a.port, not a.no_browser)
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        _msgbox(f"启动失败：{e}\n\n详细信息见 data\\app.log", "收藏学习台 打不开")


if __name__ == "__main__":
    main()
