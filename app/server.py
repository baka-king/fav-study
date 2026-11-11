"""本地网页服务：只监听 127.0.0.1，只有你自己的电脑能打开。"""
import json
import re
import mimetypes
import shutil
import tempfile
import traceback
import os
import platform
import subprocess
import threading
import time
import urllib.error
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__, backup, bili, cache, cataudit, classify, config, db, deep, imgcache, douyin, douyin_actions, dsh, insights, llm, notes, ocr, recheck, skills, transcribe, weekly, winfocus, xhs
from .worker import Worker, scan_inbox

_DEPS = None


def deps_status():
    """检查关键组件有没有装上（结果缓存，装好后重启程序即可刷新）。"""
    global _DEPS
    if _DEPS is None:
        import importlib.util as u
        import sys
        has = lambda m: u.find_spec(m) is not None
        _DEPS = {
            "python": platform.python_version(),
            "python_ok": (3, 10) <= sys.version_info[:2] <= (3, 12),
            "playwright": has("playwright"),
            "asr": has("faster_whisper") or has("mlx_whisper"),
        }
    return _DEPS

STATIC = Path(__file__).resolve().parent / "static"
worker: Worker = None
deep_runner: deep.DeepRunner = None
insight_runner: insights.InsightRunner = None
classify_runner: classify.Runner = None
dy_runner: douyin_actions.Runner = None

# 关掉网页窗口就退出程序：网页关闭时会发一个 /api/bye，这里给几秒缓冲，
# 期间只要还有请求（比如刷新页面、或者另一个窗口开着）就取消退出。
# 关掉网页窗口不再退出程序：任务队列、AI 精读、分类都继续在后台跑。
# 只有主动点「退出程序」（/api/quit）才会真的停下来。
_STOP = threading.Event()

# /api/state 的结果缓存（缓解多窗口轮询把后台压慢）
_STATE_CACHE = [0.0, None]
_STATE_LOCK = threading.Lock()

# 抖音详情/评论的缓存（同一个视频 10 分钟内不重复开页面）
_META_CACHE = {}
_META_LOCK = threading.Lock()

_QUIT = {"deadline": 0.0}


def _cancel_quit():
    if _QUIT["deadline"]:
        _QUIT["deadline"] = 0.0


def _request_quit(delay=6.0):
    _QUIT["deadline"] = time.time() + delay


def _quit_watchdog(srv):
    while True:
        time.sleep(1.0)
        deadline = _QUIT["deadline"]
        if not deadline or time.time() < deadline:
            continue
        # 正在处理视频就别退，免得把任务掐断
        if worker is not None and worker.state.get("busy"):
            _QUIT["deadline"] = 0.0
            print("窗口关了但还在处理视频，先不退出。", flush=True)
            continue
        print("窗口已关闭，程序退出。", flush=True)
        try:
            srv.shutdown()
        except Exception:
            pass
        return


def _dir_writable(d: Path) -> bool:
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / f".probe-{os.getpid()}"
        probe.write_bytes(b"x")
        probe.unlink()
        return True
    except Exception:
        return False


def ensure_temp() -> str:
    """确保有一个真正可写的临时目录。

    有的电脑 %TEMP% 权限异常（或被安全软件锁住），Playwright 启动浏览器时会执行
    mkdtemp 直接报 EPERM，表现出来就是「点了同步，抖音窗口根本不弹」。这里提前探测并兜底。
    """
    for key in ("TEMP", "TMP", "TMPDIR"):
        cur = os.environ.get(key)
        if cur and _dir_writable(Path(cur)):
            try:
                tempfile.tempdir = cur
            except Exception:
                pass
            return cur
    fallback = config.DATA / "tmp"
    fallback.mkdir(parents=True, exist_ok=True)
    for key in ("TEMP", "TMP", "TMPDIR"):
        os.environ[key] = str(fallback)
    tempfile.tempdir = str(fallback)
    return str(fallback)


BROWSER_EXES = [
    # Edge 放前面：实测部分 Chrome 版本（如 154）会忽略 --app 参数、静默不弹窗口，
    # Edge 对 --app 的支持一直正常。
    ("Edge", ["Microsoft\\Edge\\Application\\msedge.exe"]),
    ("Chrome", ["Google\\Chrome\\Application\\chrome.exe"]),
]


def find_browser_exe():
    """找本机的 Chrome / Edge，用来开独立的应用窗口。"""
    bases = [os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"),
             os.environ.get("LOCALAPPDATA")]
    for label, rels in BROWSER_EXES:
        for rel in rels:
            for base in bases:
                if not base:
                    continue
                p = Path(base) / rel
                if p.is_file():
                    return str(p), label
    return None, None


def _shell_exec(exe, params):
    """通过系统 Shell 启动程序。

    直接 subprocess 拉起 chrome.exe，在某些权限收紧的环境里会被系统挡掉
    （进程以 0x80000003 退出）；走 ShellExecute 相当于替你双击一次，最稳。
    """
    if platform.system() != "Windows":
        return False
    try:
        import ctypes
        rc = ctypes.windll.shell32.ShellExecuteW(None, "open", str(exe), params, None, 1)
        return rc > 32
    except Exception:
        return False


def _chrome_windows():
    """当前有几个可见的 Chrome/Edge 顶层窗口。用来判断新窗口到底有没有开出来。"""
    if platform.system() != "Windows":
        return []
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    found = []

    def cb(hwnd, lp):
        try:
            buf = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(hwnd, buf, 256)
            if buf.value.startswith("Chrome_WidgetWin_") and u.IsWindowVisible(hwnd):
                found.append(hwnd)
        except Exception:
            pass
        return True

    callback = CB(cb)  # 留引用，否则枚举途中会被回收
    try:
        u.EnumWindows(callback, 0)
    except Exception:
        return []
    return found


def _wait_new_window_hwnd(baseline, timeout=7.0):
    """等到出现新的可见浏览器窗口，返回新窗口句柄列表（没出现则空列表）。"""
    before = set(baseline or [])
    end = time.time() + timeout
    while time.time() < end:
        now = _chrome_windows()
        new = [h for h in now if h not in before]
        if new:
            return new
        time.sleep(0.4)
    return []


def _desktop_info():
    """打印当前进程所在的窗口站/桌面/会话，用来判断它能不能操作桌面。"""
    if platform.system() != "Windows":
        return ""
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        u32 = ctypes.windll.user32
        sid = ctypes.c_ulong()
        k32.ProcessIdToSessionId(k32.GetCurrentProcessId(), ctypes.byref(sid))

        def obj_name(handle, idx):
            buf = ctypes.create_unicode_buffer(256)
            need = ctypes.c_ulong()
            if u32.GetUserObjectInformationW(handle, idx, buf, 512, ctypes.byref(need)):
                return buf.value
            return "?"

        ws = obj_name(u32.GetProcessWindowStation(), 2)
        desk = obj_name(u32.GetThreadDesktop(k32.GetCurrentThreadId()), 2)
        fg = u32.GetForegroundWindow()
        return f"会话={sid.value} 窗口站={ws} 桌面={desk} 前台窗口={fg}"
    except Exception as e:
        return f"(取不到: {e})"


