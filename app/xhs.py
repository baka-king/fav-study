"""小红书（RED）：登录、同步收藏、解析笔记、下载视频/图片。

和抖音那套是并列的模块：
- 浏览器用独立配置目录 data/browser/xhs，登录态互不影响
- 解析靠页面里的 window.__INITIAL_STATE__，拿不到时退回 DOM（og:video / video 标签）
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .config import BROWSER_DIR

HOME = "https://www.xiaohongshu.com"
CDP_PORT = 9334
PROFILE_DIR = BROWSER_DIR / "xhs"


class XhsError(Exception):
    def __init__(self, msg, retry=False):
        super().__init__(msg)
        self.retry = retry


class NotLoggedIn(XhsError):
    pass


def note_id_from_url(url):
    """从链接里抠出笔记 id（24 位十六进制）。"""
    u = (url or "").strip()
    m = re.search(r"/(?:explore|discovery/item|item)/([0-9a-f]{24})", u)
    if m:
        return m.group(1)
    m = re.search(r"([0-9a-f]{24})", u)
    return m.group(1) if m else None


def expand_short_url(url, timeout=15):
    """xhslink.com 的短链要跟一次跳转才拿得到真地址。"""
    u = (url or "").strip()
    if "xhslink.com" not in u:
        return u
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.geturl()
    except Exception:
        return u


# ---------------------------------------------------------------- 解析页面数据

_JS_STATE = """() => {
  try {
    if (window.__INITIAL_STATE__) return JSON.stringify(window.__INITIAL_STATE__);
  } catch (e) {}
  return null;
}"""


def _walk_find(obj, keys, depth=0):
    """在 JSON 里找第一个同时带 keys 字段的 dict。"""
    if depth > 8:
        return None
    if isinstance(obj, dict):
        if all(k in obj for k in keys):
            return obj
        for v in obj.values():
            got = _walk_find(v, keys, depth + 1)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for v in obj[:30]:
            got = _walk_find(v, keys, depth + 1)
            if got is not None:
                return got
    return None


def _first_video_url(video):
    if not isinstance(video, dict):
        return None
    for key in ("url", "masterUrl", "master_url", "backupUrls", "backup_urls"):
        v = video.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v
        if isinstance(v, list):
            for x in v:
                if isinstance(x, str) and x.startswith("http"):
                    return x
    media = video.get("media") or {}
    if isinstance(media, dict):
        stream = media.get("stream") or {}
        if isinstance(stream, dict):
            for lst in stream.values():
                if isinstance(lst, list):
                    for item in lst:
                        if isinstance(item, dict):
                            u = item.get("masterUrl") or item.get("master_url")
                            if isinstance(u, str) and u.startswith("http"):
                                return u
    return None


def _cover_of(card):
    """从收藏接口的 note_card 里取封面地址（兼容几种字段写法）。"""
    cov = (card.get("cover") or {})
    if isinstance(cov, str):
        return cov if cov.startswith("http") else ""
    for k in ("url_default", "urlDefault", "url", "url_pre", "urlPre"):
        v = cov.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
    for info in (cov.get("info_list") or []):
        if isinstance(info, dict):
            u = info.get("url") or info.get("url_default")
            if isinstance(u, str) and u.startswith("http"):
                return u
    return ""


def _note_from_state(state):
    """从 __INITIAL_STATE__ 里找出笔记的 {title, desc, author, video, images, cover}。"""
    node = None
    for keys in (("noteId", "title"), ("noteId", "desc"), ("note_id", "title")):
        node = _walk_find(state, keys)
        if node:
            break
    if not node:
        return None
    title = str(node.get("title") or "").strip()
    desc = str(node.get("desc") or "").strip()
    user = node.get("user") or {}
    author = str(user.get("nickname") or user.get("name") or "").strip()
    video = node.get("video") or {}
    vurl = _first_video_url(video)
    cover = ""
    imgs = []
    for im in (node.get("imageList") or node.get("images") or []):
        if isinstance(im, dict):
            u = im.get("urlDefault") or im.get("url") or im.get("urlPre")
            if isinstance(u, str) and "/avatar/" not in u:
                imgs.append(u)
    if imgs:
        cover = imgs[0]
    if not cover:
        cov = (node.get("cover") or {})
        if isinstance(cov, dict):
            cover = cov.get("urlDefault") or cov.get("url") or ""
            if "/avatar/" in (cover or ""):
                cover = ""
    duration = 0
    if isinstance(video, dict):
        try:
            duration = int((video.get("capa") or {}).get("duration") or 0)
        except Exception:
            duration = 0
    return {"title": title, "desc": desc, "author": author, "video_url": vurl,
            "images": imgs, "cover": cover, "duration": duration}


class Browser:
    """小红书用的浏览器（独立登录态）。"""

    def __init__(self, log=print, visible=False):
        self.log = log
        self.visible = visible
        self.pw = None
        self.ctx = None
        self.page = None

    def start(self, visible=None):
        if visible is not None:
            self.visible = bool(visible)
        if self.ctx:
            try:
                if self.page and not self.page.is_closed() and self._visible == self.visible:
                    return
            except Exception:
                pass
            self.close()
        from playwright.sync_api import sync_playwright
        if not PROFILE_DIR.exists():
            PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        from . import pw as _pwmod
        self.pw = _pwmod.get()
        args = ["--disable-blink-features=AutomationControlled",
                "--no-first-run", "--no-default-browser-check",
                "--no-proxy-server",
                f"--remote-debugging-port={CDP_PORT}"]
        if not self.visible:
            args += ["--window-position=-3200,-3200", "--window-size=1280,860"]
        else:
            args += ["--window-position=140,90", "--window-size=1200,880"]
        last = None
        for ch in ("chrome", "msedge"):
            try:
                self.ctx = self.pw.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR), headless=False, channel=ch,
                    viewport={"width": 1280, "height": 860}, locale="zh-CN", args=args,
                    ignore_default_args=["--enable-automation"])
                break
            except Exception as e:
                last = str(e)[:120]
        if not self.ctx:
            pass
            raise XhsError(f"打不开浏览器：{last}")
        self._visible = self.visible
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.host = "www.xiaohongshu.com"
        try:
            if not (self.page.url or "").startswith("http"):
                self.page.goto(HOME, wait_until="domcontentloaded", timeout=45000)
                self.page.wait_for_timeout(800)
            u = urllib.parse.urlparse(self.page.url or "")
            if u.hostname and ("xiaohongshu" in u.hostname or "rednote" in u.hostname):
                self.host = u.hostname
        except Exception:
            pass
        self.log(f"已打开小红书浏览器（{self.host}）")
        if not self.visible:
            try:
                from . import winfocus
                for _ in range(6):
                    if winfocus.hide_browser_taskbar(CDP_PORT):
                        break
                    time.sleep(0.4)
            except Exception:
                pass

    def close(self):
        for fn in (lambda: self.ctx and self.ctx.close(),):
            try:
                fn()
            except Exception:
                pass
        self.pw = self.ctx = self.page = None

    def logged_in(self):
        """看 Cookie：登录后才会有像样的 web_session。

        之前要求页面 __INITIAL_STATE__ 里必须有 userId，可首页/探索页根本没有这个字段，
        明明登录了也会被判成「没登录」，所以这里以 Cookie 为准。
        """
        try:
            names = []
            for c in self.ctx.cookies(f"https://{self.host}"):
                v = str(c.get("value") or "")
                names.append(c.get("name"))
                if c.get("name") == "web_session" and len(v) > 20:
                    try:
                        from . import config
                        config.set_login("xhs", True)
                    except Exception:
                        pass
                    return True
            self.log("小红书没有登录 Cookie：" + ",".join(str(n) for n in names if n)[:160])
        except Exception as e:
            self.log(f"读取小红书登录状态失败：{e}")
            return False
        try:
            from . import config
            config.set_login("xhs", False)
        except Exception:
            pass
        return False

    def save_qr(self, path):
        """把登录二维码存成图片，给界面上那个小窗口显示。"""
        sels = ['.qrcode img', '[class*="qrcode"] img', '[class*="qrcode"]',
                'img[src^="data:image"]', '[class*="login"] img']
        for sel in sels:
            try:
                el = self.page.locator(sel).first
                if el.count() and el.is_visible():
                    box = el.bounding_box()
                    if box and box.get("width", 0) > 100:
                        el.screenshot(path=str(path))
                        return True
            except Exception:
                continue
        return False

    def ensure_login(self, timeout=300, should_stop=lambda: False, qr_path=None):
        self.start(visible=True)
        if not any(h in (self.page.url or "") for h in ("xiaohongshu.com", "rednote.com")):
            self.page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
        if self.logged_in():
            return True
        # 把登录二维码点出来：首页不点登录是不会弹二维码的
        for sel in ("button:has-text(\"登录\")", "text=\"登录\"", ".login-btn"):
            try:
                el = self.page.locator(sel).first
                if el.count() and el.is_visible():
                    el.click(timeout=2500)
                    self.page.wait_for_timeout(1200)
                    break
            except Exception:
                continue
        self.log("请在弹出的浏览器窗口里扫码登录小红书（最多等 5 分钟）……")
        end = time.time() + timeout
        while time.time() < end:
            if should_stop():
                return False
            try:
                if self.page is None or self.page.is_closed():
                    self.start(visible=True)
            except Exception:
                self.start(visible=True)
            if qr_path:
                try:
                    self.save_qr(qr_path)
                except Exception:
                    pass
            if self.logged_in():
                self.log("小红书登录成功，登录状态已保存。")
                try:
                    self.page.wait_for_timeout(1200)
                except Exception:
                    pass
                return True
            try:
                self.page.wait_for_timeout(2000)
            except Exception:
                time.sleep(2)
                try:
                    self.start(visible=True)
                except Exception:
                    pass
        raise NotLoggedIn("等了 5 分钟还没登录小红书")

    # ---- 解析单条笔记
    def fetch_note(self, note_id, url=None, token=None):
        self.start()
        url = url or f"https://{self.host}/explore/{note_id}"
        if token and "xsec_token" not in url:
            url += ("?" if "?" not in url else "&") + f"xsec_token={token}&xsec_source=pc_collect"
        self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        self.page.wait_for_timeout(2500)
        state_raw = None
        try:
            state_raw = self.page.evaluate(_JS_STATE)
        except Exception:
            state_raw = None
        info = None
        if state_raw:
            try:
                info = _note_from_state(json.loads(state_raw))
            except Exception:
                info = None
        if not info or not (info.get("video_url") or info.get("images")):
            # 兜底：直接从页面拿
            try:
                dom = self.page.evaluate("""() => {
                    const v = document.querySelector('video');
                    const og = document.querySelector('meta[property="og:video"]');
                    const imgs = [...document.querySelectorAll('img')]
                        .map(i => i.currentSrc || i.src)
                        .filter(u => /xhscdn|sns-img|sns-webpic/.test(u));
                    return {video: (v && (v.currentSrc || v.src)) || (og && og.content) || '',
                            title: document.title || '', imgs: [...new Set(imgs)].slice(0, 12)};
                }""") or {}
            except Exception:
                dom = {}
            info = {
                "title": re.sub(r"\s*-\s*小红书\s*$", "", (dom.get("title") or "")).strip(),
                "desc": "", "author": "",
                "video_url": (dom.get("video") or "").strip() or None,
                "images": dom.get("imgs") or [],
                "cover": (dom.get("imgs") or [""])[0], "duration": 0,
            }
        if not info:
            raise XhsError("解析失败：小红书这条没读到内容（可能需要登录，或者笔记已删除）")
        info["url"] = url
        info["note_id"] = note_id
        info["is_note"] = not bool(info.get("video_url"))
        return info

    def download(self, url, dest: Path):
        self.start()
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(dest.suffix + ".part")
        headers = {"User-Agent": "Mozilla/5.0", "Referer": HOME + "/"}
        try:
            resp = self.ctx.request.get(url, headers=headers, timeout=180000)
            if not resp.ok:
                raise XhsError(f"下载失败：HTTP {resp.status}")
            body = resp.body()
            if len(body) < 20 * 1024:
                raise XhsError("下载到的文件太小，可能是错误页")
            part.write_bytes(body)
            part.replace(dest)
            return dest
        except XhsError:
            raise
        except Exception as e:
            raise XhsError(f"下载失败：{str(e)[:120]}")

    # ---- 同步收藏
    def download_images(self, images, dest_dir):
        """images 是 [[候选地址...], ...]，返回保存好的文件路径列表。"""
        self.start()
        dest_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for n, cands in enumerate(images, 1):
            for u in cands:
                if not u or not str(u).startswith("http"):
                    continue
                try:
                    resp = self.page.request.get(u, headers={"Referer": "https://www.xiaohongshu.com/"}, timeout=60000)
                    if not resp.ok:
                        continue
                    body = resp.body()
                    if len(body) < 2048:
                        continue
                    ctype = (resp.headers.get("content-type") or "").lower()
                    ext = ".webp" if "webp" in ctype else ".png" if "png" in ctype else ".jpg"
                    f = dest_dir / f"{n:02d}{ext}"
                    f.write_bytes(body)
                    saved.append(f)
                    break
                except Exception:
                    continue
        return saved

    def current_uid(self):
        """拿不到 userId 时多试几种：页面状态 → 我 的链接 → /user/profile 跳转。"""
        try:
            raw = self.page.evaluate(_JS_STATE)
            st = json.loads(raw) if raw else {}
        except Exception:
            st = {}
        if st:
            node = (_walk_find(st, ("userId", "nickname"), depth=8)
                    or _walk_find(st, ("userId",), depth=8)
                    or _walk_find(st, ("redId",), depth=8))
            if node:
                for k in ("userId", "redId"):
                    v = node.get(k)
                    if v:
                        return str(v)
        # 页面上的「我」链接
        try:
            href = self.page.evaluate(
                """() => {
                  const a = document.querySelector('a[href*="/user/profile/"]');
                  return a ? a.getAttribute('href') : null;
                }""")
            if href:
                import re
                m = re.search(r"/user/profile/([0-9a-zA-Z]+)", href)
                if m and m.group(1) not in ("me", "self"):
                    return m.group(1)
        except Exception:
            pass
        return None

    def sync_favorites(self, limit=0, on_item=lambda d: None, should_stop=lambda: False):
        self.start()
        if not any(h in (self.page.url or "") for h in ("xiaohongshu.com", "rednote.com")):
            self.page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
            self.page.wait_for_timeout(2000)
        if not self.logged_in():
            raise NotLoggedIn("还没登录小红书")
        uid = self.current_uid()
        if not uid:
            raise XhsError("没找到你的小红书用户 id（可能是页面结构变了）")

        seen, n = set(), 0
        bag = {"done": False}

        def handle(resp):
            nonlocal n
            if "/api/sns/web/v2/user/me" in resp.url:
                try:
                    me = (resp.json() or {}).get("data") or {}
                    nick = me.get("nickname") or (me.get("user") or {}).get("nickname")
                    if nick:
                        from . import config as _cfg
                        _cfg.set_login("xhs", True, nick)
                except Exception:
                    pass
                return
            if bag["done"] or "/api/sns/web/v2/note/collect/page" not in resp.url:
                return
            try:
                if resp.status != 200:
                    return
                data = resp.json()
            except Exception:
                return
            notes = ((data or {}).get("data") or {}).get("notes") or []
            for note in notes:
                nid = str(note.get("note_id") or "")
                if not nid or nid in seen:
                    continue
                seen.add(nid)
                token = note.get("xsec_token") or ""
                card = note.get("note_card") or {}
                src = card if card else note          # 接口把字段放在 note 上
                cover = ""
                try:
                    cover = _cover_of(src)
                except Exception:
                    cover = ""
                title = (src.get("display_title") or src.get("title") or "").strip()
                typ = src.get("type") or ""
                cb = src.get("time") or 0
                author = ""
                try:
                    u = src.get("user") or {}
                    author = (u.get("nickname") or u.get("nick_name") or "").strip()
                except Exception:
                    author = ""
                on_item({"note_id": nid, "url": f"{HOME}/explore/{nid}",
                         "token": token, "title": title, "cover": cover, "author": author,
                         "type": typ, "published_at": cb})
                n += 1
                if limit and n >= limit:
                    bag["done"] = True
                    return

        self.page.on("response", handle)
        try:
            self.page.goto(f"https://{self.host}/user/profile/{uid}?tab=fav",
                           wait_until="domcontentloaded", timeout=60000)
            self.page.wait_for_timeout(2500)
            deadline = time.time() + 240
            for _ in range(120):
                if should_stop() or bag["done"] or time.time() > deadline:
                    break
                self.page.mouse.wheel(0, 1800)
                self.page.wait_for_timeout(1200)
                if limit and n >= limit:
                    break
        finally:
            try:
                self.page.remove_listener("response", handle)
            except Exception:
                pass
        return n


def resolve_video_url(note_id, log=print, url=None):
    """只取视频直链：优先连后台已经开着的浏览器，连不上再自己开一个。"""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    ctx = None
    own = False
    try:
        try:
            br = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
            if br.contexts:
                ctx = br.contexts[0]
        except Exception:
            ctx = None
        if ctx is None:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR), headless=False,
                viewport={"width": 1280, "height": 860}, locale="zh-CN",
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled", "--no-first-run",
                      "--window-position=-3200,-3200", "--window-size=1280,860"],
                ignore_default_args=["--enable-automation"])
            own = True
        page = ctx.new_page()
        try:
            page.goto(url or f"{HOME}/explore/{note_id}", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
            raw = page.evaluate("""() => {
                try { if (window.__INITIAL_STATE__) return JSON.stringify(window.__INITIAL_STATE__); } catch(e) {}
                const v = document.querySelector('video');
                return v ? JSON.stringify({__dom: v.currentSrc || v.src}) : null;
            }""")
            if raw:
                data = json.loads(raw)
                if isinstance(data, dict) and data.get("__dom"):
                    u = data["__dom"]
                    return u if isinstance(u, str) and u.startswith("http") else None
                info = _note_from_state(data)
                if info and info.get("video_url"):
                    return info["video_url"]
        finally:
            try:
                page.close()
            except Exception:
                pass
    except Exception as e:
        log(f"小红书取视频地址失败：{str(e)[:100]}")
        return None
    finally:
        try:
            if own and ctx:
                ctx.close()
        except Exception:
            pass
        try:
            pw.stop()
        except Exception:
            pass
    return None
