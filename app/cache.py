"""视频本地缓存：流式下载（带字节进度）+ 占用统计。

以前视频转完文字就删，点播放要现场从抖音 CDN 拉流。现在默认留在本地当缓存，
这里负责：下载时记录进度、统计占用、超上限时清理最老的。
"""
from __future__ import annotations

import threading
import time
import urllib.request
from pathlib import Path

from . import config

MAX_BYTES = 120 * 1024 ** 3        # 缓存上限 120G（要全量缓存，留足空间）
CHUNK = 256 * 1024

_lock = threading.Lock()
_active = {}                       # item_id -> {id,title,done,total,pct,speed,started}


def _entry(item_id, title):
    with _lock:
        e = _active.get(item_id)
        if e is None:
            e = {"id": item_id, "title": title or "", "done": 0, "total": 0,
                 "pct": 0, "speed": 0, "started": time.time(), "stage": "下载中"}
            _active[item_id] = e
        if title:
            e["title"] = title
        return e


def begin(item_id, title=""):
    _entry(item_id, title)


def stage(item_id, text):
    with _lock:
        e = _active.get(item_id)
        if e:
            e["stage"] = text


def update(item_id, done, total):
    with _lock:
        e = _active.get(item_id)
        if not e:
            return
        e["done"] = done
        if total:
            e["total"] = total
        el = max(0.001, time.time() - e["started"])
        e["speed"] = done / el
        e["pct"] = int(done * 100 / total) if total else 0


def end(item_id):
    with _lock:
        _active.pop(item_id, None)


def active():
    with _lock:
        return [dict(v) for v in _active.values()]


def stats():
    files = []
    total = 0
    try:
        for p in config.MEDIA_DIR.glob("*.mp4"):
            try:
                n = p.stat().st_size
            except OSError:
                continue
            total += n
            files.append({"name": p.name, "bytes": n, "mtime": p.stat().st_mtime})
    except Exception:
        pass
    files.sort(key=lambda x: x["mtime"])
    return {"count": len(files), "bytes": total, "files": files,
            "active": active(), "max_bytes": MAX_BYTES, "dir": str(config.MEDIA_DIR)}


def clear(keep_names=()):
    freed = 0
    keep = set(keep_names)
    for p in list(config.MEDIA_DIR.glob("*.mp4")) + list(config.MEDIA_DIR.glob("*.part")):
        if p.name in keep:
            continue
        try:
            n = p.stat().st_size
            remove_file(p)
            freed += n
        except OSError:
            pass
    return freed


def trim():
    """超过上限就按修改时间删最老的，留下正在下载的。"""
    st = stats()
    if st["bytes"] <= MAX_BYTES:
        return 0
    busy = {f"{a['id']}.mp4" for a in st["active"]}
    freed = 0
    cur = st["bytes"]
    try:
        paths = sorted(config.MEDIA_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    except Exception:
        return 0
    for p in paths:
        if cur <= MAX_BYTES:
            break
        if p.name in busy:
            continue
        try:
            n = p.stat().st_size
            remove_file(p)
            cur -= n
            freed += n
        except OSError:
            pass
    return freed


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")


def remove_file(path):
    """删文件：这台机器上删除会在瞬间被还原，所以删不掉就改名藏起来。"""
    p = Path(path)
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        if p.exists():
            dead = p.with_name(p.name + ".deleted")
            if dead.exists():
                dead = p.with_name(p.name + f".deleted{int(time.time())}")
            p.rename(dead)
    except OSError:
        pass


def _probe(url, referer):
    """返回 (是否支持分段, 文件大小)。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer,
                                               "Range": "bytes=0-0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        cr = r.headers.get("Content-Range") or ""
        if "/" in cr:
            try:
                return True, int(cr.rsplit("/", 1)[1])
            except ValueError:
                pass
        return False, int(r.headers.get("Content-Length") or 0)


def _fetch_range(url, referer, start, stop, fh, counter, lock, item_id, total):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer,
                                               "Range": f"bytes={start}-{stop}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        pos = start
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            fh.seek(pos)
            fh.write(chunk)
            pos += len(chunk)
            with lock:
                counter[0] += len(chunk)
                if item_id is not None:
                    update(item_id, counter[0], total)


def _probe(url, referer):
    """返回 (是否支持分段, 文件大小)。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer,
                                               "Range": "bytes=0-0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        cr = r.headers.get("Content-Range") or ""
        if "/" in cr:
            try:
                return True, int(cr.rsplit("/", 1)[1])
            except ValueError:
                pass
        return False, int(r.headers.get("Content-Length") or 0)


def _fetch_range(url, referer, start, stop, path, counter, lock, item_id, total,
                 tries=2, stall=None):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer,
                                                       "Range": f"bytes={start}-{stop}"})
            with urllib.request.urlopen(req, timeout=15) as r:
                fh = open(path, "r+b")
                try:
                    pos = start
                    while True:
                        chunk = r.read(256 * 1024)
                        if not chunk:
                            break
                        fh.seek(pos)
                        fh.write(chunk)
                        pos += len(chunk)
                        if stall is not None and stall.get("dead"):
                            raise RuntimeError("stalled")
                        with lock:
                            counter[0] += len(chunk)
                            if stall is not None:
                                stall["last"] = time.time()
                            if item_id is not None:
                                update(item_id, counter[0], total)
                finally:
                    fh.close()
            return True
        except Exception as e:
            last = e
    return False


