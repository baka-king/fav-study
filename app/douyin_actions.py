"""在抖音网页里替你做动作：点赞、取消收藏、发评论，以及取原视频的播放地址。

用的是同一个登录态浏览器：
- 程序正在后台跑任务 → 通过 CDP（远程调试端口）连上那个浏览器；
- 没在跑任务 → 临时开一个，做完就关。
动作都是真的在页面上点按钮，和你自己手点完全一样，所以不会触发接口签名校验。
"""
import queue
import threading
import time
import urllib.request

from . import douyin

CDP_PORT = getattr(douyin, "CDP_PORT", 9333)
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

LIKE_SEL = '[data-e2e="video-player-digg"]'
COLLECT_SEL = '[data-e2e="video-player-collect"]'
KIND_LABEL = {"like": "点赞", "collect": "收藏", "uncollect": "取消收藏", "comment": "发评论", "state": "查状态"}


class ActionError(Exception):
    pass

# 由 server 启动时注入：让后台把抖音浏览器跑起来（带 9333 调试端口）
START_BROWSER = None


def _wait_cdp(sec=30):
    end = time.time() + sec
    while time.time() < end:
        if _cdp_alive(0.6):
            return True
        time.sleep(0.6)
    return False


def _cdp_alive(timeout=1.2):
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


class Session:
    """借用一个浏览器会话：能连上后台那个就连，连不上就自己开一个。"""

    def __init__(self, log=print):
        self.log = log
        self.pw = None
        self.browser = None
        self.ctx = None
        self.own = None          # 自己开的 persistent context，用完要关

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        if not _cdp_alive() and START_BROWSER:
            # 后台没有浏览器在跑：先让它起来（用同一个登录态），再通过 CDP 接上去。
            # 直接自己再开一个 persistent context 会跟同一个用户目录打架，必失败。
            try:
                START_BROWSER()
            except Exception:
                pass
            _wait_cdp(30)
        if _cdp_alive():
            self.browser = self.pw.chromium.connect_over_cdp(CDP_URL)
            if not self.browser.contexts:
                raise ActionError("浏览器连上了但还没有可用的窗口")
            self.ctx = self.browser.contexts[0]
            self.log("借用后台浏览器")
            return self.ctx

        errors = []
        for ch in ("msedge", "chrome"):
            try:
                self.own = self.pw.chromium.launch_persistent_context(
                    user_data_dir=str(douyin.BROWSER_DIR / ch),
                    headless=False, channel=ch,
                    viewport={"width": 1280, "height": 860}, locale="zh-CN",
                    args=["--disable-blink-features=AutomationControlled",
                          "--no-first-run", "--no-default-browser-check",
                          # 后台操作：窗口别弹到屏幕中间
                          "--window-position=-3200,-3200", "--window-size=1280,860",
                          f"--remote-debugging-port={CDP_PORT}"],
                    ignore_default_args=["--enable-automation"],
                )
                self.ctx = self.own
                self.log(f"临时打开浏览器（{ch}）")
                return self.ctx
            except Exception as e:
                errors.append(f"{ch}: {str(e)[:120]}")
        raise ActionError("打不开浏览器（后台那个也没起来，可能是登录窗口被关了）。"
                          "请先点一次「登录抖音」或「同步收藏」，再试。" + "；".join(errors))

    def __exit__(self, *exc):
        for fn in (lambda: self.own and self.own.close(),
                   lambda: self.browser and self.browser.close(),
                   lambda: self.pw and self.pw.stop()):
            try:
                fn()
            except Exception:
                pass
        self.pw = self.ctx = self.browser = self.own = None


def _open_video(ctx, aweme_id, wait=1500):
    """打开视频页。用 commit 而不是 domcontentloaded：后台正在抓别的视频时，整页加载会互相拖慢。"""
    page = ctx.new_page()
    try:
        page.goto(f"https://www.douyin.com/video/{aweme_id}", wait_until="commit", timeout=25000)
    except Exception:
        pass
    try:
        page.wait_for_selector('[data-e2e="video-player-digg"]', timeout=20000, state="attached")
    except Exception:
        pass
    page.wait_for_timeout(wait)
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    return page


def _state(page, sel):
    return page.evaluate("(s) => { const e = document.querySelector(s); return e ? e.getAttribute('data-e2e-state') : null; }", sel)


