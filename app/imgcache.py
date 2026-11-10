"""封面图本地缓存。

浏览收藏库时，同一张封面会被反复请求（翻页、筛选、重开窗口），
每次去抖音/小红书图床拿既慢又容易遇到限流。这里按 URL 路径存一份，
第二次开始直接读本地文件。
"""
from __future__ import annotations

import hashlib
import io
import shutil
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

from . import config

CACHE_DIR = config.DATA / "imgcache"
MAX_BYTES = 400 * 1024 * 1024      # 缓存上限 400MB，超了删最老的
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

_lock = threading.Lock()


def allowed(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host.endswith((
        "douyinpic.com", "byteimg.com", "douyin.com", "ibyteimg.com",
        "xhscdn.com", "xhsimg.com", "sns-img-qc.xhscdn.com", "sns-webpic-qc.xhscdn.com",
    )) or "tos-cn" in host


def _referer(url: str) -> str:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if "xhs" in host or "sns-" in host:
        return "https://www.xiaohongshu.com/"
    return "https://www.douyin.com/"


def _key(url: str) -> str:
    """只用路径做 key：签名参数会变，但图片本身是同一张。"""
    path = urllib.parse.urlparse(url).path or url
    return hashlib.sha1(path.encode("utf-8")).hexdigest()


def _ext(ctype: str) -> str:
    ctype = (ctype or "").lower()
    if "png" in ctype:
        return ".png"
    if "webp" in ctype:
        return ".webp"
    if "gif" in ctype:
        return ".gif"
    if "avif" in ctype:
        return ".avif"
    return ".jpg"


def _lookup(k: str) -> Path | None:
    for ext in (".jpg", ".png", ".webp", ".gif", ".avif"):
        p = CACHE_DIR / (k + ext)
        if p.is_file():
            return p
    return None


def _prune():
    try:
        total, files = 0, []
        for p in CACHE_DIR.glob("*"):
            if p.is_file():
                try:
                    st = p.stat()
                except OSError:
                    continue
                total += st.st_size
                files.append((st.st_mtime, st.st_size, p))
        if total <= MAX_BYTES:
            return
        files.sort()
        for _, size, p in files:
            if total <= MAX_BYTES:
                break
            try:
                p.unlink()
                total -= size
            except OSError:
                pass
    except Exception:
        pass


def get(url: str, timeout=20):
    """返回 (bytes, content_type)。命中缓存时只读磁盘。"""
    k = _key(url)
    hit = _lookup(k)
    if hit is not None:
        try:
            ctype = "image/webp" if hit.suffix == ".webp" else f"image/{hit.suffix.lstrip('.')}"
            return hit.read_bytes(), ctype
        except OSError:
            pass

    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": _referer(url),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        ctype = (r.headers.get("Content-Type") or "image/jpeg").split(";")[0]
    if len(body) < 512:
        raise ValueError("图片太小，可能是错误页")

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        dest = CACHE_DIR / (k + _ext(ctype))
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(body)
        tmp.replace(dest)
        if hash(k) % 200 == 0:      # 偶尔整理一次，不占请求时间
            threading.Thread(target=_prune, daemon=True).start()
    except Exception:
        pass
    return body, ctype


def clear() -> int:
    freed = 0
    try:
        for p in CACHE_DIR.glob("*"):
            if p.is_file():
                try:
                    freed += p.stat().st_size
                    p.unlink()
                except OSError:
                    pass
    except Exception:
        pass
    return freed


def stats():
    count, total = 0, 0
    try:
        for p in CACHE_DIR.glob("*"):
            if p.is_file():
                count += 1
                total += p.stat().st_size
    except Exception:
        pass
    return {"count": count, "bytes": total, "max_bytes": MAX_BYTES}
