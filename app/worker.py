"""后台处理线程：一条一条地 读信息 → 下载 → 转文字 → AI 提炼 → 写笔记。

浏览器只能在同一个线程里操作，所以所有抖音相关的事都放在这个线程里排队做。
"""
import collections
import concurrent.futures as cf
import json
import re
import queue
import threading
import time
import traceback
from pathlib import Path

from . import classify, config, db, douyin, llm, notes, ocr, progress, transcribe

MEDIA_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".flv", ".avi", ".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}

# 浏览器被关掉时会报这些
DEAD_MARKS = ("context or browser has been closed", "target page, context",
              "browser has been closed", "target closed")


def media_seconds(path):
    """这条视频/音频有多长（秒）；取不到返回 0。"""
    try:
        import cv2
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        cap.release()
        if fps and total:
            return total / fps
    except Exception:
        pass
    try:
        from . import transcribe as _t
        import wave
        with wave.open(str(path)) as w:
            return w.getnframes() / (w.getframerate() or 1)
    except Exception:
        return 0.0


def has_video_stream(path):
    """这个文件里有没有画面（抖音有些源只给音频）。

    用 ffmpeg 看流信息：之前用 cv2 打开「只有音频的 mp4」会卡住好几分钟。
    """
    try:
        import subprocess
        from . import frames
        ff = frames.find_ffmpeg()
        if not ff:
            return True
        r = subprocess.run([ff, "-hide_banner", "-i", str(path)],
                           capture_output=True, timeout=10)
        return b"Video:" in (r.stderr or b"")
    except Exception:
        return True     # 判断不了就别拦，交给后面的流程


def _browser_dead(msg):
    m = (msg or "").lower()
    return any(k in m for k in DEAD_MARKS)