def _click(page, sel):
    ok = page.evaluate("(s) => { const e = document.querySelector(s); if (!e) return false; e.click(); return true; }", sel)
    if not ok:
        raise ActionError("页面上没找到按钮，可能页面没加载完或抖音改版了")
    return True


def _wait_state(page, sel, want, timeout=12.0):
    end = time.time() + timeout
    while time.time() < end:
        if _state(page, sel) == want:
            return True
        page.wait_for_timeout(400)
    return False


def do_flip(page, kind):
    """点一下切换：kind = like（点赞/取消）或 collect（收藏/取消）。返回做了什么。"""
    if kind == "like":
        sel = LIKE_SEL
        on, off = "video-player-is-digged", "video-player-no-digged"
        on_txt, off_txt = "已点赞", "已取消点赞"
    else:
        sel = COLLECT_SEL
        on, off = "video-player-is-collected", "video-player-no-collect"
        on_txt, off_txt = "已重新收藏", "已取消收藏"
    st = _state(page, sel)
    if st is None:
        raise ActionError("页面上没找到按钮，可能视频已删除或页面没加载完")
    was_on = (st == on)
    want = off if was_on else on
    _click(page, sel)
    if not _wait_state(page, sel, want):
        raise ActionError("点了但没生效，可能触发了抖音验证，看一眼浏览器窗口")
    return off_txt if was_on else on_txt


def do_comment(page, text):
    text = (text or "").strip()
    if not text:
        raise ActionError("评论内容不能为空")
    if len(text) > 200:
        raise ActionError("评论太长了（抖音限制 200 字以内）")
    # 点开评论输入框
    clicked = False
    for _ in range(2):
        try:
            page.get_by_text("留下你的精彩评论吧", exact=True).first.click(timeout=5000)
            clicked = True
            break
        except Exception:
            page.wait_for_timeout(800)
    if not clicked:
        try:
            _click(page, '[data-e2e="feed-comment-icon"]')
            page.wait_for_timeout(1200)
            page.get_by_text("留下你的精彩评论吧", exact=True).first.click(timeout=5000)
            clicked = True
        except Exception:
            clicked = False
    if not clicked:
        raise ActionError("打不开评论输入框")

    box = page.query_selector(".public-DraftEditor-content")
    if not box:
        raise ActionError("没找到评论输入框")
    box.click()
    page.wait_for_timeout(300)
    page.keyboard.type(text)
    page.wait_for_timeout(600)
    typed = page.evaluate("() => { const e = document.querySelector('.public-DraftEditor-content'); return e ? e.innerText.trim() : ''; }")
    if not typed:
        raise ActionError("评论没输进去")
    page.keyboard.press("Enter")
    page.wait_for_timeout(2500)
    left = page.evaluate("() => { const e = document.querySelector('.public-DraftEditor-content'); return e ? e.innerText.trim() : ''; }")
    if left:
        raise ActionError("评论没发出去（回车没生效），内容还留在输入框里")
    return "评论已发出"


def get_play_url(aweme_id):
    """打开视频页，从「详情接口」的响应里拿真正的视频地址（页面上的 currentSrc 是 blob 流，代理不了）。"""
    detail = None
    with Session() as ctx:
        page = ctx.new_page()
        hits = []

        def on_resp(r):
            if "/aweme/v1/web/aweme/detail" in r.url:
                hits.append(r)

        page.on("response", on_resp)
        try:
            page.goto(f"https://www.douyin.com/video/{aweme_id}", wait_until="commit", timeout=25000)
            end = time.time() + 25
            while time.time() < end and detail is None:
                while hits and detail is None:
                    r = hits.pop(0)
                    try:
                        j = r.json()
                        if j.get("aweme_detail"):
                            detail = j["aweme_detail"]
                    except Exception:
                        pass
                if detail is None:
                    page.wait_for_timeout(500)
        finally:
            try:
                page.remove_listener("response", on_resp)
                page.close()
            except Exception:
                pass
    if not detail:
        return None
    d = douyin.parse_aweme(detail)
    urls = [u for u in (d.get("play_urls") or []) if u and u.startswith("http")]
    return urls[0] if urls else None


