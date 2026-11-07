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


def _rank_urls(urls, referer):
    """多条线路先各试下前 700KB，优先用快的（抖音不同 CDN 速度差很多）。"""
    if len(urls) < 2:
        return urls
    scored = []
    for i, u in enumerate(urls[:5]):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Referer": referer,
                                                      "Range": "bytes=0-716800"})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=8) as r:
                n = len(r.read())
            dt = max(0.001, time.time() - t0)
            scored.append((n / dt, i, u))
        except Exception:
            scored.append((0.0, i, u))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [u for _, _, u in scored]


def download(urls, dest: Path, item_id=None, title="", referer="https://www.douyin.com/",
             parts=4):
    """下载到 dest：能分段就 4 路并发，速度比单连接快好几倍。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    last = "没有可用的视频地址"
    urls = _rank_urls(list(urls or []), referer)
    for u in urls:
        try:
            if item_id is not None:
                begin(item_id, title)
            ok_range, total = _probe(u, referer)
            if ok_range and total > 8 * 1024 * 1024:
                n = max(1, min(parts, (total // (2 * 1024 * 1024)) or 1))
                step = total // n
                ranges = []
                for i in range(n):
                    a = i * step
                    b = total - 1 if i == n - 1 else (a + step - 1)
                    ranges.append((a, b))
                counter, lock = [0], threading.Lock()
                with open(part, "wb") as f:
                    f.truncate(total)
                errs = []

                def worker(a, b):
                    try:
                        fh = open(part, "r+b")
                        try:
                            _fetch_range(u, referer, a, b, fh, counter, lock, item_id, total)
                        finally:
                            fh.close()
                    except Exception as e:
                        errs.append(e)

                ths = [threading.Thread(target=worker, args=(a, b), daemon=True) for a, b in ranges]
                for t in ths:
                    t.start()
                for t in ths:
                    t.join()
                if errs:
                    raise errs[0]
                size = part.stat().st_size
            else:
                req = urllib.request.Request(u, headers={"User-Agent": UA, "Referer": referer,
                                                          "Accept": "*/*"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    total = int(r.headers.get("Content-Length") or 0)
                    done = 0
                    with open(part, "wb") as f:
                        while True:
                            chunk = r.read(256 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                            done += len(chunk)
                            if item_id is not None:
                                update(item_id, done, total)
                    size = done
            if size < 10 * 1024:
                last = "下载到的文件太小，可能是错误页"
                part.unlink(missing_ok=True)
                continue
            part.replace(dest)
            return dest
        except Exception as e:
            last = str(e).splitlines()[0][:150]
            try:
                part.unlink(missing_ok=True)
            except OSError:
                pass
        finally:
            if item_id is not None:
                end(item_id)
    raise RuntimeError(f"视频下载失败：{last}")


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