class Worker:
    def __init__(self):
        self.cmds = queue.Queue()
        self.logs = collections.deque(maxlen=300)
        self.state = {"busy": False, "task": "", "item_id": None, "stage": "", "done": 0, "total": 0}
        self._stop = threading.Event()
        self.browser = None
        self.retry_later = []          # [(什么时候重试, id)]
        self.paused = False
        self._covers_done = False
        self._auto_sync_day = ""
        self._last_sync = 0
        self.prog = progress.Progress()
        # AI 提炼并行：浏览器/转文字仍由本线程独占，只有调模型的那一步放到线程池里
        try:
            self.parallel = max(1, min(8, int(config.load().get("parallel", 4))))
        except Exception:
            self.parallel = 4
        self._ai_pool = cf.ThreadPoolExecutor(max_workers=8, thread_name_prefix="ai") if self.parallel > 1 else None
        self._ai_futs = set()
        self._ai_lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True, name="worker")
        self.thread.start()

    # ------------------------------------------------------------ 启动自检
    def _selfcheck(self):
        """启动时快速体检：浏览器、临时目录、抖音连通性。结果直接写进界面日志。"""
        try:
            from .server import find_browser_exe
            exe, label = find_browser_exe()
            self.log(f"环境检查 · 浏览器：{label}（{exe}）" if exe
                     else "环境检查 · 浏览器：没找到 Chrome / Edge，同步抖音会失败")
        except Exception:
            pass
        try:
            import os
            import tempfile
            from pathlib import Path
            cur = os.environ.get("TEMP") or tempfile.gettempdir()
            Path(cur).mkdir(parents=True, exist_ok=True)
            probe = Path(cur) / f".ok{os.getpid()}"
            probe.write_bytes(b"x")
            probe.unlink()
            self.log(f"环境检查 · 临时目录：可写（{cur}）")
        except Exception as e:
            self.log(f"环境检查 · 临时目录有问题：{e}。同步抖音可能失败，请联系管理员")
        try:
            import urllib.error
            import urllib.request
            req = urllib.request.Request("https://www.douyin.com/",
                                         headers={"User-Agent": "Mozilla/5.0"})
            try:
                urllib.request.urlopen(req, timeout=8).close()
            except urllib.error.HTTPError as e:
                # 403/404 之类说明网络是通的，只是不接受这个请求
                if e.code >= 500:
                    raise
            self.log("环境检查 · 抖音：可以访问")
        except Exception as e:
            self.log(f"环境检查 · 抖音访问异常：{str(e)[:120]}（如果开着网络代理，先关掉代理再试）")

    # ------------------------------------------------------------ 对外接口
    def log(self, msg):
        self.logs.append({"t": time.time(), "msg": str(msg)})
        print(time.strftime("%H:%M:%S"), msg, flush=True)

    def submit(self, cmd, **kw):
        self._stop.clear()
        self.cmds.put((cmd, kw))

    def stop(self):
        self._stop.set()
        self.log("收到停止指令，处理完当前这一步就停。")

    def stopping(self):
        return self._stop.is_set()

    def _auto_sync_due(self):
        try:
            s = config.load()
            if not s.get("auto_sync", True) or self.paused or self.stopping():
                return False
            every = max(5, int(s.get("auto_sync_min", 10) or 10)) * 60
            return (time.time() - (self._last_sync or 0)) >= every
        except Exception:
            return False

    def _maybe_auto_sync(self):
        """全自动：定时同步收藏 + 有排队就自动开跑（用户只负责删）。"""
        try:
            s = config.load()
            if self.paused or self.stopping():
                return
            now = time.time()
            # 1) 定时自动同步（默认每 10 分钟）
            if s.get("auto_sync", True):
                every = max(5, int(s.get("auto_sync_min", 10) or 10)) * 60
                if now - (self._last_sync or 0) >= every:
                    self._last_sync = now
                    self.log(f"自动同步收藏（每 {every // 60} 分钟一次）")
                    self.cmds.put(("sync", {"kind": "collection", "limit": 0,
                                            "then_process": bool(s.get("auto_process", True))}))
                    return
            # 2) 每天固定时间也跑一次（可选）
            at = (s.get("auto_sync_at") or "").strip()
            if at and time.strftime("%H:%M") == at and self._auto_sync_day != time.strftime("%Y-%m-%d"):
                self._auto_sync_day = time.strftime("%Y-%m-%d")
                self.log(f"到点了（{at}），自动同步收藏")
                self.cmds.put(("sync", {"kind": "collection", "limit": 0, "then_process": True}))
                return
            # 3) 兜底：队列里有活就开跑（用户点了暂停就等着）
            if s.get("auto_process", True) and db.stats()["by_status"].get("queued", 0) > 0:
                self.cmds.put(("process", {}))
        except Exception as e:
            self.log(f"自动任务检查失败：{str(e)[:60]}")

    # ------------------------------------------------------------ 主循环
    def _run(self):
        self._selfcheck()
        self._maybe_auto_sync()      # 一启动就先同步一次，不用手动点
        while True:
            try:
                cmd, kw = self.cmds.get(timeout=60)
            except queue.Empty:
                self._maybe_auto_sync()
                continue
            self.state.update(busy=True, task=cmd, stage="", item_id=None)
            try:
                if cmd == "reclassify":
                    self._reclassify(limit=kw.get("limit", 100000), only=kw.get("only"))
                elif cmd == "bili_login":
                    from . import bili_login
                    bili_login.login(log=self.log)
                elif cmd == "retry_fetch_failed":
                    n = 0
                    rows = db.conn().execute(
                        "SELECT id FROM items WHERE status='failed' AND COALESCE(deleted_at,0)=0 "
                        "AND (reason LIKE '%通用页%' OR reason LIKE '%抓取失败%' OR "
                        "reason LIKE '%播放地址%' OR reason LIKE '%没有画面%')").fetchall()
                    for r in rows:
                        db.update(r["id"], status="queued", transcript=None, note=None,
                                  images=None, md_path=None, reason=None, attempts=0, auto_skip=2)
                        n += 1
                    self.log(f"把 {n} 条抓取失败的重新排队（文字稿已清空，会重新抓）")
                elif cmd == "fix_covers":
                    self._fix_covers()
                elif cmd == "dy_browser":
                    try:
                        self._browser()
                        self.log("抖音浏览器已就绪（评论/点赞要用它）")
                    except Exception as e:
                        self.log(f"抖音浏览器打不开：{str(e)[:80]}")
                elif cmd == "process":
                    self._process_all()
                elif cmd == "login":
                    self._browser().ensure_login(should_stop=self.stopping)
                elif cmd == "sync":
                    self._sync(kw.get("kind", "collection"), kw.get("limit", 50), kw.get("then_process", True))
                elif cmd == "xhs_login":
                    qr = config.DATA / "tmp" / "xhs_qr.png"
                    try:
                        qr.parent.mkdir(parents=True, exist_ok=True)
                        qr.unlink(missing_ok=True)
                    except Exception:
                        pass
                    xb = self._xhs(visible=False)
                    ok = xb.ensure_login(should_stop=self.stopping, qr_path=qr)
                    xb.hide()      # 登录窗口用完就收起来，别一直摆在桌面上
                    if ok and kw.get("sync"):
                        self._sync_xhs(kw.get("limit", 50), True)
                elif cmd == "xhs_sync":
                    self._sync_xhs(kw.get("limit", 50), kw.get("then_process", True))
                elif cmd == "check_login":
                    try:
                        b = self._browser()
                        self.log("抖音：" + ("已登录" if b.logged_in() else "未登录"))
                    except Exception as e:
                        self.log(f"抖音状态检查失败：{str(e)[:60]}")
                    try:
                        xb = self._xhs()
                        self.log("小红书：" + ("已登录" if xb.logged_in() else "未登录"))
                    except Exception as e:
                        self.log(f"小红书状态检查失败：{str(e)[:60]}")
                elif cmd == "cache_all":
                    self._cache_all()
            except douyin.DouyinError as e:
                self.log(f"⚠ {e}")
            except Exception as e:
                self.log(f"⚠ 出错了：{e}")
                traceback.print_exc()
            finally:
                if self.cmds.empty():
                    from . import cache as _c
                    if _c.all_state()["on"] and _c.all_state().get("left"):
                        self.cmds.put(("cache_all", {}))   # 缓存没跑完，接着来
                    else:
                        self._close_browser()
                        self.state.update(busy=False, task="", stage="", item_id=None)

    def _browser(self):
        if self.browser is None:
            self.browser = douyin.Browser(config.load().get("browser", "auto"), log=self.log)
        self.browser.start()
        return self.browser

    def _close_browser(self):
        if self.browser:
            self.browser.close()
            self.browser = None
        if getattr(self, "xhs_browser", None):
            self.xhs_browser.close()
            self.xhs_browser = None

    def _xhs(self, visible=None):
        """小红书用的浏览器（独立登录态，默认后台跑；登录时切到可见）。"""
        if getattr(self, "xhs_browser", None) is None:
            from . import xhs
            self.xhs_browser = xhs.Browser(log=self.log)
        self.xhs_browser.start(visible=visible)
        return self.xhs_browser

    # ------------------------------------------------------------ 收藏夹同步
    def _sync(self, kind, limit, then_process):
        name = "喜欢" if kind == "like" else "收藏"
        self.log(f"开始读取抖音「{name}」列表（{'最多 ' + str(limit) + ' 条' if limit else '全部读完'}）……")
        added, requeued, notes_n = [0], [0], [0]

        def on_item(d):
            item_id, new = db.add("favorite", aweme_id=d["aweme_id"], url=d["url"], title=d["title"],
                                  author=d["author"], duration=d["duration"], cover=d["cover"],
                                  published_at=d.get("published_at"), collected_at=d.get("collected_at"))
            if new:
                added[0] += 1
                if d.get("is_note"):
                    db.update(item_id, media_type="note")
                    notes_n[0] += 1
            else:
                old = db.get(item_id)
                # 老数据没有时间的，顺手补上（同步一次就把全部收藏的时间补齐）
                if old:
                    patch = {}
                    if d.get("published_at") and not old.get("published_at"):
                        patch["published_at"] = d["published_at"]
                    if d.get("collected_at") and not old.get("collected_at"):
                        patch["collected_at"] = d["collected_at"]
                    # 封面以列表里的为准：详情页有时会返回「电子营业执照」占位图，同步一次就修回来
                    if d.get("cover") and d["cover"] != old.get("cover"):
                        patch["cover"] = d["cover"]
                    if patch:
                        db.update(item_id, **patch)
                retry_note = (old and old["status"] == "skipped" and "图文" in (old.get("reason") or ""))
                if old and (old["status"] == "failed" or retry_note):  # 之前失败的 / 以前跳过的图文，这次重新处理
                    db.update(item_id, status="queued", attempts=0, reason=None,
                              media_type="note" if (d.get("is_note") or retry_note) else old.get("media_type"))
                    requeued[0] += 1

        n = self._browser().sync_list(kind, limit, on_item, should_stop=self.stopping)
        msg = f"读到 {n} 条，其中新增 {added[0]} 条" + (f"（含图文 {notes_n[0]} 条）" if notes_n[0] else "")
        if requeued[0]:
            msg += f"，之前失败的 {requeued[0]} 条重新排队"
        self.log(msg + "（已完成或已跳过的不会重复处理）。")
        if then_process and not self.stopping():
            self._process_all()

    # ------------------------------------------------------------ 批量处理
    def _process_all(self):
        self.retry_later = []
        try:    # 每批开始读一次，设置页改了并发数不用重启
            self.parallel = max(1, min(8, int(config.load().get("parallel", 4))))
        except Exception:
            pass
        # 不再按分类自动跳过：用户要求所有收藏都拆解（以前「生活与娱乐」会被整类跳过，
        # 结果把误分类的 AI 干货也一起跳掉了）
        self.state.update(done=0, total=db.stats()["by_status"].get("queued", 0), t0=time.time())
        self.state["retry_at"] = {str(i): t for t, i in self.retry_later}
        if not self.state["total"]:
            self.log("队列里没有待处理的视频。")
            return
        self.log(f"开始处理，共 {self.state['total']} 条。")
        while not self.stopping():
            while self.paused and not self.stopping():
                time.sleep(0.5)
            if self.stopping():
                break
            # 到点的重试放回队列
            if self.retry_later:
                now = time.time()
                due = [i for t, i in self.retry_later if t <= now]
                if due:
                    self.retry_later = [(t, i) for t, i in self.retry_later if t > now]
                    for i in due:
                        db.update(i, status="queued")
                        self.state["total"] += 1
                    continue
            # 同时在跑的 AI 别堆太多，留点余量让主流程不停
            if self._ai_pool:
                with self._ai_lock:
                    busy = len(self._ai_futs)
                if busy >= self.parallel * 2:
                    cf.wait(list(self._ai_futs), return_when=cf.FIRST_COMPLETED)
            it = db.next_queued()
            if it is None:
                if self._ai_pool:
                    with self._ai_lock:
                        pending = list(self._ai_futs)
                    if pending:
                        cf.wait(pending, return_when=cf.FIRST_COMPLETED)
                        continue
                if self.retry_later:
                    wait = max(1, min(30, self.retry_later[0][0] - time.time()))
                    time.sleep(wait)
                    continue
                # 队列空了，顺手把还挂在远端的封面抓回本地
                if not self._covers_done:
                    self._covers_done = True
                    try:
                        left = db.count_remote_covers()
                    except Exception:
                        left = 0
                    if left:
                        self._fix_covers(limit=min(200, left))
                        continue
                break
            self.state.update(item_id=it["id"])
            self._process_one(it)
            if not self._ai_pool:
                self.state["done"] += 1
            # 到点自动同步：跑着批次也照同步，新收藏不会积压
            if self._auto_sync_due():
                self._last_sync = time.time()
                self.log("到点自动同步收藏（正在跑的这批稍后继续）")
                self.cmds.put(("sync", {"kind": "collection", "limit": 0,
                                        "then_process": bool(config.load().get("auto_process", True))}))
            # 有新的登录/同步请求就先把队列让出来，处理完再继续这批
            if not self.cmds.empty():
                self.log("有新的请求，先让路（稍后继续处理队列）")
                self.cmds.put(("process", {}))
                break
            # 队列在跑的时候顺手把「全部缓存」的任务也推进一步，两边不耽误
            from . import cache as _cache
            if _cache.all_state()["on"]:
                self._cache_step()
        if self._ai_pool:
            with self._ai_lock:
                pending = list(self._ai_futs)
            if pending:
                cf.wait(pending)
        self.log("这一批处理完了。" if not self.stopping() else "已停止。")
        self._maybe_auto_sync()

    # ---------------------------------------------------------- 全部视频缓存
    def _cache_step(self):
        """缓存一条还没下载过的视频。返回 True 表示成功（或本来就有）。"""
        from . import cache
        it = cache.all_next()
        if it is None:
            return False
        aid = str(it.get("aweme_id") or "")
        dest = config.MEDIA_DIR / f"{aid}.mp4"
        if dest.is_file():
            cache.all_step(True)
            return True
        ok = False
        try:
            cache.all_current(it.get("title") or aid)
            if (it.get("platform") or "douyin") == "xhs":
                # 用后台已经开着的浏览器读笔记，别另起 Playwright 实例（同线程会冲突）
                xb = self._xhs()
                info = xb.fetch_note(aid, url=it.get("url")) or {}
                vu = info.get("video_url") or ""
                if isinstance(vu, list):
                    vu = vu[0] if vu else ""
                urls = [vu] if vu else []
                referer = "https://www.xiaohongshu.com/"
            else:
                b = self._browser()
                d = b.fetch_detail(aid) or {}
                urls = d.get("play_urls") or []
                if urls:
                    db.update(it["id"], play_url=urls[0], play_url_ts=time.time())
                referer = "https://www.douyin.com/"
            if not urls:
                if (it.get("platform") or "douyin") == "xhs":
                    db.update(it["id"], media_type="note")
                    ok = True                       # 小红书图文没有视频，不算失败
                else:
                    raise douyin.DouyinError("取不到播放地址")
            else:
                cache.download(urls, dest, item_id=it["id"], title=it.get("title") or "",
                               referer=referer)
                ok = True
        except Exception as e:
            self.log(f"[{it['id']}] 缓存失败：{str(e)[:90]}")
        cache.all_step(ok)
        st = cache.all_state()
        if st["done"] and st["done"] % 10 == 0:
            self.log(f"全部缓存进度：{st['done']}/{st['total']}（失败 {st['failed']}）")
        return True

    def _cache_all(self):
        from . import cache
        self.log(f"开始缓存全部视频，共 {cache.all_state()['total']} 条还没缓存")
        n = 0
        while not self.stopping():
            if cache.all_state()["on"] is False:
                break
            if not self.cmds.empty():
                self.log("有新的同步/登录请求，缓存先让路，处理完继续")
                break
            if not self._cache_step():
                break
            n += 1
            # 每缓存 3 条，顺手处理一条待拆解的，别让学习队列停着
            if n % 3 == 0:
                it = db.next_queued()
                if it is not None:
                    self.state.update(item_id=it["id"])
                    self._process_one(it)
        st = cache.all_state()
        cache.all_finish()
        self.log(f"全部缓存结束：成功 {st['done']} 条，失败 {st['failed']} 条")

    def _stage(self, it, status, msg):
        db.update(it["id"], status=status, reason=None)
        self.prog.stage(status)
        self.state["stage"] = msg
        self.log(f"[{it['id']}] {msg}")

    def _process_one(self, it):
        s = config.load()
        self.prog.begin(it, bool(it.get("transcript")), transcribe.pick_engine(s.get("asr_engine", "auto")))
        try:
            self._process_one_inner(it, s)
        finally:
            cur = db.get(it["id"])
            # 并行模式下这条刚交给 AI 线程池，等它跑完才算结束
            if not cur or cur["status"] != "extracting":
                self.prog.end(ok=bool(cur and cur["status"] == "done"))

    def _process_one_inner(self, it, s):
        label = (it.get("title") or it.get("url") or "")[:30]
        try:
            # 1-2. 拿到视频文件（已经有文字稿的跳过这一步，比如重新提炼）
            if not it.get("transcript"):
                media = self._get_media(it, s)
                if media is None:
                    return
                if isinstance(media, dict) and "note" in media:  # 图文：下载图片 + 识别图片文字
                    if not self._process_note(it, media["note"]):
                        return
                    it = db.get(it["id"])
                    media = None
                elif isinstance(media, dict):  # 拿到了视频自带字幕，不用下载和转写
                    db.update(it["id"], transcript=media["text"], segments=media["segments"] or None)
                    it = db.get(it["id"])
                    media = None
            if not it.get("transcript"):
                self._stage(it, "transcribing", f"转文字：{label}")
                tr = None
                try:
                    size = s.get("whisper_model", "small")
                    if s.get("asr_auto", True):
                        # 短视频用 medium（更准），长视频仍用 small（更快）
                        sec = media_seconds(media) if not isinstance(media, dict) else 0
                        if 0 < sec <= 300:
                            size = "medium"
                            self.log(f"[{it['id']}] 短视频（{int(sec)} 秒），用 medium 模型转写")
                    tr = transcribe.transcribe(
                        media, engine=s.get("asr_engine", "auto"), mlx_model=s.get("mlx_model"),
                        size=size, use_mirror=s.get("use_hf_mirror", False),
                        max_minutes=s.get("max_minutes", 15), log=self.log, should_stop=self.stopping,
                        on_progress=self.prog.set_frac, hint=(it.get("title") or "")[:120])
                except transcribe.NoSpeech as e:
                    # 没有旁白不等于没内容：很多教程视频只有画面和字幕，
                    # 抽帧把画面上的字读出来照样能整理成笔记。
                    ftext = ""
                    if media and not isinstance(media, dict):
                        self._stage(it, "transcribing", f"读画面文字：{label}")
                        try:
                            from . import frames as _frames
                            ftext = _frames.read_frames(media, log=self.log) or ""
                        except Exception as ex:
                            self.log(f"[{it['id']}] 读画面文字失败：{str(ex)[:80]}")
                    self._cleanup(it, media, s)
                    if len(ftext.strip()) >= 40:
                        db.update(it["id"], transcript="【画面文字】" + chr(10) + ftext, segments=None)
                        self.log(f"[{it['id']}] 没有人声，改用画面文字（{len(ftext)} 字），继续提炼")
                        it = db.get(it["id"])
                    else:
                        # 没旁白 + 画面也没字：用标题/话题/简介凑一份文字稿，照样出笔记
                        head = " ".join(x for x in [(it.get("title") or ""),
                                                    (it.get("author") or "")] if x)
                        bd = (it.get("bili_desc") or "").strip()
                        extra = ("【视频简介】" + chr(10) + bd + chr(10) * 2) if bd else ""
                        db.update(it["id"], transcript=(extra + head + chr(10) + chr(10) +
                                  "（这条视频没有旁白，画面里也没有可识别的文字，只能按标题和简介整理）"))
                        self.log(f"[{it['id']}] 没有旁白也没有画面文字，用标题硬整理一条")
                        it = db.get(it["id"])
                # 先读画面文字（读之前不能删视频文件），再清理临时文件
                ftext = ""
                if tr is not None and media and not isinstance(media, dict) and has_video_stream(media):
                    try:
                        from . import frames as _frames
                        ftext = (_frames.read_frames(media, log=self.log) or "").strip()
                    except Exception as ex:
                        self.log(f"[{it['id']}] 读画面文字失败：{str(ex)[:60]}")
                self._cleanup(it, media, s)
                if self.stopping():
                    db.update(it["id"], status="queued")
                    return
                if tr is not None:
                    text = tr["text"]
                    if len(ftext) >= 40:
                        text = text + chr(10) * 2 + "【画面文字】" + chr(10) + ftext
                    bd = (it.get("bili_desc") or "").strip()
                    if bd:
                        text = "【视频简介】" + chr(10) + bd + chr(10) * 2 + text
                    db.update(it["id"], transcript=text, segments=tr["segments"],
                              duration=it.get("duration") or tr["duration"])
                it = db.get(it["id"])

            # 3. AI 提炼：并行模式下丢进线程池，本线程接着准备下一条
            if self._ai_pool:
                self._submit_ai(it, s)
            else:
                self._ai_extract(it, s)

        except douyin.NotLoggedIn as e:
            self._fail(it, f"{e}。请点「登录抖音」后重试", retry=False)
        except (douyin.DouyinError, llm.LLMError) as e:
            self._fail(it, str(e), retry=getattr(e, "retry", isinstance(e, douyin.DouyinError)))
        except Exception as e:
            traceback.print_exc()
            msg = f"意外错误：{e}"
            if _browser_dead(str(e)):
                # 浏览器被关掉/崩了：换一个新的，这一条也值得再试一次
                self._reset_browser()
                msg += "（浏览器已自动重开）"
            self._fail(it, msg, retry=True)

    def _submit_ai(self, it, s):
        """把这条的文字稿交给线程池提炼，主流程立刻继续下一条。"""
        db.update(it["id"], status="extracting", reason=None)
        fut = self._ai_pool.submit(self._ai_extract, it, s)
        with self._ai_lock:
            self._ai_futs.add(fut)
        fut.add_done_callback(self._ai_done)

    def _ai_done(self, fut):
        with self._ai_lock:
            self._ai_futs.discard(fut)
        self.state["done"] += 1

    def _ai_extract(self, it, s):
        """只调模型 + 写笔记，不碰浏览器，可以多条同时跑。"""
        iid = it["id"]
        try:
            if not (s.get("api_key") or "").strip():
                db.update(iid, status="need_key", reason="已转成文字，填好 AI Key 后点「重新提炼」生成笔记")
                return
            note, used = llm.extract(s, it.get("title"), it.get("author"), it["transcript"],
                                     kind="note" if it.get("media_type") == "note" else "video")
            config.add_tokens(used)
            if note.get("skip"):
                # 不再丢弃：做成一条「内容很少」的笔记，用户自己决定删不删
                reason = note.get("skip_reason") or "没有实质内容"
                note = {"skip": False, "relevant": True,
                        "title": (it.get("title") or "（无标题）")[:40],
                        "category": "其他", "tags": [], "difficulty": "",
                        "summary": f"这条没有可学习的内容（{reason}）。觉得没用可以直接删掉。",
                        "points": [], "steps": [], "tools": [], "quiz": []}
                self.log(f"[{iid}] 内容很少，但仍生成了一条笔记")
            # 不再有「主题无关」：内容是什么就分到什么类，哪个都不合适 → 无法分类
            note["relevant"] = True
            it = self._localize_cover(it)
            it["note"] = note
            path = notes.write(it)
            c0, sub0 = classify.normalize_note_category(note.get("category"))
            db.update(iid, status="done", note=note, category=c0, subcategory=sub0 or None,
                      md_path=path, reason=None)
            self.log(f"[{iid}] ✓ 完成：{note['title']}")
        except (llm.LLMError, Exception) as e:
            msg = str(e)
            db.update(iid, status="failed", reason=msg, attempts=(it.get("attempts") or 0) + 1)
            self.log(f"[{iid}] ✗ 失败：{msg[:80]}")
            if "余额不足" in msg or "402" in msg:
                self.log("⚠ AI 账户余额不足，先停下队列（充值或换 Key 后点「开始处理」继续）")
                self._stop.set()

    def _reset_browser(self):
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        self.browser = None

    def _fail(self, it, msg, retry):
        cur = db.get(it["id"]) or it
        attempts = (cur.get("attempts") or 0) + 1
        # AI 没余额 / 无权限：整批停下，别把剩下几百条都跑成失败
        if ("余额不足" in msg or "402" in msg) and "无权限" in msg:
            db.update(it["id"], status="failed", reason=msg, attempts=attempts)
            self.log(f"[{it['id']}] ✗ 失败：{msg}")
            self.log("⚠ AI 账户余额不足，先停下队列（充值或换 Key 后点「开始处理」继续）")
            self._stop.set()
            return
        limit = 3 if _browser_dead(msg) else 2
        if retry and attempts < limit:
            # 暂时性错误：先冷却 60 秒再回队列，避免网络抖动时反复失败
            db.update(it["id"], status="retry_wait", attempts=attempts,
                      reason=f"第 {attempts} 次失败，60 秒后自动重试：{msg[:60]}")
            self.retry_later.append((time.time() + 60, it["id"]))
            self.log(f"[{it['id']}] 暂时性失败（第 {attempts}/{limit} 次），60 秒后自动重试")
            return
        if attempts >= 3 and (it.get("platform") or "") and "已删除" not in msg and "找不到" not in msg:
            # 连续失败到上限：自动收进回收站，别一直堆在「失败」里
            db.update(it["id"], status="failed", reason=msg, attempts=attempts)
            db.trash(it["id"])
            self.log(f"[{it['id']}] 连续 {attempts} 次失败，已自动放进回收站")
            return
        db.update(it["id"], status="failed", reason=msg, attempts=attempts)
        self.log(f"[{it['id']}] ✗ 失败：{msg}")

    def _reclassify(self, limit=100000, only=None):
        """只修「其他 / 无法分类」这类没分好的：用**完整文字稿**让模型重新归一次。

        之前用标题+摘要两百字去分，信息太少、来回翻烧饼；这次给全文。
        已经明确分好的分类一律不动。
        """
        weak = {"无法分类", "其他", "未分类", "", None}
        rows = db.conn().execute(
            "SELECT id,title,category,note_json,transcript FROM items "
            "WHERE status='done' AND COALESCE(deleted_at,0)=0 ORDER BY id LIMIT ?", (limit,)).fetchall()
        cats = config.load().get("categories") or []
        todo = [r for r in rows if (r["category"] or "") in weak]
        self.log(f"分类补全：全库 {len(rows)} 条，其中 {len(todo)} 条还没分好（其余不动）")
        changed = kept = 0
        for r in todo:
            if self.stopping():
                break
            try:
                note = json.loads(r["note_json"] or "{}")
            except Exception:
                note = {}
            text = " / ".join(x for x in [
                (r["title"] or "")[:80],
                (note.get("summary") or "")[:200],
                "；".join((note.get("points") or [])[:4])[:200],
                (r["transcript"] or "")[:1800],
            ] if x)
            if len(text.strip()) < 20:
                kept += 1
                continue
            time.sleep(0.4)
            try:
                new_cat = llm.classify_category(text, cats)
            except Exception as e:
                msg = str(e)
                if "429" in msg or "频繁" in msg:
                    self.log("分类请求被限速，等 30 秒再继续")
                    time.sleep(30)
                    try:
                        new_cat = llm.classify_category(text, cats)
                    except Exception:
                        new_cat = None
                else:
                    new_cat = None
            if not new_cat or new_cat == (r["category"] or ""):
                kept += 1
                continue
            old_cat = r["category"] or "未分类"
            db.update(r["id"], category=new_cat, subcategory=None)
            try:
                cur = db.get(r["id"])
                if cur and cur.get("note"):
                    cur["note"]["category"] = new_cat
                    db.update(r["id"], note=cur["note"], md_path=notes.write(cur))
            except Exception as ex:
                self.log(f"[{r['id']}] 重新归档失败：{str(ex)[:50]}")
            self.log(f"[{r['id']}] {old_cat} → {new_cat}｜{(r['title'] or '')[:26]}")
            changed += 1
            if (changed + kept) % 20 == 0:
                self.log(f"分类补全进度：改 {changed} / 留 {kept}")
        self.log(f"分类补全完成：纠正 {changed} 条，保持 {kept} 条")

    def _fix_covers(self, limit=300):
        """把还挂在远端的封面抓一份到本地（老的图床签名过期后会 403）。

        小红书能重新读一次笔记拿新封面；抖音的图床地址随签名一起过期，
        重新解析代价太大，取不到就留着占位图。
        """
        rows = db.conn().execute(
            "SELECT id,aweme_id,url,cover,platform FROM items "
            "WHERE cover LIKE 'http%' AND COALESCE(deleted_at,0)=0 LIMIT ?", (limit,)).fetchall()
        self.log(f"开始补封面：还有 {len(rows)} 条挂在远端")
        ok = fresh = fail = 0
        for r in rows:
            if self.stopping():
                break
            it = dict(r)
            before = it.get("cover") or ""
            self._localize_cover(it)
            if (it.get("cover") or "") != before:
                ok += 1
            elif (it.get("platform") or "") == "xhs":
                # 图片地址过期了 → 重新读一次笔记，拿新的封面再存
                try:
                    nid = str(it.get("aweme_id") or "")
                    info = self._xhs().fetch_note(nid, url=it.get("url"), need_video=False)
                    cov = (info.get("cover") or "").strip()
                    if not cov.startswith("http"):
                        imgs = info.get("images") or []
                        cov = imgs[0] if imgs else ""
                    if str(cov).startswith("http"):
                        it2 = dict(it, cover=cov)
                        self._localize_cover(it2, via_browser=True)
                        if (it2.get("cover") or "").startswith("/files/"):
                            db.update(it["id"], cover=it2["cover"])
                            fresh += 1
                            continue
                    fail += 1
                    self.log(f"[{it['id']}] 补封面：笔记里也没拿到可用封面")
                except Exception as e:
                    fail += 1
                    self.log(f"[{it['id']}] 补封面失败：{str(e)[:60]}")
            else:
                fail += 1
            if (ok + fresh + fail) % 20 == 0:
                self.log(f"补封面进度：直接缓存 {ok} / 重读笔记 {fresh} / 失败 {fail}")
        self.log(f"补封面完成：直接缓存 {ok} 条，重读笔记补回 {fresh} 条，仍失败 {fail} 条")

    def _localize_cover(self, it, via_browser=False):
        """把远端封面存到本地，免得签名过期后一片空白。"""
        cov = (it.get("cover") or "").strip()
        if not cov.startswith("http"):
            return it
        try:
            from . import imgcache
            if via_browser and (it.get("platform") or "") == "xhs":
                lib = config.library_dir()
                d = lib / "_图片" / str(it.get("aweme_id") or it["id"])
                f = d / "cover.jpg"
                self._xhs().grab_image(cov, f)
                rel = f.relative_to(lib).as_posix()
                db.update(it["id"], cover="/files/" + rel)
                it["cover"] = "/files/" + rel
                return it
            body, ctype = imgcache.get(cov)
            ext = ".png" if "png" in (ctype or "") else (".webp" if "webp" in (ctype or "") else ".jpg")
            lib = config.library_dir()
            d = lib / "_图片" / str(it.get("aweme_id") or it["id"])
            d.mkdir(parents=True, exist_ok=True)
            f = d / ("cover" + ext)
            f.write_bytes(body)
            rel = f.relative_to(lib).as_posix()
            db.update(it["id"], cover="/files/" + rel)
            it["cover"] = "/files/" + rel
        except Exception as e:
            self.log(f"[{it['id']}] 封面存本地失败：{str(e)[:50]}")
        return it

    # ------------------------------------------------------------ 小红书
    def _sync_xhs(self, limit=50, then_process=True):
        from . import xhs
        b = self._xhs()
        self.log(f"开始读取小红书「收藏」（{'最多 ' + str(limit) + ' 条' if limit else '全部'}）……")
        added = [0]

        def on_item(d):
            url = d.get("url") or ""
            token = d.get("token") or ""
            if token and "xsec_token" not in url:
                url += ("?" if "?" not in url else "&") + f"xsec_token={token}&xsec_source=pc_collect"
            item_id, new = db.add("xhs", aweme_id=d["note_id"], url=url,
                                  title=d.get("title") or None, platform="xhs")
            if new:
                added[0] += 1
            else:
                # 老条目把地址（带 token）、标题、封面补全
                patch = {"url": url}
                if d.get("title"):
                    patch["title"] = d["title"]
                if d.get("cover"):
                    patch["cover"] = d["cover"]
                if d.get("author"):
                    patch["author"] = d["author"]
                if d.get("published_at"):
                    patch["published_at"] = d["published_at"]
                db.update(item_id, **patch)

        n = b.sync_favorites(limit=limit, on_item=on_item, should_stop=self.stopping)
        self.log(f"小红书读到 {n} 条，新增 {added[0]} 条。")
        if then_process and added[0] and not self.stopping():
            self._process_all()

    def _get_media_xhs(self, it, s):
        from . import xhs
        nid = str(it.get("aweme_id") or "") or (xhs.note_id_from_url(it.get("url")) or "")
        if not nid:
            raise douyin.DouyinError("这条没有小红书笔记 id")
        b = self._xhs()
        self._stage(it, "fetching", f"读取小红书笔记：{nid}")
        info = b.fetch_note(nid, url=it.get("url"))
        db.update(it["id"], title=info.get("title") or it.get("title"),
                  author=info.get("author") or it.get("author"),
                  media_type=("video" if info.get("video_url") else "note"),
                  cover=(it.get("cover") or info.get("cover")),
                  url=info.get("url") or it.get("url"),
                  duration=info.get("duration") or it.get("duration"))
        it.update({k: v for k, v in info.items() if v})
        it["bili_desc"] = (info.get("desc") or "")[:2000]   # 后面兜底要用，必须放到内存里
        self.prog.set_title(it.get("title"), info.get("duration"))
        if not info.get("video_url"):
            imgs = info.get("images") or []
            if not imgs:
                self.log(f"[{it['id']}] 小红书这条没读到图片，用正文/标题兜底")
                return {"note": {"images": [], "desc": (info.get("desc") or "").strip()
                                 or (info.get("title") or it.get("title") or "")}}
            self.log(f"[{it['id']}] 小红书图文：{len(imgs)} 张图，下载后识别文字")
            return {"note": {"images": [[u] for u in imgs], "desc": info.get("desc") or it.get("title") or ""}}
        dest = config.MEDIA_DIR / f"xhs_{nid}.mp4"
        vu = info.get("video_url")
        if isinstance(vu, list):
            vu = vu[0] if vu else ""
        if vu:
            db.update(it["id"], play_url=vu, play_url_ts=time.time())
        self._stage(it, "downloading", f"下载小红书视频：{(info.get('title') or '')[:24]}")
        from . import cache
        urls = info["video_url"] if isinstance(info["video_url"], list) else [info["video_url"]]
        try:
            cache.download(urls, dest, item_id=it["id"], title=it.get("title") or "",
                           referer="https://www.xiaohongshu.com/")
        except Exception:
            b.download(info["video_url"], dest)
        cache.trim()
        return dest

    def _get_media_bili(self, it, s):
        """B 站：手动粘贴的链接，取信息 → 有字幕用字幕，没字幕下音频转文字。"""
        from . import bili
        bv = str(it.get("aweme_id") or "") or (bili.match(it.get("url") or "") or "")
        if not bv:
            raise douyin.DouyinError("这条没有 B 站视频号")
        self._stage(it, "fetching", f"读取 B 站视频：{bv}")
        info = bili.fetch_info(bv)
        db.update(it["id"], title=info.get("title") or it.get("title"),
                  author=info.get("author") or it.get("author"),
                  duration=info.get("duration") or it.get("duration"),
                  published_at=info.get("published_at") or it.get("published_at"),
                  bili_desc=(info.get("desc") or "")[:2000],
                  media_type="video", aweme_id=info.get("bv") or bv)
        it.update({k: v for k, v in info.items() if v})
        self.prog.set_title(it.get("title"), info.get("duration"))
        cover = (info.get("cover") or "").strip()
        if cover:
            try:
                lib = config.library_dir()
                f = lib / "_图片" / str(info.get("bv") or bv) / "cover.jpg"
                bili.download_cover(cover, f)
                rel = f.relative_to(lib).as_posix()
                db.update(it["id"], cover="/files/" + rel)
                it["cover"] = "/files/" + rel
            except Exception as e:
                self.log(f"[{it['id']}] B 站封面没存下来：{str(e)[:50]}")
        sub = bili.subtitle_text(info.get("bv") or bv, info.get("cid"))
        if len(sub) >= 40:
            self.log(f"[{it['id']}] 用 B 站字幕（{len(sub)} 字），不用转写")
            return {"text": sub, "segments": None, "duration": info.get("duration") or 0}
        # 优先下视频（≤720p）：既转文字，又能抽帧读画面上的字；失败了退回只下音频
        self._stage(it, "downloading", f"下载 B 站视频：{(info.get('title') or '')[:24]}")
        try:
            return bili.download_video(info.get("bv") or bv, config.MEDIA_DIR, log=self.log)
        except Exception as e:
            self.log(f"[{it['id']}] 视频没下下来（{str(e)[:60]}），改用音频")
            try:
                return bili.download_audio(info.get("bv") or bv, config.MEDIA_DIR, log=self.log)
            except Exception as e2:
                raise douyin.DouyinError(f"B 站下载失败：{str(e2)[:120]}")

    def _get_media(self, it, s):
        """返回本地视频路径；视频自带字幕时返回 {"text", "segments"}；不需要处理时返回 None（已标记跳过）。"""
        if (it.get("platform") or "") == "bili":
            return self._get_media_bili(it, s)
        if (it.get("platform") or "douyin") == "xhs":
            return self._get_media_xhs(it, s)
        if it["source"] == "local":
            p = Path(it["local_path"])
            if not p.exists():
                raise douyin.DouyinError("本地文件不见了")
            return p

        aweme_id = it.get("aweme_id")
        if not aweme_id:
            self._stage(it, "fetching", f"解析链接：{it['url'][:40]}")
            aweme_id, kind = douyin.resolve(it["url"])
            if kind == "note":
                db.update(it["id"], media_type="note")
                it["media_type"] = "note"
            other = db.conn().execute("SELECT id FROM items WHERE aweme_id=? AND id<>?",
                                      (aweme_id, it["id"])).fetchone()
            if other:
                db.delete(it["id"])
                self.log(f"[{it['id']}] 这个视频之前已经加过了（第 {other['id']} 条），不重复处理。")
                return None
            db.update(it["id"], aweme_id=aweme_id)
            it["aweme_id"] = aweme_id

        kind = "note" if it.get("media_type") == "note" else "video"
        self._stage(it, "fetching", f"读取{'图文' if kind == 'note' else '视频'}信息：{aweme_id}")
        b = self._browser()
        try:
            d = b.fetch_detail(aweme_id, kind)
        except douyin.NotLoggedIn:
            b.ensure_login(should_stop=self.stopping)
            d = b.fetch_detail(aweme_id, kind)
        db.update(it["id"], title=d.get("title") or it.get("title"), author=d.get("author") or it.get("author"),
                  duration=d.get("duration") or it.get("duration"),
                  # 封面优先用详情接口这一条的（按视频来的，不会串）；列表里的图偶尔会串成别的视频
                  cover=d.get("cover") or it.get("cover"),
                  url=d.get("url") or it.get("url"),
                  # 顺手把发布时间补上（老数据第一次处理时就补齐）
                  published_at=d.get("published_at") or it.get("published_at"),
                  collected_at=d.get("collected_at") or it.get("collected_at"))
        it.update({k: v for k, v in d.items()
                   if v and k in ("title", "author", "duration", "cover", "url", "published_at", "collected_at")})
        self.prog.set_title(it.get("title"), d.get("duration"))
        if d.get("is_ad"):
            self.log(f"[{it['id']}] 这条带广告标识，照常拆，让 AI 判断")
        if d.get("is_note"):
            db.update(it["id"], media_type="note")
            it["media_type"] = "note"
            if not d.get("images"):
                self.log(f"[{it['id']}] 抖音这条图文没读到图片，用标题兜底")
                return {"note": {"images": [], "desc": (d.get("desc") or "").strip()
                                 or (it.get("title") or "")}}
            return {"note": d}

        if s.get("use_subtitles", True) and d.get("subtitle_urls"):
            for su in d["subtitle_urls"]:
                try:
                    raw = b.fetch_text(su)
                    text = transcribe.parse_subtitle(raw)
                except Exception:
                    continue
                if len(text) >= 30:
                    self.log(f"[{it['id']}] 视频自带字幕，直接使用（跳过下载和转写）")
                    return {"text": text, "segments": transcribe.subtitle_segments(raw)}

        self._stage(it, "downloading", f"下载视频：{(it.get('title') or '')[:30]}")
        dest = config.MEDIA_DIR / f"{aweme_id}.mp4"
        from . import cache
        urls = d.get("play_urls") or []
        if urls:
            db.update(it["id"], play_url=urls[0], play_url_ts=time.time())
        try:
            cache.download(urls, dest, item_id=it["id"], title=it.get("title") or "")
        except Exception:
            b.download(urls, dest)
        # 抖音有些源只给音频流（下下来没画面），先记一笔，别在源之间来回试拖慢队列
        if dest.exists() and not has_video_stream(dest):
            self.log(f"[{it['id']}] 这条只下到音频（没有画面），读画面文字会跳过")
        cache.trim()
        time.sleep(1.0)  # 别太快，降低被风控的概率
        return dest

    def _process_note(self, it, d):
        """图文：下载图片到笔记目录，识别图片里的文字，和正文合成文字稿。返回 False 表示已标记跳过。"""
        aweme_id = it.get("aweme_id") or str(it["id"])
        imgs = d.get("images") or []
        # 头像/图标一律不要（之前混进笔记里出现过）
        imgs = [[u for u in cand if "avatar" not in str(u).lower()] for cand in imgs]
        imgs = [c for c in imgs if c]
        self.prog.mark_note(len(imgs))
        self._stage(it, "downloading", f"下载图文图片（{len(imgs)} 张）：{(it.get('title') or '')[:24]}")
        lib = config.library_dir()
        folder = lib / notes.IMAGE_DIR / aweme_id
        try:
            if (it.get("platform") or "douyin") == "xhs":
                files = self._xhs().download_images(imgs, folder)
            else:
                files = self._browser().download_images(imgs, folder)
        except douyin.DouyinError:
            files = []
            self.log(f"[{it['id']}] 图文的图都拿不到（可能是占位图），只用正文")
        rels = [f.relative_to(lib).as_posix() for f in files]
        db.update(it["id"], images=rels, cover=("/files/" + rels[0]) if rels else None)

        self._stage(it, "transcribing", f"识别图片文字（{len(files)} 张）")
        parts = []
        desc = (d.get("desc") or it.get("title") or "").strip()
        if desc:
            parts.append("【正文】\n" + desc)
        if ocr.backend() is None:
            self.log(f"[{it['id']}] ⚠ 没装文字识别组件，只用正文。重新运行一次安装脚本就能识别图片里的字。")
        else:
            for i, f in enumerate(files, 1):
                if self.stopping():
                    break
                try:
                    text = ocr.recognize(f)
                except Exception as e:
                    self.log(f"[{it['id']}] 第 {i} 张图识别失败：{str(e)[:80]}")
                    text = ""
                if text:
                    parts.append(f"【图{i}】\n{text}")
                self.prog.set_frac(i / len(files))
        transcript = "\n\n".join(parts)
        if len(transcript.replace("【正文】", "").replace(" ", "").replace("\n", "")) < 15:
            # 图里没字也不丢：用正文/标题凑一份，照样生成笔记
            fallback = (desc or "").strip() or (it.get("title") or "")
            transcript = "【正文】" + chr(10) + fallback + chr(10) + chr(10) + "（图片里没有可识别的文字）"
            self.log(f"[{it['id']}] 图片里几乎没有文字，用正文/标题兜底")
        db.update(it["id"], transcript=transcript, segments=None)
        self.log(f"[{it['id']}] 图文文字已提取：{len(files)} 张图，共 {len(transcript)} 字")
        return True

    def _cleanup(self, it, media, s):
        if media is None:
            return
        if it["source"] == "local" or s.get("keep_video", True):
            return
        try:
            Path(media).unlink(missing_ok=True)
        except Exception:
            pass


def scan_inbox():
    """把 data/inbox 文件夹里的音视频加入队列。返回新增条数。"""
    n = 0
    for p in sorted(config.INBOX_DIR.rglob("*")):
        if p.is_file() and p.suffix.lower() in MEDIA_EXT:
            _, new = db.add("local", local_path=str(p), title=p.stem, jump=True)
            n += int(new)
    return n
