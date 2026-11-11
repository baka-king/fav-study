"""抖音相关：解析分享链接、用你自己的浏览器登录态读取视频信息 / 收藏夹、下载视频。

原理：打开一个真实浏览器窗口（优先用电脑上已有的 Edge / Chrome），你扫码登录一次，
登录态保存在 data/browser 里。之后程序打开视频页或收藏页，网页自己会去请求视频数据，
程序只是"旁听"这些数据，不自己伪造签名，所以比直接调接口稳定。
"""
import random
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import BROWSER_DIR

UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

URL_RE = re.compile(r"https?://[^\s　-〿＀-￯<>\"']+")
ID_PATTERNS = [
    (re.compile(r"douyin\.com/video/(\d{8,})"), "video"),
    (re.compile(r"douyin\.com/note/(\d{8,})"), "note"),
    (re.compile(r"iesdouyin\.com/share/video/(\d{8,})"), "video"),
    (re.compile(r"iesdouyin\.com/share/note/(\d{8,})"), "note"),
    (re.compile(r"[?&](?:modal_id|aweme_id|vid)=(\d{8,})"), "video"),
]


class DouyinError(Exception):
    pass


class NotLoggedIn(DouyinError):
    pass


# ---------------------------------------------------------------- 链接解析

def extract_links(text: str):
    """从一大段粘贴内容里找出所有抖音链接（支持"复制打开抖音"那种分享口令）。"""
    found = []
    for m in URL_RE.finditer(text or ""):
        u = m.group(0).rstrip(".,;:!?)）】」'\"")
        if "douyin.com" in u or "iesdouyin.com" in u:
            if u not in found:
                found.append(u)
    # 也接受一行只写视频 ID 的情况
    for line in (text or "").splitlines():
        line = line.strip()
        if re.fullmatch(r"\d{15,20}", line) and line not in found:
            found.append(line)
    return found


def _match_id(url: str):
    for pat, kind in ID_PATTERNS:
        m = pat.search(url)
        if m:
            return m.group(1), kind
    return None, None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def resolve(url: str):
    """把链接变成 (视频ID, 类型)。短链 v.douyin.com 需要跟一下跳转。"""
    if re.fullmatch(r"\d{15,20}", url):
        return url, "video"
    vid, kind = _match_id(url)
    if vid:
        return vid, kind
    opener = urllib.request.build_opener(_NoRedirect)
    current = url
    for _ in range(6):
        req = urllib.request.Request(current, headers={"User-Agent": UA_MOBILE})
        try:
            resp = opener.open(req, timeout=15)
            final = resp.geturl()
            resp.close()
            vid, kind = _match_id(final)
            if vid:
                return vid, kind
            break
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location")
            if e.code in (301, 302, 303, 307, 308) and loc:
                current = urllib.request.urljoin(current, loc)
                vid, kind = _match_id(current)
                if vid:
                    return vid, kind
                continue
            raise DouyinError(f"链接打不开（HTTP {e.code}）")
        except urllib.error.URLError as e:
            raise DouyinError(f"网络连不上抖音：{e.reason}")
    raise DouyinError("没能从链接里识别出视频 ID，请确认是抖音视频的分享链接")


# ---------------------------------------------------------------- 数据整理

def _https(u):
    if not u:
        return u
    return "https:" + u if u.startswith("//") else u


# 抖音拿不到图/被风控时会返回「电子营业执照」占位图，这种地址不能当封面
BAD_IMG_MARKS = ("p-pc-weboff.byteimg.com", "emblem-new", "tos-cn-i-9r5gewecjs")


def _usable_img(u):
    if not u:
        return False
    ul = str(u).lower()
    return not any(m in ul for m in BAD_IMG_MARKS)