def fetch_danmaku(aweme_id, wait_ms=15000):
    """抓一次视频页的弹幕（页面自己请求 danmaku/get_v2，我们只是把它接住）。"""
    data = None
    with Session() as ctx:
        page = ctx.new_page()
        hits = []

        def on_resp(r):
            if "danmaku/get_v2" in r.url:
                hits.append(r)

        page.on("response", on_resp)
        try:
            page.goto(f"https://www.douyin.com/video/{aweme_id}", wait_until="commit", timeout=25000)
            end = time.time() + wait_ms / 1000.0
            while time.time() < end and data is None:
                while hits:
                    r = hits.pop(0)
                    try:
                        j = r.json()
                        if isinstance(j, dict) and "danmaku_list" in j:
                            data = j
                            break
                    except Exception:
                        pass
                if data is None and hits:
                    continue
                if data is None:
                    page.wait_for_timeout(500)
        finally:
            try:
                page.remove_listener("response", on_resp)
                page.close()
            except Exception:
                pass
    lst = (data or {}).get("danmaku_list") or []
    out = []
    for d in lst:
        if not isinstance(d, dict):
            continue
        t = d.get("offset_time") or d.get("start_time") or d.get("time") or 0
        txt = str(d.get("text") or d.get("content") or "").strip()
        try:
            t = float(t)
        except Exception:
            t = 0.0
        if t > 60:   # 抖音弹幕的时间是毫秒
            t = t / 1000.0
        if txt:
            out.append({"t": round(t, 1), "text": txt[:120]})
    out.sort(key=lambda x: x["t"])
    return out


def fetch_meta(aweme_id, want_comments=True, wait_ms=16000):
    """打开一次视频页，接住「详情」（点赞/评论/收藏数、我有没有赞过）和评论列表。

    页面自己会去请求 detail 和 comment/list 接口，我们只是把响应接住，不用自己签名。
    返回 (stats, comments)；取不到的部分是 {} / []。
    """
    detail, comments = None, None
    with Session() as ctx:
        page = ctx.new_page()
        dhits, chits = [], []

        def on_resp(r):
            u = r.url
            if "/aweme/v1/web/aweme/detail" in u:
                dhits.append(r)
            elif "/aweme/v1/web/comment/list" in u:
                chits.append(r)

        page.on("response", on_resp)
        try:
            page.goto(f"https://www.douyin.com/video/{aweme_id}", wait_until="commit", timeout=25000)
            end = time.time() + wait_ms / 1000.0
            while time.time() < end:
                if detail is None:
                    for r in list(dhits):
                        try:
                            j = r.json()
                        except Exception:
                            continue
                        if isinstance(j, dict) and j.get("aweme_detail"):
                            detail = j["aweme_detail"]
                            dhits.clear()
                            break
                if want_comments and comments is None:
                    for r in list(chits):
                        try:
                            j = r.json()
                        except Exception:
                            continue
                        if isinstance(j, dict) and "comments" in j:
                            comments = j.get("comments") or []
                            chits.clear()
                            break
                if detail is not None and (comments is not None or not want_comments):
                    break
                page.wait_for_timeout(350)
        finally:
            try:
                page.remove_listener("response", on_resp)
                page.close()
            except Exception:
                pass

    stats = {}
    if detail:
        st = detail.get("statistics") or {}
        stats = {
            "digg": int(st.get("digg_count") or 0),
            "comment": int(st.get("comment_count") or 0),
            "collect": int(st.get("collect_count") or 0),
            "share": int(st.get("share_count") or 0),
            "liked": bool(detail.get("user_digged")),
        }

    out = []
    for c in comments or []:
        if not isinstance(c, dict):
            continue
        txt = str(c.get("text") or "").strip()
        if not txt:
            continue
        user = c.get("user") or {}
        av = ((user.get("avatar_thumb") or {}).get("url_list") or [None])
        out.append({
            "id": str(c.get("cid") or ""),
            "text": txt[:300],
            "user": str(user.get("nickname") or "抖音用户")[:40],
            "avatar": av[0] if av else None,
            "likes": int(c.get("digg_count") or 0),
            "replies": int(c.get("reply_comment_total") or 0),
            "time": int(c.get("create_time") or 0),
        })
    out.sort(key=lambda x: -x["likes"])
    return stats, out[:40]


def do_state(page):
    """只读：现在是不是已点赞 / 已收藏。"""
    like = _state(page, LIKE_SEL)
    coll = _state(page, COLLECT_SEL)
    return ("已点赞" if like == "video-player-is-digged" else "未点赞") + " / " +            ("已收藏" if coll == "video-player-is-collected" else "未收藏")