def _popen_window(exe, url, profile=None):
    """直接起进程开 --app 窗口。返回 (是否发起成功, 进程对象)。"""
    args = [exe, f"--app={url}", "--window-size=1400,940",
            "--no-first-run", "--no-default-browser-check",
            "--no-proxy-server"]  # 本地地址不能走系统代理，否则页面加载失败
    if profile is not None:
        profile.mkdir(parents=True, exist_ok=True)
        args.append(f"--user-data-dir={profile}")
    try:
        return True, subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"  启动窗口失败：{e}", flush=True)
        return False, None


def _focus_window(hwnds):
    """把新窗口提到最前面，避免它开在别的窗口后面。"""
    if platform.system() != "Windows" or not hwnds:
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        h = hwnds[-1]
        u.ShowWindow(h, 9)  # SW_RESTORE
        u.SetForegroundWindow(h)
        u.BringWindowToTop(h)
    except Exception:
        pass


def open_app_window(url: str):
    """用一个没有地址栏、没有标签页的独立窗口打开，像桌面软件一样。

    实测结论（很关键）：
    - URL 不能加引号，否则浏览器当非法参数丢弃；
    - 必须给独立配置目录，否则浏览器会「交接」给别的实例后静默退出，窗口根本不出现；
    - 用 subprocess 直接起进程最可靠（ShellExecute 在这台机器上会静默失败）；
    - 要加 --no-proxy-server，否则本地地址会被系统代理拦掉、页面白屏；
    - 首次要建配置目录，窗口大概 7 秒才出来，超时要给足；
    - 出来后主动置顶，不然可能藏在别的窗口后面。
    """
    exe, label = find_browser_exe()
    print(f"  桌面环境：{_desktop_info()}", flush=True)
    if exe:
        base = _chrome_windows()
        print(f"  启动前可见浏览器窗口：{len(base)}", flush=True)
        ok, _ = _popen_window(exe, url, config.DATA / "uiwindow")
        new = _wait_new_window_hwnd(base, 15.0)
        if ok and new:
            _focus_window(new)
            return True, f"{label} 应用窗口"
        print(f"  {label} 应用窗口没出现，改用不带独立配置的窗口", flush=True)

        base = _chrome_windows()
        ok, _ = _popen_window(exe, url)
        new = _wait_new_window_hwnd(base, 12.0)
        if ok and new:
            _focus_window(new)
            return True, f"{label} 独立窗口"
        print(f"  {label} 独立窗口也没出现", flush=True)

    try:
        import webbrowser
        webbrowser.open(url)
        # 走到这里说明浏览器窗口/标签页都没法确认，交给上层弹提示
        return False, "浏览器打不开，需要手动访问"
    except Exception:
        return False, "打不开窗口，请手动访问上面的地址"


def _copy_to_clipboard(text: str) -> bool:
    """把地址放进剪贴板，用户切到浏览器 Ctrl+V 就能打开。"""
    if platform.system() != "win32":
        return False
    try:
        import ctypes
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        u32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        if not u32.OpenClipboard(None):
            return False
        try:
            u32.EmptyClipboard()
            data = text.encode("utf-16-le") + b"\x00\x00"
            h = k32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            p = k32.GlobalLock(h)
            ctypes.memmove(p, data, len(data))
            k32.GlobalUnlock(h)
            u32.SetClipboardData(CF_UNICODETEXT, h)
        finally:
            u32.CloseClipboard()
        return True
    except Exception:
        return False


def _notify(msg, title="收藏学习台"):
    """弹一个系统提示框。窗口开不出来时至少让用户知道程序在跑。"""
    if platform.system() != "win32":
        print(msg, flush=True)
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(msg), title, 0x40)
    except Exception:
        print(msg, flush=True)


def open_path(p):
    p = str(p)
    sysname = platform.system()
    if sysname == "Windows":
        # 有些环境（提权/沙箱/非交互会话）里 os.startfile 会报 WinError 5，
        # 直接用 explorer 打开目录更稳。
        try:
            os.startfile(p)  # noqa
        except OSError:
            subprocess.Popen(["explorer.exe", p])
    elif sysname == "Darwin":
        subprocess.Popen(["open", p])
    else:
        subprocess.Popen(["xdg-open", p])


def reveal(p):
    p = str(p)
    sysname = platform.system()
    if sysname == "Windows":
        subprocess.Popen(["explorer.exe", "/select," + p])
    elif sysname == "Darwin":
        subprocess.Popen(["open", "-R", p])
    else:
        subprocess.Popen(["xdg-open", str(Path(p).parent)])