def parse_aweme(a: dict) -> dict:
    """把抖音返回的一条视频数据整理成我们需要的字段。"""
    video = a.get("video") or {}
    urls = []

    def add(lst):
        for u in lst or []:
            u = _https(u)
            if u and u.startswith("http") and u not in urls:
                urls.append(u)

    # 优先 720p：体积只有原画的 1/3~1/5，下载快、不占空间，转文字和观看都够用
    brs = sorted(video.get("bit_rate") or [], key=lambda b: b.get("bit_rate", 0))
    pref = None
    for b in brs:
        gear = str(b.get("gear_name") or "").lower()
        if "720" in gear:
            pref = b
            break
    if pref is None and brs:
        pref = brs[0]
    if pref:
        add((pref.get("play_addr") or {}).get("url_list"))
    add((video.get("play_addr") or {}).get("url_list"))
    add((video.get("play_addr_h264") or {}).get("url_list"))
    for br in brs:
        add((br.get("play_addr") or {}).get("url_list"))
    add((video.get("download_addr") or {}).get("url_list"))

    cover = None
    for key in ("cover", "origin_cover", "dynamic_cover"):
        for u in (video.get(key) or {}).get("url_list") or []:
            u = _https(u)
            if _usable_img(u):
                cover = u
                break
        if cover:
            break

    # 视频自带的字幕（作者上传的或抖音自动生成的），有的话可以跳过下载和转写
    subs = []
    for s in (video.get("subtitle_infos") or []) + (a.get("subtitle_infos") or []):
        if not isinstance(s, dict):
            continue
        su = _https(s.get("Url") or s.get("url") or s.get("SubtitleUrl") or "")
        lang = str(s.get("LanguageCodeName") or s.get("language_code_name") or s.get("Language") or "")
        if su and su.startswith("http") and (not lang or lang.lower().startswith(("zh", "cmn", "chs"))):
            subs.append(su)

    raw_imgs = a.get("images") or (a.get("image_post_info") or {}).get("images") or []
    images = []
    for img in raw_imgs:
        if not isinstance(img, dict):
            continue
        cands = []
        for key in ("url_list", "download_url_list"):  # url_list 是无水印原图，download_url_list 带水印，作备用
            for u in img.get(key) or []:
                u = _https(u)
                if u and u.startswith("http") and u not in cands and _usable_img(u):
                    cands.append(u)
        # jpeg 最通用（有的是 webp/heic），排前面
        cands.sort(key=lambda u: 0 if ("jpeg" in u or ".jpg" in u) else (1 if "webp" in u else 2))
        if cands:
            images.append(cands)
    is_note = bool(images) or a.get("aweme_type") in (68, 150)
    dur = video.get("duration") or a.get("duration") or 0
    aweme_id = str(a.get("aweme_id") or "")

    def _ts(*keys):
        """时间戳统一成秒。抖音有的接口给毫秒。"""
        for k in keys:
            v = a.get(k)
            if isinstance(v, (int, float)) and v > 0:
                return v / 1000 if v > 10_000_000_000 else v
        return None

    return {
        "aweme_id": aweme_id,
        "title": (a.get("desc") or "").strip() or f"抖音{'图文' if (raw_imgs or a.get('aweme_type') in (68, 150)) else '视频'} {aweme_id}",
        "desc": (a.get("desc") or "").strip(),
        "author": (a.get("author") or {}).get("nickname") or "",
        "duration": round(dur / 1000, 1) if dur > 1000 else dur,
        "cover": cover,
        "play_urls": urls,
        "subtitle_urls": subs,
        "is_ad": bool(a.get("is_ads") or a.get("raw_ad_data")),
        "is_note": is_note,
        "images": images,
        "url": (f"https://www.douyin.com/{'note' if is_note else 'video'}/{aweme_id}") if aweme_id else None,
        # 视频发布时间；收藏列表里可能还带收藏时间（不同版本字段名不一样，都试一遍）
        "published_at": _ts("create_time", "create_time_ms"),
        "collected_at": _ts("collect_time", "collect_time_ms", "favorite_time", "collect_time_str"),
    }


# ---------------------------------------------------------------- 浏览器

CDP_PORT = 9333  # 浏览器远程调试端口，给「点赞/评论/播放」复用同一个登录态