def download(urls, dest: Path, item_id=None, title="", referer="https://www.douyin.com/",
             parts=8):
    """多线路、多连接分段下载：不同 CDN 地址 + 多线程同时拉，速度比单连接快很多。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    urls = [u for u in (urls or []) if isinstance(u, str) and u.startswith("http")]
    if not urls:
        raise RuntimeError("视频下载失败：没有可用的地址")
    last = "没有可用的视频地址"
    try:
        if item_id is not None:
            begin(item_id, title)

        # 先探第一条，拿到总大小
        ok_range, total = (False, 0)
        candidates = []
        for u in urls[:4]:
            try:
                ok, size = _probe(u, referer)
                if ok and size > 0:
                    candidates.append(u)
                    if not total:
                        total = size
            except Exception:
                continue

        if total > 600 * 1024 * 1024:
            raise RuntimeError(f"文件太大（{total//1024//1024}MB），跳过缓存，播放时在线看")
        if total > 6 * 1024 * 1024 and candidates:
            n = max(1, min(parts, total // (1024 * 1024)))
            step = total // n
            with open(part, "wb") as f:
                f.truncate(total)
            counter, lock = [0], threading.Lock()
            stall = {"last": time.time(), "dead": False}
            fails = []

            def watchdog():
                while not stop_evt.wait(5):
                    if time.time() - stall["last"] > 30:
                        stall["dead"] = True
                        return

            stop_evt = threading.Event()
            threading.Thread(target=watchdog, daemon=True).start()

            def worker(i, a, b):
                u = candidates[i % len(candidates)]
                if not _fetch_range(u, referer, a, b, part, counter, lock, item_id, total):
                    fails.append((a, b))
                    # 换一条线路再试
                    for alt in candidates:
                        if alt != u and _fetch_range(alt, referer, a, b, part, counter, lock, item_id, total):
                            fails.pop()
                            break

            ths = []
            for i in range(n):
                a = i * step
                b = total - 1 if i == n - 1 else (a + step - 1)
                t = threading.Thread(target=worker, args=(i, a, b), daemon=True)
                ths.append(t)
                t.start()
            deadline = time.time() + 90
            for t in ths:
                while t.is_alive() and time.time() < deadline:
                    t.join(1)
                    if stall["dead"]:
                        break
                if stall["dead"]:
                    break
            stop_evt.set()
            if stall["dead"]:
                # 给已阻塞的连接一点时间自己超时退出，再删半截文件
                end_at = time.time() + 20
                for t in ths:
                    t.join(max(0, end_at - time.time()))
                remove_file(part)
            if stall["dead"]:
                raise RuntimeError("下载停滞（CDN 卡住）")
            if fails:
                raise RuntimeError(f"{len(fails)} 个分段没下完")
            size = part.stat().st_size
        else:
            # 小文件或不支持分段：单连接
            done, size = 0, 0
            with open(part, "wb") as f:
                for u in urls:
                    try:
                        req = urllib.request.Request(u, headers={"User-Agent": UA, "Referer": referer,
                                                                  "Accept": "*/*"})
                        with urllib.request.urlopen(req, timeout=20) as r:
                            total2 = int(r.headers.get("Content-Length") or 0)
                            f.seek(0)
                            f.truncate(0)
                            done = 0
                            while True:
                                chunk = r.read(256 * 1024)
                                if not chunk:
                                    break
                                f.write(chunk)
                                done += len(chunk)
                                if item_id is not None:
                                    update(item_id, done, total2)
                        size = done
                        break
                    except Exception as e:
                        last = str(e).splitlines()[0][:120]
                        continue

        if size < 10 * 1024:
            raise RuntimeError("下载到的文件太小，可能是错误页")
        part.replace(dest)
        return dest
    finally:
        if item_id is not None:
            end(item_id)


# ---------------------------------------------------------------- 全部缓存任务
_all = {"on": False, "total": 0, "done": 0, "failed": 0, "current": "", "todo": []}


def all_state():
    with _lock:
        return {"on": _all["on"], "total": _all["total"], "done": _all["done"],
                "failed": _all["failed"], "current": _all["current"],
                "left": len(_all["todo"])}


def all_start(items):
    """items = [{id, aweme_id, title, ...}]，还没缓存过的那些。"""
    with _lock:
        _all.update(on=True, total=len(items), done=0, failed=0, current="", todo=list(items))


def all_stop():
    with _lock:
        _all["on"] = False
        _all["todo"] = []
        _all["current"] = ""


def all_next():
    with _lock:
        if not _all["on"] or not _all["todo"]:
            return None
        return _all["todo"].pop(0)


def all_step(done=True):
    with _lock:
        if done:
            _all["done"] += 1
        else:
            _all["failed"] += 1
        if not _all["todo"]:
            _all["on"] = False


def all_finish():
    with _lock:
        _all["on"] = False
        _all["todo"] = []
        _all["current"] = ""


def all_current(title):
    with _lock:
        _all["current"] = title or ""
