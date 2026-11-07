"""后台处理线程：一条一条地 读信息 → 下载 → 转文字 → AI 提炼 → 写笔记。

浏览器只能在同一个线程里操作，所以所有抖音相关的事都放在这个线程里排队做。
"""
import collections
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
        self.retry_later = []
        self.prog = progress.Progress()
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

    # ------------------------------------------------------------ 主循环
    def _run(self):
        self._selfcheck()
        while True:
            cmd, kw = self.cmds.get()
            self.state.update(busy=True, task=cmd, stage="", item_id=None)
            try:
                if cmd == "process":
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
                    ok = self._xhs(visible=False).ensure_login(should_stop=self.stopping, qr_path=qr)
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
        skipped_n = db.skip_by_category()
        if skipped_n:
            self.log(f"按分类跳过 {skipped_n} 条生活/娱乐类内容（不拆解，想处理可以进详情页点「还是处理这条」）")
        self.state.update(done=0, total=db.stats()["by_status"].get("queued", 0))
        if not self.state["total"]:
            self.log("队列里没有待处理的视频。")
            return
        self.log(f"开始处理，共 {self.state['total']} 条。")
        while not self.stopping():
            it = db.next_queued()
            if it is None:
                if self.retry_later:
                    ids, self.retry_later = self.retry_later, []
                    self.log(f"有 {len(ids)} 条失败了，30 秒后自动重试一次……")
                    for _ in range(30):
                        if self.stopping():
                            return
                        time.sleep(1)
                    for i in ids:
                        db.update(i, status="queued")
                    self.state["total"] += len(ids)
                    continue
                break
            self.state.update(item_id=it["id"])
            self._process_one(it)
            self.state["done"] += 1
            # 有新的登录/同步请求就先把队列让出来，处理完再继续这批
            if not self.cmds.empty():
                self.log("有新的请求，先让路（稍后继续处理队列）")
                self.cmds.put(("process", {}))
                break
            # 队列在跑的时候顺手把「全部缓存」的任务也推进一步，两边不耽误
            from . import cache as _cache
            if _cache.all_state()["on"]:
                self._cache_step()
        self.log("这一批处理完了。" if not self.stopping() else "已停止。")

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
                from . import xhs as _xhs
                url = _xhs.resolve_video_url(aid, log=self.log)
                urls = [url] if url else []
                referer = "https://www.xiaohongshu.com/"
            else:
                b = self._browser()
                d = b.fetch_detail(aid) or {}
                urls = d.get("play_urls") or []
                if urls:
                    db.update(it["id"], play_url=urls[0], play_url_ts=time.time())
                referer = "https://www.douyin.com/"
            if not urls:
                raise douyin.DouyinError("取不到播放地址")
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
                try:
                    tr = transcribe.transcribe(
                        media, engine=s.get("asr_engine", "auto"), mlx_model=s.get("mlx_model"),
                        size=s.get("whisper_model", "small"), use_mirror=s.get("use_hf_mirror", False),
                        max_minutes=s.get("max_minutes", 15), log=self.log, should_stop=self.stopping,
                        on_progress=self.prog.set_frac, hint=(it.get("title") or "")[:120])
                except transcribe.NoSpeech as e:
                    db.update(it["id"], status="skipped", reason=str(e))
                    self.log(f"[{it['id']}] 跳过：{e}")
                    self._cleanup(it, media, s)
                    return
                self._cleanup(it, media, s)
                if self.stopping():
                    db.update(it["id"], status="queued")
                    return
                db.update(it["id"], transcript=tr["text"], segments=tr["segments"],
                          duration=it.get("duration") or tr["duration"])
                it = db.get(it["id"])

            # 3. AI 提炼
            if not (s.get("api_key") or "").strip():
                db.update(it["id"], status="need_key", reason="已转成文字，填好 AI Key 后点「重新提炼」生成笔记")
                self.log(f"[{it['id']}] 已转成文字；还没填 AI Key，先不提炼。")
                return
            self._stage(it, "extracting", f"AI 提炼：{label}")
            note, used = llm.extract(s, it.get("title"), it.get("author"), it["transcript"],
                                     kind="note" if it.get("media_type") == "note" else "video")
            config.add_tokens(used)
            if note.get("skip"):
                db.update(it["id"], status="skipped", reason=note.get("skip_reason"), note=None)
                self.log(f"[{it['id']}] 跳过：{note.get('skip_reason')}")
                return
            if not note["relevant"] and s.get("only_relevant", True) and it["source"] != "paste":
                notes.remove(it)
                c0, sub0 = classify.normalize_note_category(note.get("category"))
                db.update(it["id"], status="irrelevant", note=note, category=c0, subcategory=sub0 or None, md_path=None,
                          reason="和你设置的关注主题无关，已收起")
                self.log(f"[{it['id']}] 和关注主题无关，已收起：{note['title']}")
                return
            it["note"] = note
            path = notes.write(it)
            c0, sub0 = classify.normalize_note_category(note.get("category"))
            db.update(it["id"], status="done", note=note, category=c0, subcategory=sub0 or None,
                      md_path=path, reason=None)
            self.log(f"[{it['id']}] ✓ 完成：{note['title']}")

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
        db.update(it["id"], status="failed", reason=msg, attempts=attempts)
        self.log(f"[{it['id']}] ✗ 失败：{msg}")
        if retry and attempts < (3 if _browser_dead(msg) else 2):
            self.retry_later.append(it["id"])

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
        self.prog.set_title(it.get("title"), info.get("duration"))
        if not info.get("video_url"):
            imgs = info.get("images") or []
            if not imgs:
                db.update(it["id"], status="skipped", reason="这条笔记没有可用的图片或视频")
                self.log(f"[{it['id']}] 跳过：小红书这条没有可用的图片")
                return None
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

    def _get_media(self, it, s):
        """返回本地视频路径；视频自带字幕时返回 {"text", "segments"}；不需要处理时返回 None（已标记跳过）。"""
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
            db.update(it["id"], status="skipped", reason="广告视频")
            self.log(f"[{it['id']}] 跳过：广告")
            return None
        if d.get("is_note"):
            db.update(it["id"], media_type="note")
            it["media_type"] = "note"
            if not d.get("images"):
                db.update(it["id"], status="skipped", reason="这条图文没有读到图片")
                return None
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
        cache.trim()
        time.sleep(1.0)  # 别太快，降低被风控的概率
        return dest

    def _process_note(self, it, d):
        """图文：下载图片到笔记目录，识别图片里的文字，和正文合成文字稿。返回 False 表示已标记跳过。"""
        aweme_id = it.get("aweme_id") or str(it["id"])
        imgs = d.get("images") or []
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
            db.update(it["id"], status="skipped", reason="图文里几乎没有文字（可能是纯图片、表情包或摄影作品）")
            self.log(f"[{it['id']}] 跳过：图文里几乎没有文字")
            return False
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
            _, new = db.add("local", local_path=str(p), title=p.stem)
            n += int(new)
    return n