class Browser:
    """一个保存了登录态的真实浏览器窗口。只能在同一个线程里使用。"""

    def __init__(self, preference="auto", log=print, visible=False):
        self.preference = preference
        self.log = log
        self.pw = None
        self.ctx = None
        self.page = None
        self.visible = visible          # 默认不弹窗：窗口放到屏幕外面去，后台跑
        self._launched_visible = None

    def _channels(self):
        p = self.preference
        order = ["chrome", "msedge", "chromium"]
        if p in order:  # 用户指定了优先用的，失败时仍然回退，不至于直接报错
            return [p] + [x for x in order if x != p]
        return order

    def start(self, visible=None):
        if visible is not None:
            self.visible = bool(visible)
        if self.ctx:
            # 浏览器可能被手动关掉过：还挂着旧的 ctx 的话，后面每一条都会报
            # "Target page, context or browser has been closed"，所以先判断一下死活
            alive = False
            try:
                alive = self.page is not None and not self.page.is_closed()
            except Exception:
                alive = False
            if alive and self._launched_visible == self.visible:
                return
            if alive:  # 要切换显示/隐藏：只能重开
                self.close()
            else:
                self.log("浏览器好像被关掉了，重新开一个……")
                self.close()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise DouyinError("缺少 playwright 组件：安装没有完成。请关掉程序，重新运行安装脚本（推荐 Python 3.12），看到「安装完成」再启动")
        from . import pw as _pwmod
        self.pw = _pwmod.get()
        errors = []
        for ch in self._channels():
            try:
                kw = dict(
                    user_data_dir=str(BROWSER_DIR / ch),
                    headless=False,
                    viewport={"width": 1280, "height": 860},
                    locale="zh-CN",
                    args=["--disable-blink-features=AutomationControlled",
                          "--no-first-run", "--no-default-browser-check",
                          # 开着这个端口，别的地方（点赞/评论/取播放地址）能连上同一个浏览器，
                          # 不用再开第二份配置、也不用重复登录
                          f"--remote-debugging-port={CDP_PORT}"],
                    ignore_default_args=["--enable-automation"],
                )
                if not self.visible:
                    # 后台跑：窗口挪到屏幕外面，不挡着你用电脑；要扫码登录时会切回可见
                    kw["args"] = kw["args"] + ["--window-position=-3200,-3200",
                                               "--window-size=1280,860"]
                if ch != "chromium":
                    kw["channel"] = ch
                self.ctx = self.pw.chromium.launch_persistent_context(**kw)
                self._launched_visible = self.visible
                self.ctx.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
                self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
                self.log("后台浏览器已就绪（%s，窗口不显示）" %
                         {'msedge': 'Edge', 'chrome': 'Chrome', 'chromium': '内置 Chromium'}[ch])
                if not self.visible:
                    # 后台模式：窗口已经在屏幕外了，再从任务栏/Alt-Tab 里藏掉，别打扰你
                    try:
                        from . import winfocus
                        for _ in range(8):      # 窗口是异步创建的，多试几次
                            if winfocus.hide_browser_taskbar(CDP_PORT):
                                break
                            time.sleep(0.4)
                    except Exception:
                        pass
                return
            except Exception as e:  # 这个浏览器没装 / 起不来，换下一个
                msg = str(e).replace("\n", " ").strip()
                errors.append(f"{ch}: {msg[:300]}")
        self.close()
        hint = ""
        if any("EPERM" in e or "mkdtemp" in e or "temporary directory" in e for e in errors):
            hint = ("\n提示：临时目录不可写，Playwright 无法启动浏览器。"
                    "可以手动把 TMP / TEMP 环境变量指向一个可写目录（例如程序目录下的 data\\tmp），再重启程序。")
        raise DouyinError("找不到可用的浏览器。请安装 Microsoft Edge 或 Google Chrome，"
                          "或在终端运行 `python -m playwright install chromium`。" + hint + "\n"
                          + "\n".join(errors))

    def close(self):
        for fn in (lambda: self.ctx and self.ctx.close(),):
            try:
                fn()
            except Exception:
                pass
        self.pw = self.ctx = self.page = None
        self._launched_visible = None

    # ---- 登录
    def logged_in(self) -> bool:
        ok = False
        try:
            for c in self.ctx.cookies("https://www.douyin.com"):
                if c["name"] in ("sessionid", "sessionid_ss", "sid_tt") and c.get("value"):
                    ok = True
                    break
        except Exception:
            return False
        try:
            from . import config
            config.set_login("douyin", ok, self.nickname() if ok else None)
        except Exception:
            pass
        return ok

    def nickname(self):
        try:
            return (self.page.evaluate("""() => {
                const el = document.querySelector('[data-e2e="user-info-name"], .user-info-name');
                if (el && el.innerText) return el.innerText.trim();
                const s = window.__INITIAL_STATE__ || {};
                const u = (s.userInfo && s.userInfo.user) || (s.user && s.user.userInfo) || null;
                return (u && (u.nickname || u.name)) || '';
            }""") or "").strip()
        except Exception:
            return ""

    def ensure_login(self, timeout=300, should_stop=lambda: False, visible=False):
        """visible=False（默认）：后台只检查登录态，绝不把窗口弹到用户面前。
        visible=True：只在用户主动点「登录抖音」时用，这时才需要扫码。"""
        self.start(visible=visible)
        if not self.page.url.startswith("https://www.douyin.com"):
            self.page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=60000)
        if self.logged_in():
            return True
        if not visible:
            # 后台自动流程：不弹窗、不干等，交给上层提示用户手动登录
            self.log("抖音登录已失效（后台模式不弹窗），请在界面点「登录抖音」重新扫码")
            return False
        self.log("请在弹出的浏览器窗口里用抖音 App 扫码登录（右上角「登录」）。最多等 5 分钟……"
                 "（如果没看到窗口，检查一下任务栏，可能被其它窗口挡住了）")
        try:
            self.page.bring_to_front()
            btn = self.page.get_by_text("登录", exact=True).first
            btn.click(timeout=5000)
        except Exception:
            pass
        end = time.time() + timeout
        while time.time() < end:
            if should_stop():
                return False
            if self.logged_in():
                self.log("登录成功，登录状态已保存，下次不用再扫码。")
                self.page.wait_for_timeout(1500)
                return True
            self.page.wait_for_timeout(2000)
        raise NotLoggedIn("等了 5 分钟还没登录，已取消。")

    # ---- 单个视频信息
    def fetch_detail(self, aweme_id: str, kind: str = "video") -> dict:
        self.start()
        hits = []

        def on_resp(r):
            if "/aweme/v1/web/aweme/detail" in r.url:
                hits.append(r)

        self.page.on("response", on_resp)
        try:
            self.page.goto(f"https://www.douyin.com/{'note' if kind == 'note' else 'video'}/{aweme_id}",
                           wait_until="domcontentloaded", timeout=60000)
            detail = None
            for _ in range(40):  # 最多等 20 秒
                while hits and detail is None:
                    r = hits.pop(0)
                    try:
                        j = r.json()
                        if j.get("aweme_detail"):
                            detail = j["aweme_detail"]
                    except Exception:
                        pass
                if detail:
                    break
                self.page.wait_for_timeout(500)
        finally:
            self.page.remove_listener("response", on_resp)

        if detail:
            return parse_aweme(detail)

        # 兜底（图文）：只从「这条图文自己的轮播」里拿图。
        # 以前是抓页面上所有大图，结果把旁边推荐流的图也抓进来了，
        # 好几条图文的封面都变成同一张（推荐位那张），这就是封面串图的根因。
        if kind == "note" or "/note/" in self.page.url:
            info = self.page.evaluate("""() => {
                const big = (i) => (i.naturalWidth || 0) >= 400;
                const ok = (i) => /douyinpic|tos-cn|byteimg/.test(i.currentSrc || i.src);
                const pick = (list) => [...new Set(list.filter(i => big(i) && ok(i))
                                        .map(i => i.currentSrc || i.src))];
                let imgs = pick([...document.querySelectorAll('.dySwiperSlide img, [class*="dySwiperSlide"] img')]);
                if (!imgs.length) {
                    imgs = pick([...document.querySelectorAll('img')].filter((i) => {
                        const a = i.closest('a');
                        const href = a ? (a.getAttribute('href') || '') : '';
                        return !/[/](video|note)[/]/.test(href);
                    }));
                }
                const meta = document.querySelector('meta[name="description"]');
                return {imgs, desc: meta ? meta.content : '', title: document.title};
            }""") or {}
            if info.get("imgs"):
                title = re.sub(r"\s*-\s*抖音\s*$", "", info.get("title") or "").strip()
                return {"aweme_id": aweme_id, "title": title or f"抖音图文 {aweme_id}", "desc": info.get("desc") or "",
                        "author": "", "duration": 0, "cover": info["imgs"][0], "play_urls": [], "subtitle_urls": [],
                        "images": [[u] for u in info["imgs"]], "is_ad": False, "is_note": True,
                        "url": f"https://www.douyin.com/note/{aweme_id}"}

        # 兜底：直接从页面的播放器里拿视频地址
        info = self.page.evaluate("""() => {
            const v = document.querySelector('video');
            if (!v) return null;
            const s = [...v.querySelectorAll('source')].map(x => x.src);
            if (v.currentSrc) s.unshift(v.currentSrc);
            return {sources: s, title: document.title};
        }""")
        urls = [u for u in (info or {}).get("sources", []) if u and u.startswith("http")]
        if urls:
            title = re.sub(r"\s*-\s*抖音\s*$", "", (info or {}).get("title") or "").strip()
            return {"aweme_id": aweme_id, "title": title or f"抖音视频 {aweme_id}", "author": "",
                    "duration": 0, "cover": None, "play_urls": list(dict.fromkeys(urls)),
                    "is_ad": False, "is_note": False, "url": f"https://www.douyin.com/video/{aweme_id}"}
        if not self.logged_in():
            raise NotLoggedIn("没读到视频信息，可能需要先登录抖音")
        raise DouyinError("没读到视频信息。可能视频已删除/私密，或者抖音弹了验证码——"
                          "请看一眼弹出的浏览器窗口，完成验证后点「重试」")

    # ---- 字幕
    def fetch_text(self, url) -> str:
        self.start()
        resp = self.ctx.request.get(url, headers={"Referer": "https://www.douyin.com/"}, timeout=30000)
        if not resp.ok:
            raise DouyinError(f"字幕下载失败 HTTP {resp.status}")
        return resp.body().decode("utf-8", "ignore")

    # ---- 图文图片
    def download_images(self, images, dest_dir: Path, referer="https://www.douyin.com/"):
        """images 是 [[候选地址...], ...]，返回保存好的文件路径列表（按顺序）。"""
        self.start()
        dest_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for n, cands in enumerate(images, 1):
            for u in cands:
                if not _usable_img(u):
                    continue
                try:
                    resp = self.ctx.request.get(u, headers={"Referer": referer}, timeout=60000)
                    if not resp.ok:
                        continue
                    body = resp.body()
                    if len(body) < 2048:
                        continue
                    ctype = (resp.headers.get("content-type") or "").lower()
                    ext = (".webp" if "webp" in ctype else ".png" if "png" in ctype else
                           ".heic" if "heic" in ctype else ".jpg")
                    f = dest_dir / f"{n:02d}{ext}"
                    f.write_bytes(body)
                    saved.append(f)
                    break
                except Exception:
                    continue
            time.sleep(0.3)
        if not saved:
            raise DouyinError("图文的图片都下载失败了")
        return saved

    # ---- 下载
    def download(self, urls, dest: Path) -> Path:
        self.start()
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(dest.suffix + ".part")
        last = "没有可用的视频地址"
        for u in urls:
            try:
                resp = self.ctx.request.get(u, headers={"Referer": "https://www.douyin.com/"},
                                            timeout=180000)
                if not resp.ok:
                    last = f"HTTP {resp.status}"
                    continue
                body = resp.body()
                if len(body) < 10 * 1024:  # 抖音 CDN 出错时返回的是几 KB 的错误页
                    last = "下载到的文件太小，可能是错误页"
                    continue
                part.write_bytes(body)
                part.replace(dest)
                return dest
            except Exception as e:
                last = str(e).splitlines()[0][:150]
        raise DouyinError(f"视频下载失败：{last}")

    # ---- 收藏夹 / 喜欢
    def sync_list(self, kind="collection", limit=0, on_item=lambda d: None, should_stop=lambda: False):
        """kind = collection（收藏）或 like（喜欢）。返回读到的条数。

        limit = 0 表示不设上限，一直读到列表到底（has_more 为 false）为止。
        """
        cap = limit if limit and limit > 0 else 10 ** 9
        if not self.ensure_login(should_stop=should_stop):
            raise NotLoggedIn("抖音登录已失效，请在界面点「登录抖音」重新扫码")
        if kind == "like":
            tab_url, tab_text = "https://www.douyin.com/user/self?showTab=like", "喜欢"
            match = lambda u: "/aweme/v1/web/aweme/favorite" in u
        else:
            tab_url = ("https://www.douyin.com/user/self?from_tab_name=main"
                       "&showSubTab=video&showTab=favorite_collection")
            tab_text = "收藏"
            match = lambda u: "/aweme/v1/web/" in u and "collect" in u
        hits = []

        def on_resp(r):
            if match(r.url):
                hits.append(r)

        self.page.on("response", on_resp)
        seen = set()
        try:
            self.page.goto(tab_url, wait_until="domcontentloaded", timeout=60000)
            self.page.wait_for_timeout(3000)
            if not hits:
                try:
                    self.page.get_by_text(tab_text, exact=True).first.click(timeout=5000)
                except Exception:
                    pass
            idle, has_more = 0, True
            while len(seen) < cap and idle < 6 and has_more:
                if should_stop():
                    break
                self.page.wait_for_timeout(random.randint(1200, 2200))  # 慢一点，别被风控
                new = 0
                while hits:
                    r = hits.pop(0)
                    try:
                        j = r.json()
                    except Exception:
                        continue
                    lst = j.get("aweme_list")
                    if lst is None:
                        continue
                    if j.get("has_more") in (0, False):
                        has_more = False
                    for a in lst:
                        d = parse_aweme(a)
                        if d["aweme_id"] and d["aweme_id"] not in seen and len(seen) < cap:
                            seen.add(d["aweme_id"])
                            new += 1
                            on_item(d)
                idle = 0 if new else idle + 1
                try:
                    self.page.mouse.move(640, 560)
                    self.page.mouse.wheel(0, random.randint(1800, 2800))
                except Exception:
                    pass
            if not seen:
                raise DouyinError(f"没读到「{tab_text}」列表。请看一眼浏览器窗口：是否需要验证，"
                                  f"或者{tab_text}列表是否为空。")
            return len(seen)
        finally:
            self.page.remove_listener("response", on_resp)
