"""没有旁白的视频：抽帧 + 识别画面文字。

很多 AI 教程视频只有字幕/幻灯片、没有讲解人声，转文字会得到空稿，
以前就直接跳过。这里按固定间隔抽帧、去掉几乎一样的画面，再走本地 OCR，
把画面上的字读出来喂给 AI，这样这类视频也能整理成笔记。

抽帧优先用 ffmpeg（一次解码整条视频，比 cv2 逐次 seek 快很多），
没装 ffmpeg 时退回 cv2。
"""
import glob
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import ocr

EVERY_SEC = 5.0        # 多久抽一帧（视频很长时自动拉大间隔，保证总帧数不超上限）
MAX_FRAMES = 24        # 最多读多少帧（按整条视频均匀铺开，不再只截开头）
MAX_W = 1280            # 识别前把图缩小，字幕照样认得出来
MIN_TEXT = 40          # 画面文字少于这个字数就当没内容

_FF_CACHE = []
_LAST_ERR = []


def find_ffmpeg():
    """找到 ffmpeg 的可执行文件（程序从启动器起来时 PATH 里不一定有）。"""
    if _FF_CACHE:
        return _FF_CACHE[0]
    cands = [os.environ.get("FFMPEG_BINARY") or "", shutil.which("ffmpeg") or ""]
    la = os.environ.get("LOCALAPPDATA") or ""
    if la:
        cands += glob.glob(os.path.join(la, "Microsoft", "WinGet", "Packages", "*FFmpeg*",
                                        "**", "ffmpeg.exe"), recursive=True)
        cands += glob.glob(os.path.join(la, "Microsoft", "WinGet", "Links", "ffmpeg.exe"))
    cands.append("C:/ffmpeg/bin/ffmpeg.exe")
    for c in cands:
        if c and Path(c).is_file():
            _FF_CACHE.append(c)
            return c
    _FF_CACHE.append("")
    return ""


def _same(a, b) -> bool:
    """两张画面是不是同一张幻灯片（只看灰度差）。"""
    try:
        import cv2
        import numpy as np
        ga = cv2.cvtColor(cv2.resize(a, (160, 90)), cv2.COLOR_BGR2GRAY)
        gb = cv2.cvtColor(cv2.resize(b, (160, 90)), cv2.COLOR_BGR2GRAY)
        return float(np.mean(cv2.absdiff(ga, gb))) < 3.0
    except Exception:
        return False


def _has_picture(ff, path) -> bool:
    """文件里到底有没有画面流（只有音频的 mp4 用 cv2 打开会卡住）。"""
    try:
        r = subprocess.run([ff, "-hide_banner", "-i", str(path)], capture_output=True, timeout=10)
        return b"Video:" in (r.stderr or b"")
    except Exception:
        return True


def _duration(path):
    try:
        import cv2
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        cap.release()
        return (total / fps) if (fps and total) else 0.0
    except Exception:
        return 0.0


def _grab_ffmpeg(path, out_dir, n, dur):
    """用 ffmpeg 一次解码抽出 n 张图（整条视频均匀分布）。"""
    ff = find_ffmpeg()
    if not ff:
        _LAST_ERR.append("没找到 ffmpeg")
        return []
    fps = (n / dur) if dur > 0 else (1.0 / EVERY_SEC)
    out = out_dir / "f%03d.png"
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-i", str(path),
           "-vf", "fps=%f,scale=%d:-2" % (fps, MAX_W),
           "-frames:v", str(n), "-y", str(out)]
    try:
        r = subprocess.run(cmd, check=False, capture_output=True, timeout=180)
        if r.returncode != 0:
            _LAST_ERR.append((r.stderr or b"")[-200:].decode("utf-8", "replace"))
    except Exception as e:
        _LAST_ERR.append(str(e)[:200])
        return []
    return sorted(out_dir.glob("f*.png"))


def _grab_cv2(path, n, dur):
    import cv2
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return []
    out_dir = Path(tempfile.mkdtemp(prefix="frames_"))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    shots = []
    try:
        if total > n:      # 顺序解码一遍、按间隔取帧：比反复 seek 快十几倍
            step = max(1, total // n)
            idx = 0
            while idx < total and len(shots) < n:
                ok = cap.grab()
                if not ok:
                    break
                if idx % step == 0:
                    ok, img = cap.retrieve()
                    if ok and img is not None:
                        if img.shape[1] > MAX_W:
                            h, w0 = img.shape[:2]
                            img = cv2.resize(img, (MAX_W, round(h * MAX_W / w0)))
                        p2 = out_dir / f"f{len(shots)+1:03d}.png"
                        cv2.imwrite(str(p2), img)
                        shots.append(p2)
                idx += 1
        else:              # 帧数太少或读不到，退回按时间取
            step_t = max(EVERY_SEC, (dur / n) if dur > 0 else EVERY_SEC)
            t = 2.0
            while (dur <= 0 or t < dur) and len(shots) < n:
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                ok, img = cap.read()
                if not ok:
                    break
                t += step_t
                if img is None:
                    continue
                if img.shape[1] > MAX_W:
                    h, w0 = img.shape[:2]
                    img = cv2.resize(img, (MAX_W, round(h * MAX_W / w0)))
                p2 = out_dir / f"f{len(shots)+1:03d}.png"
                cv2.imwrite(str(p2), img)
                shots.append(p2)
    finally:
        cap.release()
    return shots


def read_frames(path, every_sec=EVERY_SEC, max_frames=MAX_FRAMES, log=None):
    """返回画面上的文字（按出现顺序，重复画面只读一次）。"""
    def say(msg):
        if log:
            log(msg)

    path = str(path)
    if not Path(path).exists():
        return ""
    dur = _duration(path)
    tmp = Path(tempfile.mkdtemp(prefix="frames_"))
    shots = _grab_ffmpeg(path, tmp, max_frames, dur)
    if not shots:
        ff = find_ffmpeg()
        if ff and not _has_picture(ff, path):
            say("这个文件里只有音频、没有画面，读画面文字跳过")
            return ""
        err = (_LAST_ERR[-1] if _LAST_ERR else "").strip().replace(chr(10), " ")[:150]
        say("ffmpeg 抽帧没成功（%s ｜ %s），改用 opencv" % (ff or "没找到", err))
        shots = _grab_cv2(path, max_frames, dur)
    if not shots:
        return ""
    say(f"抽到 {len(shots)} 帧，开始识别画面文字")

    texts = []
    for p in shots:
        try:
            text = (ocr.recognize(p) or "").strip()
        except Exception:
            text = ""
        if len(text) >= 4 and not (texts and text in texts[-1]):
            texts.append(text)
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass

    joined = "\n".join(texts)
    say(f"画面文字：读了 {len(texts)} 屏，共 {len(joined)} 字")
    return joined