class Handler(BaseHTTPRequestHandler):
    server_version = "DouyinStudy/1.0"
    # 单个连接最多占用 20 秒：浏览器被关掉/网络断了的时候，别让线程一直吊在那里
    timeout = 20

    def log_message(self, *a):
        pass

    # ---------------------------------------------------------- 工具
    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        enc = (self.headers.get("Accept-Encoding") or "").lower()
        gz = "gzip" in enc and len(body) > 2048
        if gz:
            import gzip as _gz
            body = _gz.compress(body, 6)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if gz:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _err(self, msg, code=400):
        self._json({"error": msg}, code)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _static(self, rel):
        p = (STATIC / rel).resolve()
        if STATIC not in p.parents or not p.is_file():
            return self._err("not found", 404)
        data = p.read_bytes()
        if rel in ("index.html", "print.html"):
            # 脚本/样式带上文件时间戳，改完刷新就能拿到新代码，不会被浏览器缓存卡住
            import time as _t
            for asset in ("app.js", "style.css"):
                f = STATIC / asset
                if f.is_file():
                    v = str(int(f.stat().st_mtime))
                    data = data.replace(f'/static/{asset}"'.encode(), f'/static/{asset}?v={v}"'.encode())
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        enc = (self.headers.get("Accept-Encoding") or "").lower()
        gz = "gzip" in enc and len(data) > 2048 and (
            ctype.startswith("text/") or "javascript" in ctype or "json" in ctype or "svg" in ctype)
        if gz:
            import gzip as _gz
            data = _gz.compress(data, 6)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if gz:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _restore_upload(self, dry):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return self._err("没有收到备份文件")
        if n > 3 * 1024 ** 3:
            return self._err("备份文件太大")
        tmpdir = Path(tempfile.mkdtemp(prefix="dsrs-"))
        f = tmpdir / "upload.zip"
        try:
            with open(f, "wb") as out:
                left = n
                while left > 0:
                    chunk = self.rfile.read(min(left, 1024 * 256))
                    if not chunk:
                        break
                    out.write(chunk)
                    left -= len(chunk)
            if dry:
                return self._json(backup.inspect(f))
            why = self._busy_reason()
            if why:
                return self._err(why)
            res = backup.restore(f)
            backup.prune_auto_backups(keep=5)
            worker.log(f"已从备份恢复：{res['items']} 条，其中 {res['done']} 条笔记；恢复前的数据已自动备份")
            return self._json(res)
        except backup.BackupError as e:
            return self._err(str(e))
        except Exception as e:
            traceback.print_exc()
            return self._err(f"恢复失败：{e}", 500)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _download(self, text, filename, ctype):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        if filename:
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, f, ctype):
        size = f.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{urllib.parse.quote(f.name)}")
        self.send_header("Content-Length", str(size))
        self.end_headers()
        with open(f, "rb") as fh:
            shutil.copyfileobj(fh, self.wfile, 1024 * 256)

    def _busy_reason(self):
        if worker.state.get("busy"):
            return "后台正在处理视频，请先等处理完或点「停止」，再恢复备份"
        d = deep_runner.snapshot()
        if d.get("item_id") or d.get("pending"):
            return "正在精读，请等精读完成后再恢复备份"
        if insight_runner.snapshot().get("pending"):
            return "正在整理共识观点，请等整理完成后再恢复备份"
        return None

    def _local_only(self):
        # 防止别的网站在你浏览器里偷偷调用这个本地服务
        origin = self.headers.get("Origin")
        if origin and not origin.startswith(("http://127.0.0.1", "http://localhost")):
            self._err("forbidden", 403)
            return False
        return True

    # ---------------------------------------------------------- 原视频
    def _stream_file(self, f):
        """本地 mp4 直接播，带 Range，能拖进度条。"""
        size = f.stat().st_size
        start, end = 0, size - 1
        rng = self.headers.get("Range") or ""
        if rng.startswith("bytes="):
            try:
                a, _, b = rng[6:].partition("-")
                start = int(a) if a else 0
                end = int(b) if b else size - 1
            except ValueError:
                start, end = 0, size - 1
            start = max(0, min(start, size - 1))
            end = max(start, min(end, size - 1))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            with open(f, "rb") as fh:
                fh.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = fh.read(min(262144, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _drop_cache(self, it):
        """删掉这条视频的本地缓存文件（进回收站时用）。"""
        aid = str(it.get("aweme_id") or "")
        if not aid:
            return
        name = f"xhs_{aid}.mp4" if (it.get("platform") or "douyin") == "xhs" else f"{aid}.mp4"
        for n in (name, name + ".part"):
            cache.remove_file(config.MEDIA_DIR / n)

    def _video(self, item):
        """把原视频代理过来播放（带 Range 支持，可以拖着看）。"""
        aweme_id = str(item.get("aweme_id") or "")
        if not aweme_id:
            return self._err("这条没有原视频地址", 404)
        # 先看本地缓存（最快），没有再退到直链/解析
        name = f"xhs_{aweme_id}.mp4" if (item.get("platform") or "douyin") == "xhs" else f"{aweme_id}.mp4"
        local = config.MEDIA_DIR / name
        try:
            if local.is_file() and local.stat().st_size > 10240:
                return self._stream_file(local)
        except OSError:
            pass
        pu, pts = item.get("play_url"), item.get("play_url_ts") or 0
        if pu and time.time() - float(pts) < 6 * 3600:
            # 第一次点开是网络流；顺手在后台存一份，下次点开就秒开
            self._warm_cache(item["id"], pu, config.MEDIA_DIR / f"{aweme_id}.mp4")
            return self._proxy_media(pu)
        if (item.get("platform") or "douyin") == "xhs":
            key = "xhs:" + aweme_id
            with _META_LOCK:
                got = _META_CACHE.get(key)
                if got and time.time() - got[1] < 600:
                    return self._proxy_media(got[0])
            url = xhs.resolve_video_url(aweme_id, log=print, url=item.get("url"))
            if not url:
                return self._err("取不到小红书视频地址（可能需要先登录小红书）", 404)
            with _META_LOCK:
                _META_CACHE[key] = (url, time.time())
            return self._proxy_media(url)
        url = dy_runner.cached_url(aweme_id)
        if not url:
            try:
                url = dy_runner.fetch_play_url(aweme_id)
            except Exception as e:
                return self._err(f"取播放地址失败：{str(e)[:120]}", 502)
            if not url:
                return self._err("取不到播放地址（视频可能已删除，或在浏览器里需要过一下验证）", 404)
        return self._proxy_media(url)

    _warming = set()
    _warming_lock = threading.Lock()

    def _warm_cache(self, item_id, url, dest):
        """点开视频时在后台悄悄存一份，不拖慢这次播放。"""
        if dest.is_file() and dest.stat().st_size > 10240:
            return
        try:
            if cache.all_state().get("on"):
                return          # 全量缓存正在跑，别和它抢同一个文件
        except Exception:
            pass
        with Handler._warming_lock:
            if item_id in Handler._warming:
                return
            Handler._warming.add(item_id)

        def job():
            try:
                cache.download([url], dest, item_id=item_id,
                               referer="https://www.douyin.com/")
            except Exception:
                pass
            finally:
                try:
                    dest.with_suffix(dest.suffix + ".part").unlink(missing_ok=True)
                except Exception:
                    pass
                with Handler._warming_lock:
                    Handler._warming.discard(item_id)
        threading.Thread(target=job, daemon=True, name="warm-video").start()

    def _proxy_media(self, url):
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.douyin.com/"}
        rng = self.headers.get("Range")
        if rng:
            headers["Range"] = rng
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30)
        except urllib.error.HTTPError as e:
            return self._err(f"视频源返回 {e.code}", 502)
        except Exception as e:
            return self._err(f"连不上视频源：{str(e)[:100]}", 502)
        try:
            self.send_response(r.status if r.status in (200, 206) else 200)
            for h in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
                v = r.headers.get(h)
                if v:
                    self.send_header(h, v)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            try:
                r.close()
            except Exception:
                pass

    # ---------------------------------------------------------- GET
    def do_GET(self):
        _cancel_quit()
        u = urllib.parse.urlparse(self.path)
        path, qs = u.path, urllib.parse.parse_qs(u.query)
        q = lambda k, d=None: (qs.get(k) or [d])[0]

        if path in ("/", "/index.html"):
            return self._static("index.html")
        if path == "/print":
            return self._static("print.html")
        if path.startswith("/static/"):
            return self._static(path[len("/static/"):])
        if path.startswith("/files/"):  # 笔记目录里的图片（图文）
            rel = urllib.parse.unquote(path[len("/files/"):])
            lib = config.library_dir().resolve()
            f = (lib / rel).resolve()
            if lib not in f.parents or not f.is_file():
                return self._err("not found", 404)
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            if f.suffix.lower() == ".webp":
                ctype = "image/webp"
            data = f.read_bytes()
            etag = '"%d-%d"' % (int(f.stat().st_mtime), len(data))
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")   # 文件可能被修复/替换，必须回源校验
            self.end_headers()
            self.wfile.write(data)
            return

        if path == "/api/ping":
            # 启动器探活用：不读数据库、不读配置，必须秒回
            return self._json({"ok": True, "version": __version__})
        if path == "/api/audit_cats":
            try:
                return self._json(cataudit.run())
            except Exception as e:
                return self._err(f"分类自查失败：{str(e)[:80]}", 500)
        if path == "/api/bili/status":
            try:
                from . import bili_login
                return self._json({"logged_in": bool(bili_login.logged_in())})
            except Exception:
                return self._json({"logged_in": False})
        if path == "/api/skills":
            return self._json({"report": skills.report(), "progress": skills.progress()})
        if path == "/api/today":
            return self._json(db.today_summary())
        if path == "/api/cache":
            st = cache.stats()
            st["all"] = cache.all_state()
            # 把缓存文件和条目对上：标题、封面，按时间从新到旧
            awemes = []
            for f in st["files"]:
                stem = f["name"][:-4]
                awemes.append(stem[4:] if stem.startswith("xhs_") else stem)
            info = db.items_by_aweme(awemes)
            out = []
            for f in st["files"]:
                stem = f["name"][:-4]
                aid = stem[4:] if stem.startswith("xhs_") else stem
                it = info.get(aid) or {}
                out.append({"aweme_id": aid, "id": it.get("id"), "title": it.get("title") or aid,
                            "cover": it.get("cover"), "platform": it.get("platform") or "douyin",
                            "duration": it.get("duration") or 0,
                            "bytes": f["bytes"], "mtime": f["mtime"], "name": f["name"]})
            out.sort(key=lambda x: -x["mtime"])
            st["files"] = out
            return self._json(st)
        if path == "/api/meta":
            return self._json({"providers": config.PROVIDERS, "free_plans": config.FREE_PLANS})
        if path == "/api/state":
            # 一次 /api/state 里 db.stats() 要跑两遍、还要读配置读依赖，
            # 多个窗口/标签页每秒轮询一次就把它压垮了。这里缓存 0.8 秒，
            # 响应快很多，也不影响看到进度。
            now = time.time()
            with _STATE_LOCK:
                if _STATE_CACHE[0] and now - _STATE_CACHE[0] < 0.8:
                    return self._json(_STATE_CACHE[1])
            s = config.load()
            st = db.stats()
            payload = {
                "worker": dict(worker.state, paused=bool(worker.paused)), "logs": list(worker.logs)[-80:], "stats": st,
                "settings": config.public(s),
                "library_dir": str(config.library_dir()), "inbox_dir": str(config.INBOX_DIR),
                "asr": transcribe.engine_status(),
                "ocr": ocr.status(), "version": __version__, "deps": deps_status(),
                "progress": worker.prog.snapshot(max(0, st["by_status"].get("queued", 0))),
                "deep": deep_runner.snapshot(),
                "insights": insight_runner.snapshot(),
                "classify": classify_runner.snapshot(),
                "cache": {"active": len(cache.active()), "all": cache.all_state()},
                "login": config.login_status(),
                "trash_n": db.trash_count(),
                "dups_n": db.dups_count(),
                "dy": dy_runner.snapshot(),
            }
            with _STATE_LOCK:
                _STATE_CACHE[0], _STATE_CACHE[1] = time.time(), payload
            return self._json(payload)
        if path == "/api/graph":
            return self._json(insights.graph())
        if path == "/api/insights":
            return self._json({"categories": insights.categories(), "runner": insight_runner.snapshot()})
        if path.startswith("/api/insights/"):
            cat = urllib.parse.unquote(path[len("/api/insights/"):])
            ins = db.get_insight(cat)
            if not ins:
                return self._err("这个分类还没整理过共识观点", 404)
            titles = {it["id"]: (it.get("note") or {}).get("title") or it.get("title") or "未命名"
                      for it in db.done_items()}
            ins["titles"] = {i: titles[i] for i in ins["item_ids"] if i in titles}
            return self._json(ins)
        if path == "/api/weekly":
            return self._json(weekly.report(int(q("offset", "0") or 0)))
        if path == "/api/weekly/due":
            # 上一周的周报有内容、而且还没看过 → 学习库里提示一下
            last = weekly.report(-1)
            return self._json({"due": last["has_any"] and config.load().get("weekly_seen") != last["week"],
                               "week": last["week"]})
        if path == "/api/backup":
            try:
                f, m = backup.create(include_keys=q("keys", "1") == "1")
            except Exception as e:
                return self._err(f"备份失败：{e}", 500)
            try:
                return self._send_file(f, "application/zip")
            finally:
                shutil.rmtree(f.parent, ignore_errors=True)
        if path == "/api/img":
            # 封面/头像代理：浏览器拿不到抖音图床时（签名过期、被拦、跨域）走这里兜底
            u = (q("u") or "").strip()
            if not u:
                return self._err("缺 u")
            if not imgcache.allowed(u):
                return self._err("不代理这个域名", 403)
            try:
                body, ctype = imgcache.get(u)
                import hashlib as _hl
                etag = '"' + _hl.md5(body).hexdigest() + '"'
                if self.headers.get("If-None-Match") == etag:
                    self.send_response(304)
                    self.send_header("ETag", etag)
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                # 取不到（图床签名过期等）就回一张 1×1 透明图：卡片底下本来就有占位底色，
                # 返回 502 只会让浏览器刷一堆红色报错
                import base64 as _b64
                blank = _b64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(blank)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(blank)
                return
        if path == "/api/backups":
            return self._json({"dir": str(backup.BACKUP_DIR), "files": backup.list_auto_backups()})
        if path.startswith("/api/items/") and (path.endswith("/comments") or path.endswith("/dycheck")):
            # 评论列表 / 点赞收藏评论数：走后台那个已登录的浏览器，把页面自己发出的接口响应接住
            try:
                item_id = int(path.split("/")[3])
            except ValueError:
                return self._err("bad id")
            it = db.get(item_id)
            if not it:
                return self._err("找不到这条", 404)
            aid = str(it.get("aweme_id") or "")
            if not aid:
                return self._err("这条没有抖音来源")
            want_c = path.endswith("/comments")
            key = ("c:" if want_c else "s:") + aid
            with _META_LOCK:
                got = _META_CACHE.get(key)
                if got and time.time() - got[1] < 600:
                    return self._json(got[0])
            try:
                stats, comments = douyin_actions.fetch_meta(aid, want_comments=want_c)
            except Exception as e:
                # 浏览器临时打不开之类的：返回空数据（200），页面上不刷红字，用户点刷新还能再来
                payload = {"comments": [], "stats": {}, "soft_error": str(e)[:100]} if want_c                     else {"stats": {}, "soft_error": str(e)[:100]}
                return self._json(payload)
            payload = ({"comments": comments, "stats": stats} if want_c else {"stats": stats})
            with _META_LOCK:
                _META_CACHE[key] = (payload, time.time())
            return self._json(payload)
        if path.startswith("/api/items/") and path.endswith("/warm"):
            try:
                item_id = int(path.split("/")[3])
            except ValueError:
                return self._err("bad id")
            it = db.get(item_id)
            if not it or not it.get("aweme_id") or (it.get("platform") or "douyin") == "xhs":
                return self._json({"ok": False})
            if it.get("play_url") and time.time() - (it.get("play_url_ts") or 0) < 3600:
                return self._json({"ok": True, "cached": True})

            def _warm():
                try:
                    url = dy_runner.fetch_play_url(it["aweme_id"])
                    if url:
                        db.update(item_id, play_url=url, play_url_ts=time.time())
                        dy_runner.remember(it["aweme_id"], url)
                except Exception:
                    pass

            import threading as _th
            _th.Thread(target=_warm, daemon=True).start()
            return self._json({"ok": True, "queued": True})
        if path.startswith("/api/items/") and path.endswith("/danmaku"):
            try:
                item_id = int(path.split("/")[3])
            except ValueError:
                return self._err("bad id")
            it = db.get(item_id)
            if not it:
                return self._err("找不到这条", 404)
            aid = str(it.get("aweme_id") or "")
            if not aid:
                return self._err("这条没有抖音来源")
            cached = dy_runner.cached_danmaku(aid)
            if cached is not None:
                return self._json({"items": cached})
            try:
                items = douyin_actions.fetch_danmaku(aid)
            except Exception as e:
                return self._err(f"取弹幕失败：{str(e)[:100]}", 502)
            dy_runner.remember_danmaku(aid, items)
            return self._json({"items": items})
        if path == "/api/trash":
            return self._json({"items": db.trash_items(), "n": db.trash_count()})
        if path == "/api/dups":
            mode = (q("mode") or "title").strip()
            if mode == "content":
                groups = db.similar_content_groups(platform=q("platform"))
            else:
                groups = db.duplicate_groups()
            return self._json({"groups": groups, "mode": mode,
                               "n": sum(len(g["items"]) - 1 for g in groups)})
        if path == "/api/items":
            learned = q("learned")
            since_s = q("since")
            scope = q("scope")
            return self._json(db.list_items(
                since=(float(since_s) if since_s else None), scope=scope,
                status=q("status"), category=q("category"), sub=q("sub"), q=(q("q") or "").strip() or None,
                learned=None if learned in (None, "") else learned == "1", starred=q("starred") == "1",
                dur=q("dur"), sort=q("sort", "new") or "new", stage=q("stage"),
                platform=q("platform")))
        if path.startswith("/api/items/"):
            parts = path.split("/")
            try:
                item = db.get(int(parts[3]))
            except (ValueError, IndexError):
                item = None
            if not item:
                return self._err("找不到这条", 404)
            sub = parts[4] if len(parts) > 4 else ""
            name = notes.safe_name((item.get("note") or {}).get("title") or item.get("title"))
            if sub == "video":
                return self._video(item)
            if sub == "anki.txt":
                if not item.get("deep"):
                    return self._err("还没有精读结果")
                return self._download(deep.anki_tsv(item["deep"]), f"{name}-Anki卡片.txt", "text/plain")
            if sub == "mindmap.html":
                d = item.get("deep") or {}
                html = deep.mindmap_html(d.get("title") or name, d.get("mindmap"))
                if q("download") == "1":
                    return self._download(html, f"{name}-思维导图.html", "text/html")
                return self._download(html, None, "text/html")
            if sub == "prompt":
                return self._json({"text": deep.prompt_for_other_ai(item, config.load())})
            if sub == "md":
                body = notes.render(item).encode("utf-8")
                fname = urllib.parse.quote(notes.safe_name((item.get("note") or {}).get("title") or item.get("title")) + ".md")
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{fname}")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            item["dsh"] = dsh.build(item) if item.get("note") else ""
            return self._json(item)
        return self._err("not found", 404)

    # ---------------------------------------------------------- POST
    def do_POST(self):
        if not self._local_only():
            return
        u = urllib.parse.urlparse(self.path)
        path = u.path
        if path == "/api/bye":
            # 窗口关了也不退出了：后台继续处理，桌面图标再点一次就能把窗口叫回来
            return self._json({"ok": True, "background": True})
        _cancel_quit()
        if path == "/api/quit":
            # 真的要退出（用户点了设置里的退出按钮）
            _STOP.set()
            return self._json({"ok": True})
        if path == "/api/restore":
            return self._restore_upload(urllib.parse.parse_qs(u.query).get("dry", ["0"])[0] == "1")
        b = self._body()

        if path == "/api/links":
            text = b.get("text", "") or ""
            jump = bool(b.get("jump", True))   # 手动添加默认插到队首
            links = douyin.extract_links(text)
            added = 0
            xhs_n = 0
            touched = []
            for link in links:
                vid, kind = douyin._match_id(link)
                item_id, new = db.add("link", aweme_id=vid, url=link, jump=jump)
                touched.append(item_id)
                if new and kind == "note":
                    db.update(item_id, media_type="note")
                elif not new:
                    old = db.get(item_id)  # 以前被跳过的图文，现在可以处理了
                    if old and old["status"] == "skipped" and "图文" in (old.get("reason") or ""):
                        db.update(item_id, status="queued", media_type="note", reason=None, attempts=0)
                        new = True
                added += int(new)
            # 小红书链接：xhslink.com 短链 / xiaohongshu.com/explore/<id>
            for raw in re.findall(r"https?://[^\s一-鿿]+", text):
                if "xhslink.com" not in raw and "xiaohongshu.com" not in raw:
                    continue
                full = xhs.expand_short_url(raw) if "xhslink.com" in raw else raw
                nid = xhs.note_id_from_url(full)
                if not nid:
                    continue
                item_id, new = db.add("xhs", aweme_id=nid, url=f"https://www.xiaohongshu.com/explore/{nid}",
                                      platform="xhs", jump=jump)
                touched.append(item_id)
                if new:
                    added += 1
                    xhs_n += 1
            # B 站：只做手动粘贴（B 站号是共用的，不做自动同步）
            bili_n = 0
            for raw in re.findall(r"https?://[^\s一-鿿]+", text):
                if "bilibili.com" not in raw and "b23.tv" not in raw:
                    continue
                bv = bili.match(raw)
                if not bv:
                    continue
                item_id, new = db.add("bili", aweme_id=bv, url=f"https://www.bilibili.com/video/{bv}/",
                                      platform="bili", jump=jump)
                touched.append(item_id)
                if new:
                    added += 1
                    bili_n += 1
            if not links and not xhs_n and not bili_n:
                return self._err("没找到抖音 / 小红书 / B 站链接。粘贴「分享 → 复制链接」得到的整段内容就行。")
            if jump:        # 新加的已在队首；已经在队列里的同一条也提到队首
                for iid in touched:
                    cur = db.get(iid)
                    if cur and cur["status"] == "queued":
                        db.jump(iid)
            if b.get("process", True) and added:
                worker.submit("process")
            return self._json({"found": len(links) + xhs_n + bili_n, "added": added,
                               "xhs": xhs_n, "bili": bili_n})

        if path == "/api/xhs/login":
            worker.submit("xhs_login", sync=bool(b.get("sync")), limit=int(b.get("limit") or 50))
            return self._json({"ok": True, "msg": "已打开小红书浏览器，请扫码登录"})
        if path == "/api/xhs/qr":
            f = config.DATA / "tmp" / "xhs_qr.png"
            if not f.is_file():
                return self._err("还没有二维码", 404)
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/xhs/sync":
            limit = int(b.get("limit") or 0)
            worker.submit("xhs_sync", limit=limit, then_process=bool(b.get("process", True)))
            return self._json({"ok": True})
        if path == "/api/login/check":
            worker.submit("check_login")
            return self._json({"ok": True})
        if path == "/api/retry_failed":
            n = db.requeue_failed()
            worker.submit("process")
            return self._json({"ok": True, "n": n})
        if path == "/api/process":
            worker.submit("process")
            return self._json({"ok": True})
        if path == "/api/dups/keep":
            # 用户确认「留这条，其余进回收站」
            try:
                keep = int(b.get("keep") or 0)
                drop = [int(x) for x in (b.get("drop") or []) if str(x).isdigit()]
            except Exception:
                return self._err("参数不对")
            drop = [x for x in drop if x != keep]
            if not drop:
                return self._err("没有要删的条目")
            n = 0
            for i in drop:
                it = db.get(i)
                if not it:
                    continue
                db.trash(i)
                n += 1
            db._sim_cache["key"] = None  # 下次查重重新算
            worker.log(f"重复清理：保留 #{keep}，把 {n} 条相似内容移进回收站")
            return self._json({"ok": True, "trashed": n})
        if path == "/api/irrelevant/recheck":
            # 老版本「关注主题」只写了 AI，把摄影/美食/健身误判成无关；这里重新审查再放回
            return self._json(recheck.recheck_all(config.load(), log=worker.log))
        if path == "/api/trash/empty":
            items = [db.get(r["id"]) for r in db.trash_items(limit=20000)]
            for it in items:
                try:
                    notes.remove(it, with_images=True)
                except Exception:
                    pass
            n = db.empty_trash()
            return self._json({"deleted": n})
        if path == "/api/cache/all":
            on = bool(b.get("on", True))
            if not on:
                cache.all_stop()
                return self._json({"ok": True, "all": cache.all_state()})
            items = [it for it in db.items_with_video()
                     if not (config.MEDIA_DIR / f"{it['aweme_id']}.mp4").is_file()]
            cache.all_start(items)
            worker.submit("cache_all")
            return self._json({"ok": True, "queued": len(items), "all": cache.all_state()})
        if path == "/api/cache/del":
            name = str(b.get("name") or "")
            if not name.endswith(".mp4") or "/" in name or "\\" in name:
                return self._err("文件名不对")
            f = config.MEDIA_DIR / name
            try:
                if f.is_file():
                    f.unlink()
                return self._json({"ok": True, **cache.stats()})
            except OSError as e:
                return self._err(f"删不掉：{e}")
        if path == "/api/cache/clear":
            busy = {f"{a['id']}.mp4" for a in cache.active()}
            freed = cache.clear(keep_names=busy)
            return self._json({"ok": True, "freed": freed, **cache.stats()})
        if path == "/api/classify":
            # 规则分类是纯本地的，毫秒级，直接同步做完；AI 分类放到独立线程，不占下载队列
            mode = b.get("mode", "rule")
            scope = b.get("scope") or ("missing" if b.get("only_missing", True) else "all")
            plat = b.get("platform") or None
            if mode == "ai":
                classify_runner.submit("ai", scope=scope, platform=plat)
                return self._json({"ok": True, "mode": "ai", "scope": scope, "queued": True})
            mapping = classify.rule_classify(scope=scope, platform=plat)
            n = db.set_categories(mapping, src="rule")
            return self._json({"ok": True, "mode": "rule", "scope": scope, "n": n})
        if path == "/api/stop":
            worker.stop()
            return self._json({"ok": True})
        if path == "/api/login":
            worker.submit("login")
            return self._json({"ok": True})
        if path == "/api/sync":
            # 不再限制条数：limit=0 表示一直读到列表到底
            limit = int(b.get("limit") or 0)
            worker.submit("sync", kind=b.get("kind", "collection"), limit=limit, then_process=True)
            return self._json({"ok": True})
        if path == "/api/inbox":
            n = scan_inbox()
            if n:
                worker.submit("process")
            return self._json({"added": n})
        if path == "/api/failures/clean":
            ids = [int(x) for x in (b.get("ids") or []) if str(x).isdigit()]
            n = 0
            for i in ids:
                it = db.get(i)
                if it and it["status"] == "failed":
                    db.trash(i)
                    n += 1
            return self._json({"ok": True, "n": n})
        if path == "/api/pause":
            worker.paused = True
            return self._json({"ok": True, "paused": True})
        if path == "/api/resume":
            worker.paused = False
            if not worker.state.get("busy"):
                worker.submit("process")
            return self._json({"ok": True, "paused": False})
        if path == "/api/skills/review":
            ok = skills.review_async()
            return self._json({"ok": True, "started": ok})
        if path == "/api/skills/mark":
            n = skills.mark(b.get("ids") or [], b.get("field") or "installed",
                            bool(b.get("value", True)))
            return self._json({"ok": True, "n": n})
        if path == "/api/bili/login":
            worker.submit("bili_login")
            return self._json({"ok": True, "msg": "已打开 B 站登录页，扫码即可"})
        if path == "/api/retry_fetch_failed":
            worker.submit("retry_fetch_failed")
            return self._json({"ok": True})
        if path == "/api/reclassify":
            worker.submit("reclassify", only=b.get("only") or None)
            return self._json({"ok": True})
        if path == "/api/fix_covers":
            worker.submit("fix_covers")
            return self._json({"ok": True})
        if path == "/api/open":
            what = b.get("what")
            try:
                if what == "library":
                    open_path(config.library_dir())
                elif what == "inbox":
                    open_path(config.INBOX_DIR)
                elif what == "media":
                    open_path(config.MEDIA_DIR)
                elif what == "item":
                    it = db.get(int(b.get("id")))
                    if it and it.get("md_path") and Path(it["md_path"]).exists():
                        reveal(it["md_path"])
                    else:
                        return self._err("这条还没有生成笔记文件")
                elif what == "insight":
                    ins = db.get_insight(str(b.get("category") or ""))
                    if not ins or not ins.get("md_path") or not Path(ins["md_path"]).exists():
                        return self._err("还没有生成共识观点文件")
                    reveal(ins["md_path"])
                return self._json({"ok": True})
            except Exception as e:
                return self._err(f"打不开：{e}")

        if path == "/api/insights":
            cat = str(b.get("category") or "").strip()
            if not cat:
                return self._err("缺少分类")
            if not (config.llm_cfg(config.load(), "deep").get("api_key") or "").strip():
                return self._err("还没保存 AI Key。请到「设置」填好 Key，点「测试连接」（成功会自动保存）。")
            insight_runner.submit(cat)
            return self._json({"ok": True})
        if path == "/api/weekly/save":
            try:
                f = weekly.save_md(int(b.get("offset") or 0))
                reveal(f)
            except Exception as e:
                return self._err(f"保存失败：{e}")
            return self._json({"path": f})
        if path == "/api/weekly/seen":
            config.save({"weekly_seen": str(b.get("week") or "")})
            return self._json({"ok": True})

        if path == "/api/settings":
            patch = {k: v for k, v in b.items()
                     if k in config.DEFAULTS and k not in ("tokens_used", "tokens_weekly", "weekly_seen")}
            if "api_key" in patch and not str(patch["api_key"]).strip():
                patch.pop("api_key")  # 空着表示不修改
            if "deep_api_key" in patch and not str(patch["deep_api_key"]).strip():
                patch.pop("deep_api_key")
            if b.get("clear_key"):
                patch["api_key"] = ""
            if b.get("clear_deep_key"):
                patch["deep_api_key"] = ""
            if "deep_chunk_chars" in patch:
                patch["deep_chunk_chars"] = max(3000, min(100000, int(patch["deep_chunk_chars"] or 12000)))
            if "deep_prompt" in patch and not str(patch["deep_prompt"]).strip():
                patch["deep_prompt"] = config.DEFAULT_DEEP_PROMPT
            if "max_minutes" in patch:
                patch["max_minutes"] = max(1, min(120, int(patch["max_minutes"] or 15)))
            if isinstance(patch.get("categories"), str):
                patch["categories"] = [c.strip() for c in patch["categories"].replace("，", ",").split(",") if c.strip()]
            s = config.save(patch)
            return self._json(config.public(s))
        if path == "/api/test_llm":
            s = config.load()
            purpose = "deep" if b.get("purpose") == "deep" else "main"
            cfg = config.llm_cfg(s, purpose)
            for k in ("provider", "base_url", "model"):
                if b.get(k):
                    cfg[k] = b[k]
            if (b.get("api_key") or "").strip():
                cfg["api_key"] = b["api_key"].strip()
            cfg["kind"] = config.provider_kind(cfg.get("provider"), cfg.get("base_url"))
            try:
                reply = llm.test(cfg)
            except llm.LLMError as e:
                return self._json({"ok": False, "error": str(e)})
            # 测试成功就直接保存，免得忘了点「保存设置」
            if purpose == "deep":
                patch = {"deep_provider": cfg.get("provider"), "deep_base_url": cfg.get("base_url"),
                         "deep_model": cfg.get("model"), "deep_same": False}
                if (b.get("api_key") or "").strip():
                    patch["deep_api_key"] = cfg["api_key"]
            else:
                patch = {"provider": cfg.get("provider"), "base_url": cfg.get("base_url"), "model": cfg.get("model")}
                if (b.get("api_key") or "").strip():
                    patch["api_key"] = cfg["api_key"]
            config.save({k: v for k, v in patch.items() if v is not None})
            models = []
            try:
                models = llm.list_models(cfg)
            except llm.LLMError:
                pass
            return self._json({"ok": True, "reply": reply, "saved": True, "models": models})
        if path == "/api/free_setup":
            plan = b.get("plan")
            key = str(b.get("api_key") or "").strip()
            if plan not in config.FREE_PLANS:
                return self._err("未知的免费方案")
            if not key:
                return self._err("先把 Key 粘贴进来")
            try:
                model, tried = llm.free_setup(plan, key)
            except llm.LLMError as e:
                return self._err(str(e))
            p = config.FREE_PLANS[plan]
            config.save({"provider": p["provider"], "base_url": p["base_url"], "model": model, "api_key": key,
                         "deep_same": True, "free_plan": plan})
            worker.log(f"已配置免费方案：{p['name']} · {model}")
            return self._json({"ok": True, "plan": plan, "name": p["name"], "model": model, "tried": tried})
        if path == "/api/models":
            s = config.load()
            purpose = "deep" if b.get("purpose") == "deep" else "main"
            cfg = config.llm_cfg(s, purpose)
            for k in ("provider", "base_url"):
                if b.get(k):
                    cfg[k] = b[k]
            if (b.get("api_key") or "").strip():
                cfg["api_key"] = b["api_key"].strip()
            cfg["kind"] = config.provider_kind(cfg.get("provider"), cfg.get("base_url"))
            try:
                return self._json({"models": llm.list_models(cfg)})
            except llm.LLMError as e:
                return self._err(str(e))

        if path == "/api/restore_auto":
            name = Path(str(b.get("name") or "")).name
            f = backup.BACKUP_DIR / name
            if not name.endswith(".zip") or not f.exists():
                return self._err("找不到这个自动备份")
            why = self._busy_reason()
            if why:
                return self._err(why)
            try:
                return self._json(backup.restore(f))
            except backup.BackupError as e:
                return self._err(str(e))

        if path == "/api/paste":
            text = str(b.get("text") or "").strip()
            if len(text) < 50:
                return self._err("文稿太短了，至少要 50 个字")
            title = str(b.get("title") or "").strip() or text[:20].replace("\n", " ") + "…"
            dcfg = config.llm_cfg(config.load(), "deep")
            if not (dcfg.get("api_key") or "").strip():
                return self._err("精读用的 AI Key 还没保存。请到「设置」填好 Key，点「测试连接」（成功会自动保存）。")
            item_id, _ = db.add("paste", title=title, author=str(b.get("author") or "").strip() or None, jump=True)
            db.update(item_id, transcript=text, status="done")
            deep_runner.submit(item_id)
            return self._json({"id": item_id})

        if path.startswith("/api/items/") and path.split("/")[-1] in ("deep", "check", "ask", "quiz"):
            try:
                item_id = int(path.split("/")[3])
            except ValueError:
                return self._err("bad id")
            act = path.split("/")[-1]
            try:
                if act == "deep":
                    if not (db.get(item_id) or {}).get("transcript"):
                        return self._err("这条还没有文字稿，等处理完再精读")
                    dcfg = config.llm_cfg(config.load(), "deep")
                    if not (dcfg.get("api_key") or "").strip():
                        return self._err("精读用的 AI Key 还没保存。请到「设置」填好 Key，点「测试连接」（成功会自动保存）。")
                    if not (dcfg.get("model") or "").strip():
                        return self._err("精读用的模型名是空的，请到「设置」里选一个模型")
                    deep_runner.submit(item_id)
                    return self._json({"ok": True, "model": dcfg["model"]})
                if act == "check":
                    ans = str(b.get("answer") or "").strip()
                    if not ans:
                        return self._err("先写下你的回答")
                    return self._json(deep.check_answer(item_id, int(b.get("idx", -1)), ans))
                if act == "ask":
                    qtext = str(b.get("q") or "").strip()
                    if not qtext:
                        return self._err("问题不能为空")
                    return self._json(deep.ask(item_id, qtext))
                if act == "quiz":
                    deep.quiz_result(item_id, int(b.get("score", 0)), int(b.get("total", 0)))
                    return self._json({"ok": True})
            except llm.LLMError as e:
                return self._err(str(e))

        if path.startswith("/api/items/") and path.endswith("/dy"):
            # 抖音动作：点赞 / 取消点赞 / 收藏 / 取消收藏 / 发评论
            try:
                item_id = int(path.split("/")[3])
            except ValueError:
                return self._err("bad id")
            it = db.get(item_id)
            if not it:
                return self._err("找不到这条", 404)
            if not it.get("aweme_id"):
                return self._err("这条没有抖音原视频")
            action = (b.get("action") or "").strip()
            if action not in ("like", "collect", "uncollect", "comment", "state"):
                return self._err("不支持的操作")
            if action == "comment" and not (b.get("text") or "").strip():
                return self._err("评论内容不能为空")
            dy_runner.submit(action, it["aweme_id"], b.get("text") or "")
            return self._json({"ok": True, "action": action})

        if path.startswith("/api/items/") and path.endswith("/action"):
            try:
                item_id = int(path.split("/")[3])
            except ValueError:
                return self._err("bad id")
            it = db.get(item_id)
            if not it:
                return self._err("找不到这条", 404)
            act = b.get("action")
            if act == "retry" and any(k in (it.get("reason") or "") for k in ("抓取失败", "通用页", "播放地址", "没有画面")):
                # 抓取类的失败：旧的文字稿是垃圾，必须丢掉重新抓
                db.update(item_id, transcript=None, note=None, images=None, md_path=None)
                it = db.get(item_id)
            if act in ("retry", "reextract", "include"):
                if act == "include" and it.get("note"):
                    # 用户认为"无关"的也值得学 → 直接收进学习库，不用再花钱提炼
                    it["note"]["relevant"] = True
                    path_ = notes.write(it)
                    db.update(item_id, status="done", note=it["note"], md_path=path_, reason=None)
                    return self._json(db.get(item_id))
                db.update(item_id, status="queued", attempts=0, reason=None, auto_skip=2)
                worker.submit("process")
            elif act == "learned":
                v = bool(b.get("value", True))
                db.update(item_id, learned=int(v), learned_at=time.time() if v else None)
            elif act == "jump":
                # 插队：排到队首，下一个就处理它
                if it["status"] in ("fetching", "downloading", "transcribing", "extracting"):
                    return self._err("这条正在处理，不用插队")
                if it["status"] == "done":
                    return self._err("这条已经处理完了")
                db.jump(item_id)
                db.update(item_id, status="queued", attempts=0, reason=None, auto_skip=2)
                # 正在跑的那一批不用打断：它每处理完一条都会重新取队首，插队的自然就是下一个
                if not worker.state.get("busy"):
                    worker.submit("process")
            elif act == "star":
                db.update(item_id, starred=int(bool(b.get("value", True))))
            elif act == "note":
                db.update(item_id, my_note=str(b.get("text", ""))[:20000])
                it = db.get(item_id)
                if it["status"] == "done":
                    db.update(item_id, md_path=notes.write(it))
            elif act == "category":
                cat = str(b.get("value") or "").strip()
                if cat and it.get("note"):
                    it["note"]["category"] = cat
                    db.update(item_id, note=it["note"], category=cat, category_src="manual")
                    it = db.get(item_id)
                    if it["status"] == "done":
                        db.update(item_id, md_path=notes.write(it))
            elif act == "delete":
                self._drop_cache(it)       # 本地缓存也一起删
                db.trash(item_id)          # 记录进回收站，可以恢复
                return self._json({"deleted": True, "trashed": True})
            elif act == "unfavorite":
                # 取消收藏：抖音那边同时取消（异步）+ 删本地缓存 + 进回收站
                if it.get("aweme_id") and (it.get("platform") or "douyin") != "xhs":
                    dy_runner.submit("uncollect", it["aweme_id"], "")
                self._drop_cache(it)
                db.trash(item_id)
                return self._json({"deleted": True, "trashed": True, "unfavorited": True})
            elif act == "restore":
                db.restore(item_id)
                return self._json({"restored": True})
            elif act == "purge":
                notes.remove(it, with_images=True)
                db.delete(item_id)
                return self._json({"purged": True})
            else:
                return self._err("未知操作")
            return self._json(db.get(item_id))

        return self._err("not found", 404)


def _safe_audit():
    """启动时跑一次分类自查，报告写到 data/tmp/cat_audit.md（不打扰用户）。"""
    try:
        r = cataudit.run()
        n = r.get("suspicious_n", 0)
        try:
            worker.log(f"分类自查：疑似分错 {n} 条，报告 data/tmp/cat_audit.md")
        except Exception:
            pass
    except Exception as e:
        try:
            worker.log(f"分类自查失败：{str(e)[:60]}")
        except Exception:
            pass


def serve(port=8765, open_browser=True):
    global worker
    tmp = ensure_temp()
    db.init()
    worker = Worker()
    # 启动时顺手做一次分类自查（纯规则，很快），报告写到 data/tmp/cat_audit.md
    threading.Thread(target=lambda: _safe_audit(), daemon=True, name="cataudit").start()
    global deep_runner
    deep_runner = deep.DeepRunner(worker.log)
    global insight_runner
    insight_runner = insights.InsightRunner(worker.log)
    global classify_runner
    classify_runner = classify.Runner()
    global dy_runner
    dy_runner = douyin_actions.Runner(worker.log)
    # 点赞/评论要用的浏览器 = 后台那一个（同一个登录态），没起来就让 worker 拉起来
    douyin_actions.START_BROWSER = lambda: worker.submit("dy_browser")
    srv = None
    for p in range(port, port + 20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            port = p
            break
        except OSError:
            continue
    if srv is None:
        raise SystemExit("找不到可用端口")
    threading.Thread(target=_quit_watchdog, args=(srv,), daemon=True, name="quit-watch").start()
    # 先把服务跑起来再开窗口，否则窗口可能先于服务加载，看到的是「无法访问」
    threading.Thread(target=srv.serve_forever, daemon=True, name="http").start()
    url = f"http://127.0.0.1:{port}/"
    print("=" * 56)
    print(f"  收藏学习台 v{__version__} 已启动")
    print(f"  窗口地址：{url}")
    print(f"  临时目录：{tmp}")
    print("  关掉窗口后仍在后台继续处理；要彻底退出，请到「设置」里点「退出程序」")
    print("=" * 56, flush=True)
    if open_browser:
        ok, how = open_app_window(url)
        print(f"  打开方式：{how}", flush=True)
        if not ok:
            _copy_to_clipboard(url)
            _notify("程序已经在运行了，但没能自动打开窗口。\n\n"
                    f"地址已复制到剪贴板：\n{url}\n\n"
                    "请切到浏览器，新建标签页按 Ctrl+V，回车即可打开。\n"
                    "打开一次后按 Ctrl+D 收藏，以后一点就开。")
    # 一直在后台跑：关窗口不停，只有 /api/quit（设置里的退出按钮）才会结束
    try:
        _STOP.wait()
    except KeyboardInterrupt:
        pass
    print("收到退出指令，正在退出……", flush=True)
    try:
        srv.shutdown()
    except Exception:
        pass
