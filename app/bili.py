"""B 站视频：手动粘贴链接 → 解析信息、下音频、转文字。

和抖音/小红书不一样：B 站号是用户和别人共用的，不能自动同步，
所以这里只提供「粘贴一条链接就解析一条」的能力，不做后台同步。

流程：
  链接 → 抓页面信息（标题/作者/封面/时长/简介）
       → 有官方字幕就直接用字幕
       → 没字幕就下音频（yt-dlp）交给本机转文字
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Referer": "https://www.bilibili.com/"}

BV_RE = re.compile(r"(BV[0-9A-Za-z]{10})")
AV_RE = re.compile(r"/video/av(\d+)", re.I)


class BiliError(Exception):
    pass


def cookie_args():
    """登录过 B 站就带上 cookie，能拿到更高的清晰度/会员内容。"""
    from . import bili_login
    f = bili_login.cookies_file()
    return ["--cookies", str(f)] if f.exists() and f.stat().st_size > 32 else []


def find_ytdlp():
    """找 yt-dlp（程序从启动器起来时 PATH 里不一定有）。"""
    cands = [os.environ.get("YTDLP") or "", shutil.which("yt-dlp") or ""]
    la = os.environ.get("LOCALAPPDATA") or ""
    if la:
        cands.append(os.path.join(la, "Microsoft", "WinGet", "Links", "yt-dlp.exe"))
        import glob
        cands += glob.glob(os.path.join(la, "Microsoft", "WinGet", "Packages", "*yt-dlp*",
                                        "**", "yt-dlp.exe"), recursive=True)
    for c in cands:
        if c and Path(c).is_file():
            return c
    return ""


def _get(url, timeout=20, headers=None):
    req = urllib.request.Request(url, headers=headers or HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def expand_short(url: str) -> str:
    """b23.tv 短链 → 真实地址。"""
    if "b23.tv" not in url:
        return url
    try:
        req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.geturl() or url
    except Exception:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.geturl() or url
        except Exception:
            return url


def match(url: str):
    """从任意 B 站链接里取出 BV 号；不是 B 站链接返回 None。"""
    if not url:
        return None
    if "bilibili.com" not in url and "b23.tv" not in url:
        return None
    full = expand_short(url.strip())
    m = BV_RE.search(full)
    if m:
        return m.group(1)
    m = AV_RE.search(full)
    if m:
        return "av" + m.group(1)
    return None


def fetch_info(bv: str) -> dict:
    """拿标题、作者、时长、封面、简介。"""
    key = "bvid" if bv.lower().startswith("bv") else "aid"
    val = bv if key == "bvid" else bv[2:]
    data = json.loads(_get(f"https://api.bilibili.com/x/web-interface/view?{key}={val}").decode("utf-8"))
    if data.get("code") != 0:
        raise BiliError(f"B 站返回错误：{data.get('message') or data.get('code')}")
    d = data.get("data") or {}
    if not d:
        raise BiliError("这条 B 站视频读不到信息（可能已删除或需要登录）")
    return {
        "bv": d.get("bvid") or bv,
        "title": d.get("title") or "",
        "author": ((d.get("owner") or {}).get("name")) or "",
        "duration": float(d.get("duration") or 0),
        "cover": d.get("pic") or "",
        "desc": d.get("desc") or "",
        "cid": d.get("cid"),
        "published_at": float(d.get("pubdate") or 0) or None,
        "pages": d.get("pages") or [],
    }


def subtitle_text(bv: str, cid) -> str:
    """官方/AI 字幕（需要登录才有，取不到就返回空）。"""
    if not cid:
        return ""
    try:
        u = f"https://api.bilibili.com/x/player/v2?bvid={bv}&cid={cid}"
        d = json.loads(_get(u).decode("utf-8"))
        subs = (((d.get("data") or {}).get("subtitle") or {}).get("subtitles") or [])
        if not subs:
            return ""
        su = subs[0].get("subtitle_url") or ""
        if su.startswith("//"):
            su = "https:" + su
        if not su:
            return ""
        j = json.loads(_get(su).decode("utf-8"))
        body = j.get("body") or []
        return "".join(str(b.get("content") or "") for b in body).strip()
    except Exception:
        return ""


def download_audio(bv: str, dest_dir: Path, log=print) -> Path:
    """下音频（B 站要登录才给全，失败会给出清楚的提示）。"""
    exe = find_ytdlp()
    if not exe:
        raise BiliError("没找到 yt-dlp，装一个再试（winget install yt-dlp）")
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"{bv}.m4a"
    if out.exists() and out.stat().st_size > 1024:
        return out
    cmd = [exe, "-f", "bestaudio", "-x", "--audio-format", "m4a",
           "--no-playlist", *cookie_args(), "-o", str(dest_dir / f"{bv}.%(ext)s"),
           f"https://www.bilibili.com/video/{bv}/"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if not out.exists():
        tail = (r.stderr or r.stdout or "")[-200:]
        raise BiliError(f"音频下载失败：{tail.strip()[:160]}")
    return out


def download_video(bv: str, dest_dir: Path, log=print, max_h=720) -> Path:
    """下视频（≤720p，合并成一个 mp4）：既能转文字，也能抽帧读画面文字。"""
    exe = find_ytdlp()
    if not exe:
        raise BiliError("没找到 yt-dlp，装一个再试（winget install yt-dlp）")
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"{bv}.mp4"
    if out.exists() and out.stat().st_size > 1024:
        return out
    cmd = [exe, "-f", f"bv*[height<={max_h}]+ba/b[height<={max_h}]/b",
           "--merge-output-format", "mp4", "--no-playlist", *cookie_args(),
           "-o", str(dest_dir / f"{bv}.%(ext)s"),
           f"https://www.bilibili.com/video/{bv}/"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if not out.exists():
        tail = (r.stderr or r.stdout or "")[-200:]
        raise BiliError(f"视频下载失败：{tail.strip()[:160]}")
    return out


def download_cover(url: str, dest: Path) -> Path:
    if not url:
        raise BiliError("这条没有封面")
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = _get(url, timeout=20)
    if len(body) < 512:
        raise BiliError("封面太小，可能是占位图")
    dest.write_bytes(body)
    return dest