"""B 站登录：扫码后把 cookie 存成 yt-dlp 能用的 Netscape 格式。

为什么要登录：B 站有些视频（清晰度、会员内容、部分番剧）不登录只给试看，
登录后 yt-dlp 才能拿到完整音视频。日常公开视频不登录也能解析。
"""
from __future__ import annotations

import time
from pathlib import Path

from . import config

PROFILE = config.BROWSER_DIR / "bili"
COOKIE = config.DATA / "bili_cookies.txt"


def cookies_file() -> Path:
    return COOKIE


def logged_in() -> bool:
    """cookie 文件里还留着 SESSDATA 就算登录过。"""
    try:
        if not COOKIE.exists():
            return False
        for line in COOKIE.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 7 and parts[5] == "SESSDATA" and len(parts[6]) > 10:
                return True
    except Exception:
        pass
    return False


def _netscape(cookies) -> str:
    lines = ["# Netscape HTTP Cookie File", "# 由收藏变笔记自动生成，用于 yt-dlp 下载 B 站视频", ""]
    for c in cookies or []:
        dom = (c.get("domain") or "")
        if "bilibili" not in dom and "b23" not in dom:
            continue
        lines.append("\t".join([
            dom,
            "TRUE" if dom.startswith(".") else "FALSE",
            c.get("path") or "/",
            "TRUE" if c.get("secure") else "FALSE",
            str(int(c.get("expires") or 0)),
            c.get("name") or "",
            c.get("value") or "",
        ]))
    return "\n".join(lines) + "\n"


def login(timeout=300, log=print) -> bool:
    """打开 B 站让你扫码，登录成功后把 cookie 存下来。"""
    from . import pw
    PROFILE.mkdir(parents=True, exist_ok=True)
    p = pw.get()
    ctx = None
    try:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE), headless=False, channel="chrome",
            viewport={"width": 1280, "height": 860}, locale="zh-CN",
            args=["--no-proxy-server", "--window-position=140,90"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto("https://www.bilibili.com/", wait_until="domcontentloaded", timeout=45000)
        except Exception:
            pass
        log("请在弹出的浏览器里扫码登录 B 站（最多等 5 分钟）……")
        ok = False
        end = time.time() + timeout
        while time.time() < end:
            try:
                cs = ctx.cookies()
            except Exception:
                cs = []
            if any(c.get("name") == "SESSDATA" and len(c.get("value") or "") > 10 for c in cs):
                COOKIE.parent.mkdir(parents=True, exist_ok=True)
                COOKIE.write_text(_netscape(cs), encoding="utf-8")
                log("B 站登录成功，cookie 已保存（下载清晰度更高的视频时就会用上）")
                ok = True
                break
            time.sleep(2)
        if not ok:
            log("等太久没扫上，B 站登录没完成")
        return ok
    except Exception as e:
        log(f"B 站登录失败：{str(e)[:80]}")
        return False
    finally:
        try:
            if ctx is not None:
                ctx.close()
        except Exception:
            pass