class Runner:
    """抖音动作在单独线程里排队做，界面不会卡住。"""

    def __init__(self, log=print):
        self.log = log
        self.q = queue.Queue()
        self.state = {"busy": False, "kind": "", "stage": "", "last": "", "error": "", "finished_at": 0}
        self._urls = {}
        self._url_lock = threading.Lock()
        self._waits = {}           # aweme_id -> (Event, 结果盒)
        threading.Thread(target=self._run, daemon=True, name="douyin-actions").start()

    def snapshot(self):
        return dict(self.state)

    def submit(self, kind, aweme_id, text=""):
        self.q.put((kind, str(aweme_id), text))
        self.state.update(kind=kind, stage="排队中", error="")

    def cached_url(self, aweme_id, max_age=1200):
        with self._url_lock:
            got = self._urls.get(str(aweme_id))
            if got and time.time() - got[1] < max_age:
                return got[0]
        return None

    def fetch_play_url(self, aweme_id, timeout=75):
        """让后台线程去取播放地址（同一时间只开一个浏览器），同步等结果。"""
        aweme_id = str(aweme_id)
        url = self.cached_url(aweme_id)
        if url:
            return url
        ev, box = threading.Event(), {}
        self._waits[aweme_id] = (ev, box)
        self.submit("play_url", aweme_id)
        ev.wait(timeout)
        self._waits.pop(aweme_id, None)
        return box.get("url")

    def cached_danmaku(self, aweme_id, max_age=1800):
        with self._url_lock:
            got = self._urls.get("dm:" + str(aweme_id))
            if got and time.time() - got[1] < max_age:
                return got[0]
        return None

    def remember_danmaku(self, aweme_id, items):
        with self._url_lock:
            self._urls["dm:" + str(aweme_id)] = (items, time.time())

    def remember(self, aweme_id, url):
        with self._url_lock:
            self._urls[str(aweme_id)] = (url, time.time())

    def _do(self, kind, aweme_id, text):
        if kind == "state":
            with Session() as ctx:
                page = _open_video(ctx, aweme_id)
                try:
                    return do_state(page)
                finally:
                    try:
                        page.close()
                    except Exception:
                        pass
        if kind == "uncollect":
            with Session() as ctx:
                page = _open_video(ctx, aweme_id)
                try:
                    st = _state(page, COLLECT_SEL)
                    if st != "video-player-is-collected":
                        return "本来就没收藏"
                    _click(page, COLLECT_SEL)
                    if not _wait_state(page, COLLECT_SEL, "video-player-no-collect"):
                        raise ActionError("点了但没生效，可能触发了抖音验证，看一眼浏览器窗口")
                    return "已取消收藏"
                finally:
                    try:
                        page.close()
                    except Exception:
                        pass
        if kind == "play_url":
            url = get_play_url(aweme_id)
            if not url:
                raise ActionError("没取到播放地址（可能视频已删除或需要验证）")
            self.remember(aweme_id, url)
            box = self._waits.get(str(aweme_id))
            if box:
                box[1]["url"] = url
                box[0].set()
            return "ok"
        with Session() as ctx:
            page = _open_video(ctx, aweme_id)
            try:
                return do_comment(page, text) if kind == "comment" else do_flip(page, kind)
            finally:
                try:
                    page.close()
                except Exception:
                    pass

    def _run(self):
        while True:
            kind, aweme_id, text = self.q.get()
            self.state.update(busy=True, kind=kind, stage="打开原视频…", error="", last="")
            box = {}

            def task():
                try:
                    box["msg"] = self._do(kind, aweme_id, text)
                except Exception as e:
                    box["err"] = str(e)[:300]

            t = threading.Thread(target=task, daemon=True)
            t.start()
            t.join(100)      # 卡住也不能把后面的动作堵死
            if t.is_alive():
                self.state.update(error="这次抖音页面没响应，已跳过；稍后再试一次")
                self.log("抖音动作卡住，已跳过")
            elif box.get("err"):
                self.state.update(error=box["err"])
                self.log(f"抖音动作失败：{box['err'][:200]}")
            else:
                msg = box.get("msg", "")
                self.state.update(last=msg)
                if kind != "play_url":
                    self.log(f"抖音动作：{KIND_LABEL.get(kind, kind)} → {msg}")
            box_wait = self._waits.get(str(aweme_id))
            if box_wait:
                box_wait[0].set()
            self.state.update(busy=False, stage="", finished_at=time.time())
