/* 收藏变笔记 前端（原生 JS，不需要编译） */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const view = $("#view");

/* ---------------------------------------------------------------- 线条图标（Lucide 风格，ISC 开源协议） */
const ICONS = {
  zap: '<path d="M13 2 4.5 13.5H11l-1 8.5L19.5 10H13z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
  arrowUp: '<path d="M12 19V5"/><path d="m5 12 7-7 7 7"/>',
  shuffle: '<path d="M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l6.1-8.6c.7-1.1 2-1.7 3.3-1.7H22"/><path d="m18 2 4 4-4 4"/><path d="M2 6h1.9c1.5 0 2.9.9 3.6 2.2"/><path d="M22 18h-5.9c-1.3 0-2.6-.7-3.3-1.8l-.5-.8"/><path d="m18 14 4 4-4 4"/>',
  copy: '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
  external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  play: '<path d="M6 3.5v17a1 1 0 0 0 1.5.86l14-8.5a1 1 0 0 0 0-1.72l-14-8.5A1 1 0 0 0 6 3.5z" fill="currentColor" stroke="none"/>',
  star: '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"/>',
  starFill: '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z" fill="currentColor"/>',
  bulb: '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
  eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  coffee: '<path d="M10 2v2"/><path d="M14 2v2"/><path d="M6 2v2"/><path d="M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1"/>',
  cap: '<path d="M21.42 10.92a1 1 0 0 0-.02-1.84L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.83l8.57 3.91a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
  book: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  retry: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  checkCircle: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
  xCircle: '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
  trophy: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>',
  folder: '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>',
  sparkles: '<path d="M9.94 15.5A2 2 0 0 0 8.5 14.06l-6.14-1.58a.5.5 0 0 1 0-.96L8.5 9.94A2 2 0 0 0 9.94 8.5l1.58-6.14a.5.5 0 0 1 .96 0L14.06 8.5A2 2 0 0 0 15.5 9.94l6.14 1.58a.5.5 0 0 1 0 .96L15.5 14.06a2 2 0 0 0-1.44 1.44l-1.58 6.14a.5.5 0 0 1-.96 0z"/>',
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  heart: '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l8.84 8.84 8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
};
const ico = (name, cls = "ic") => `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;

/* ---------------------------------------------------------------- 分类配色（Radix Colors 色阶） */
const CAT_PALETTE = ["blue", "orange", "violet", "pink", "green", "indigo", "amber", "teal", "cyan", "red"];
const CAT_FIXED = {
  "AI 工具推荐": "blue", "提示词技巧": "orange", "AI 编程": "violet", "AI 绘画与视频": "pink", "AI 办公效率": "green",
  "大模型与行业资讯": "indigo", "AI 副业与变现": "amber", "AI 学习方法": "teal", "其他": "gray", "未分类": "gray",
};
function catColor(name) {
  name = name || "其他";
  if (CAT_FIXED[name]) return CAT_FIXED[name];
  let h = 0; for (const ch of name) h = (h * 31 + ch.codePointAt(0)) >>> 0;
  return CAT_PALETTE[h % CAT_PALETTE.length];
}
// 抖音图床偶尔会拒掉浏览器直连（签名过期/被拦）：失败一次就走本机代理再试
/* 本地笔记图片会被修复/替换，带上条目更新时间做版本号，防止浏览器缓存旧图 */
function coverUrl(it) {
  const c = (it && it.cover) || "";
  if (!c) return "";
  if (c.startsWith("/files/")) {
    const v = Math.floor((it.updated_at || it.created_at || 0) * 1000);
    return c + (c.includes("?") ? "&" : "?") + "v=" + v;
  }
  // 远端封面走本机代理：小红书的图带签名，过期就 403；抖音图床也会拦跨域
  if (/^https?:/i.test(c)) return "/api/img?u=" + encodeURIComponent(c);
  return c;
}
window.coverUrl = coverUrl;

/* 粘贴文稿：把一段文字直接变成一条笔记（走同样的精读流程） */
function openPasteDoc() {
  if (document.getElementById("pasteModal")) return;
  const d = document.createElement("div");
  d.className = "modal"; d.id = "pasteModal";
  d.innerHTML = `<div class="modal-card" style="width:min(780px,100%)">
    <div class="modal-head"><h2>粘贴文稿</h2><button class="icon" data-close>✕</button></div>
    <div class="body" style="padding:0 24px">
      <div class="field"><label>标题</label><input id="pdTitle" placeholder="给这份文稿起个名字（可不填）"></div>
      <div class="field" style="margin-top:12px"><label>正文</label>
        <textarea id="pdText" rows="12" placeholder="把公众号 / 文档 / 聊天记录里的文字粘进来，至少 50 字"></textarea></div>
    </div>
    <div class="modal-foot"><span class="muted small">会当成一条收藏，直接进学习库</span><span class="spacer"></span>
      <button class="btn" data-close>取消</button><button class="btn primary" id="pdOk">保存</button></div>
  </div>`;
  document.body.appendChild(d);
  const close = () => d.remove();
  d.querySelectorAll("[data-close]").forEach((b) => b.onclick = close);
  d.onclick = (e) => { if (e.target === d) close(); };
  $("#pdOk").onclick = async () => {
    const text = $("#pdText").value.trim();
    if (text.length < 50) return toast("文稿太短了，至少 50 个字");
    $("#pdOk").disabled = true;
    try {
      const r = await api("/api/paste", { text, title: $("#pdTitle").value.trim() });
      close();
      toast("已保存，正在生成笔记");
      await refreshState();
      if (r && r.id) location.hash = "#/item/" + r.id;
    } catch (e) {
      toast(e.message, 5000);
      $("#pdOk").disabled = false;
    }
  };
  setTimeout(() => $("#pdText").focus(), 60);
}
window.openPasteDoc = openPasteDoc;

function imgFallback(el) {
  if (el.dataset.fb) { el.remove(); return; }
  el.dataset.fb = "1";
  el.src = "/api/img?u=" + encodeURIComponent(el.src);
}
window.imgFallback = imgFallback;

const catChip = (name, extra = "") => `<span class="chip cat cat-${catColor(name)} ${extra}">${esc(name || "其他")}</span>`;

const STATUS = {
  queued: ["排队中", "gray"], fetching: ["读取信息", "teal"], downloading: ["下载中", "teal"],
  transcribing: ["转文字中", "teal"], extracting: ["AI 提炼中", "teal"], done: ["已完成", "teal"],
  retry_wait: ["等待重试", "warn"],
  need_key: ["待提炼", "warn"], irrelevant: ["主题无关", "gray"], skipped: ["已跳过", "gray"], failed: ["失败", "bad"],
};
const ACTIVE = ["queued", "retry_wait", "fetching", "downloading", "transcribing", "extracting"];
/* 已完成列表排序：desc = 最新完成在前（默认），asc = 最早完成在前 */
let doneSort = localStorage.getItem("doneSort") || "desc";

/* ---------------------------------------------------------------- 外观主题 */
function applyTheme(name) {
  const root = document.documentElement;
  if (!name || name === "auto") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", name);
  try { localStorage.setItem("theme", name || "auto"); } catch (e) {}
}
(() => {
  const q = new URLSearchParams(location.search).get("theme");
  applyTheme(q || localStorage.getItem("theme") || "auto");
})();
/* 侧边栏的小圆钮：循环切换 跟随系统 → 浅色 → 纯白 → 深色 */
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("themeBtn");
  if (!btn) return;
  const order = ["auto", "light", "white", "dark"];
  btn.onclick = () => {
    const cur = localStorage.getItem("theme") || "auto";
    const next = order[(order.indexOf(cur) + 1) % order.length];
    applyTheme(next);
    const name = { auto: "跟随系统", light: "浅色", white: "纯白", dark: "深色" }[next];
    if (window.toast) toast("外观：" + name);
  };
});

let STATE = null;
let libFilter = { q: "", learned: "", starred: "", category: "" };
let favFilter = { q: "", category: "", sub: "", dur: "", stage: "", sort: "new", platform: "", since: "", scope: "" };
let favView = localStorage.getItem("favView") || "grid";   // grid | list
let wasClassifyBusy = false;
let favItems = [];

/* ---------------------------------------------------------------- 原视频：播放 / 点赞 / 收藏 / 评论 */
let dyItem = null;

function closeDyModals() {
  ["#playModal", "#cmtModal"].forEach((s) => { const m = $(s); if (m) m.hidden = true; });
  const v = $("#playVideo");
  if (v) { try { v.muted = false; if (!v.volume) v.volume = 1; } catch (e) {} }
  if (v) { try { v.pause(); } catch (e) {} v.removeAttribute("src"); try { v.load(); } catch (e) {} v.hidden = true; }
  stopDanmaku();
}

/* ---------------------------------------------------------------- 上一个 / 下一个 */
let navLoading = null;
let entryHash = "";
function navListNow() {
  return (favItems && favItems.length ? favItems : lastItems) || [];
}
async function ensureNavList() {
  if (navListNow().length) return navListNow();
  if (!navLoading) {
    navLoading = api("/api/items?status=all&limit=2000").then((r) => { lastItems = r || []; navLoading = null; return lastItems; })
      .catch(() => { navLoading = null; return []; });
  }
  return navLoading;
}
async function stepItem(dir) {
  const list = await ensureNavList();
  if (!list.length) return;
  const open = !$("#playModal").hidden;
  const cur = open ? dyItem : (route().name === "item" ? route().id : null);
  let i = list.findIndex((x) => x.id === cur);
  if (i < 0) i = 0;
  const it = list[(i + dir + list.length) % list.length];
  if (!it) return;
  if (open) openPlayer(it.id, it.note_title || it.title || "", it.aweme_id || "");
  else location.hash = `#/item/${it.id}`;
}

function warmNeighbors(currentId) {
  const list = navListNow();
  const i = list.findIndex((x) => x.id === currentId);
  if (i < 0) return;
  [list[i + 1], list[i - 1]].forEach((it) => {
    if (!it || !it.aweme_id || (it.platform || "douyin") === "xhs") return;
    fetch(`/api/items/${it.id}/warm`).catch(() => {});
  });
}

function openPlayer(id, title = "", aweme = "") {
  dyItem = id;
  warmNeighbors(id);
  $("#playTitle").textContent = (title || "原视频").slice(0, 60);
  $("#playModal").hidden = false;
  switchToProxy(id);
  $("#dmToggle").onclick = () => showDanmaku(id);
}



let dmRaf = null;

function stopDanmaku() {
  if (dmRaf) cancelAnimationFrame(dmRaf);
  dmRaf = null;
  const l = $("#dmLayer");
  if (l) l.innerHTML = "";
}

function startDanmaku(video, list) {
  stopDanmaku();
  const layer = $("#dmLayer");
  if (!layer) return;
  let i = 0;
  const tick = () => {
    const t = video.currentTime;
    while (i < list.length && list[i].t <= t) {
      if (t - list[i].t < 3) {
        const d = document.createElement("div");
        d.className = "dm";
        d.textContent = list[i].text;
        d.style.top = (Math.random() * 62 + 6).toFixed(0) + "%";
        d.style.animationDuration = (6 + Math.random() * 3).toFixed(1) + "s";
        layer.appendChild(d);
        setTimeout(() => d.remove(), 9500);
      }
      i++;
    }
    dmRaf = requestAnimationFrame(tick);
  };
  tick();
}

async function showDanmaku(id) {
  const v = $("#playVideo");
  switchToProxy(id);
  $("#playHint").textContent = "正在去抖音取弹幕…";
  try {
    const r = await api(`/api/items/${id}/danmaku`);
    const list = r.items || [];
    if (!list.length) {
      $("#playHint").textContent = "这条在抖音那边没有弹幕（要么没人发，要么视频不公开）。";
      return;
    }
    $("#playHint").textContent = `弹幕 ${list.length} 条 · 跟着下面这个播放器走`;
    startDanmaku(v, list);
  } catch (e) {
    $("#playHint").textContent = "取弹幕失败：" + e.message;
  }
}

function switchToProxy(id) {
  const v = $("#playVideo");
  v.hidden = false;
  v.src = `/api/items/${id}/video`;
  v.play().catch(() => {});
  $("#playHint").textContent = "本地播放器（走代理，第一次要等几秒）。";
}

function openComment(id, title = "") {
  dyItem = id;
  $("#cmtWhere").textContent = title ? `评论到：${title.slice(0, 60)}` : "";
  $("#cmtModal").hidden = false;
  setTimeout(() => $("#cmtText").focus(), 60);
}

async function dyAct(action, text = "") {
  if (!dyItem) return;
  const started = Date.now();
  try { await api(`/api/items/${dyItem}/dy`, { action, text }); }
  catch (e) { return toast(e.message, 5000); }
  toast(action === "comment" ? "正在发评论…" : "正在抖音里操作…");
  while (Date.now() - started < 45000) {
    await new Promise((r) => setTimeout(r, 1200));
    await refreshState();
    const d = STATE.dy || {};
    if (!d.busy && (d.finished_at || 0) * 1000 > started) {
      if (d.error) return toast("没成功：" + d.error, 8000);
      return toast(d.last || "完成");
    }
  }
  toast("还在处理，稍等一会儿再看", 5000);
}

document.addEventListener("click", (e) => {
  const b = e.target.closest && e.target.closest("[data-play]");
  if (b) { e.preventDefault(); e.stopPropagation(); openPlayer(+b.dataset.play, b.dataset.title || "", b.dataset.aweme || ""); return; }
  const nv = e.target.closest && e.target.closest(".pm-nav[data-step]");
  if (nv) { e.preventDefault(); e.stopPropagation(); stepItem(nv.dataset.step === "prev" ? -1 : 1); return; }
  const c = e.target.closest && e.target.closest("#playModal [data-close], #cmtModal [data-close]");
  if (c) { closeDyModals(); }
  const d = e.target.closest && e.target.closest("#dupModal [data-close]");
  if (d) { $("#dupModal").hidden = true; }
});
document.addEventListener("keydown", (e) => {
  const tag = (e.target && e.target.tagName) || "";
  const typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
  const open = !$("#playModal").hidden || !$("#cmtModal").hidden;
  const onItem = route().name === "item";
  if (e.key === "Escape") {
    if (open) { closeDyModals(); e.preventDefault(); return; }
    if (onItem) {
      e.preventDefault();
      location.hash = entryHash || (favFilter.platform ? `#/favs/p/${favFilter.platform}` : "#/favs");
    }
    return;
  }
  if (typing) return;
  if (!open && !onItem) return;
  if (e.key === "ArrowUp" || e.key === "ArrowDown") {
    e.preventDefault();
    stepItem(e.key === "ArrowUp" ? -1 : 1);
  }
});
let procTab = "active";
let lastItems = [];

async function api(path, body) {
  const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || `请求失败 ${r.status}`);
  return j;
}

function toast(msg, ms = 2600) {
  const t = $("#toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), ms);
}

const fmtDur = (s) => { s = Math.round(s || 0); return s ? `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}` : ""; };
const fmtTime = (t) => new Date(t * 1000).toLocaleTimeString("zh-CN", { hour12: false });
const fmtBytes = (n) => {
  n = n || 0;
  if (n >= 1024 ** 3) return (n / 1024 ** 3).toFixed(2) + " GB";
  if (n >= 1024 ** 2) return (n / 1024 ** 2).toFixed(1) + " MB";
  if (n >= 1024) return (n / 1024).toFixed(0) + " KB";
  return n + " B";
};

/* ---------------------------------------------------------------- 状态轮询 */
/* 收藏库分类折叠（记住选择） */
function favFolded() { return localStorage.getItem("favFold2") === "1"; }
function applyFavFold() {
  const box = $("#navCatsFav");
  if (box) box.hidden = favFolded();
  const b = $("#navFavFold");
  if (b) {
    b.classList.toggle("up", favFolded());
    b.title = favFolded() ? "展开分类" : "折叠分类";
    b.textContent = favFolded() ? "展开分类 ▸" : "折叠分类 ▾";
  }
}

function renderSideCats(st) {
  const favBox = $("#navCatsFav");
  if (!favBox) return;
  const pf = favFilter.platform || "";
  const sig = JSON.stringify([pf, favFilter.category, favFilter.sub, st.total,
    st.by_platform || {}, st.all_categories || [], (st.platform_categories || {})[pf] || []]);
  const ncache = $("#navCacheN");
  if (ncache && STATE) {
    const cc = STATE.cache || {};
    const n = (cc.all && cc.all.on) ? (cc.all.total - cc.all.done) : (cc.active || 0);
    ncache.hidden = !n;
    ncache.textContent = n || "";
  }
  const dn = $("#navDupsN");
  if (dn) {
    const n = STATE.dups_n || 0;
    dn.hidden = !n;
    dn.textContent = n;
  }
  if (sig === window.__sideSig) { applyFavFold(); return; }
  window.__sideSig = sig;
  const cats = pf ? ((st.platform_categories || {})[pf] || []) : (st.all_categories || []);
  const total = pf ? (((st.by_platform || {})[pf]) || 0) : (st.total || 0);
  const pfx = pf ? `p/${pf}/` : "";
  const out = [`<a href="#/favs${pf ? "/" + pfx.slice(0, -1) : ""}" class="${!favFilter.category ? "on" : ""}">全部<span>${total}</span></a>`];
  for (const c of cats) {
    const name = c.category || "其他";
    const on = favFilter.category === name;
    out.push(`<a href="#/favs/${pfx}cat/${encodeURIComponent(name)}" class="${on ? "on" : ""}">
      <i class="dot cat-${catColor(name)}"></i>${esc(name)}<span>${c.n}</span></a>`);
    if (on && (c.subs || []).length > 1) {
      out.push(`<div class="subcats">${(c.subs || []).map((x) => {
        const active = favFilter.sub === x.sub;
        const href = x.sub === "未细分"
          ? `#/favs/${pfx}cat/${encodeURIComponent(name)}`
          : `#/favs/${pfx}cat/${encodeURIComponent(name)}/sub/${encodeURIComponent(x.sub)}`;
        return `<a href="${href}" class="${active ? "on" : ""}">${esc(x.sub)}<span>${x.n}</span></a>`;
      }).join("")}</div>`);
    }
  }
  favBox.innerHTML = out.join("");
  applyFavFold();
}

async function refreshState() {
  try { STATE = await api("/api/state"); } catch { return; }
  const meta = window.__META || {};
  if (!STATE.providers) STATE.providers = meta.providers || {};
  if (!STATE.free_plans) STATE.free_plans = meta.free_plans || {};
  const st = STATE.stats, w = STATE.worker;
  const queued = ACTIVE.reduce((n, k) => n + (st.by_status[k] || 0), 0);
  const q = $("#navQueue"); q.hidden = !queued; q.textContent = queued;
  const sf = $("#sideStatus");
  const pg = STATE.progress || {}, dp = STATE.deep || {};
  const parts = [];
  if (w.busy) parts.push(pg.item_id ? `${pg.stage_label} ${pg.pct}% · ${fmtEta(pg.eta)}` : (w.stage || "处理中…"));
  if (dp.item_id) parts.push(`精读 ${dp.pct || 0}% · ${fmtEta(dp.eta)}`);
  const cfs = STATE.classify || {};
  if (cfs.busy) parts.push(`分类 ${cfs.done || 0}/${cfs.total || 0}`);
  const tn = STATE.trash_n || 0;
  const ntr = $("#navTrash");
  if (ntr) { ntr.hidden = !tn; ntr.textContent = tn; }
  const dy = STATE.dy || {};
  if (dy.busy) parts.push(`抖音操作中…`);
  sf.className = "side-foot" + (parts.length ? " busy" : "");
  sf.textContent = parts.join("\n") || `后台运行中 · v${STATE.version || ""}`;
  renderSideCats(st);
  const _L = (STATE && STATE.login) || {};
  $$("#pfTabs .pf-tab").forEach((a) => {
    const p2 = a.dataset.p;
    if (!p2) return;
    const st2 = _L[p2];
    a.classList.toggle("ok", !!(st2 && st2.ok));
    a.classList.toggle("bad", !!(st2 && !st2.ok));
    a.title = st2 ? (st2.ok ? `已登录${st2.name ? "：" + st2.name : ""}` : "未登录") : "未检测";
  });
  $("#navCats").innerHTML = (st.categories || []).map((c) =>
    `<a href="#/library/cat/${encodeURIComponent(c.category || "其他")}" class="${libFilter.category === c.category ? "on" : ""}">
      <i class="dot cat-${catColor(c.category)}"></i>${esc(c.category || "其他")}<span>${c.n}</span></a>`).join("");
  return STATE;
}

let pollTimer = null;
let wasDeepBusy = false;
let lastInsKey = null;
let lastGridPaint = 0;
function startPolling() {
  clearTimeout(pollTimer);
  const tick = async () => {
    // 窗口最小化 / 切到后台时不轮询，回来立刻刷一次：别让后台白烧 CPU
    if (document.hidden) { pollTimer = setTimeout(tick, 5000); return; }
    const before = JSON.stringify(STATE?.stats);
    await refreshState();
    const r = route();
    if (r.name === "process") renderProcessLive();
    else if (r.name === "library" && JSON.stringify(STATE?.stats) !== before
             && Date.now() - lastGridPaint > 10000) { lastGridPaint = Date.now(); renderLibrary(true); }
    else if (r.name === "favs" && JSON.stringify(STATE?.stats) !== before
             && Date.now() - lastGridPaint > 10000) { lastGridPaint = Date.now(); renderFavs(true); }
    else if (r.name === "item" && curItem) {
      const busy = deepBusy(curItem.id);
      if (busy && itemTab === "deep") renderDeepTab($("#tabBody"));
      if (wasDeepBusy && !busy) {
        await renderItem(curItem.id, "deep");
        const err = curItem?.chat?.deep_error;
        toast(err ? "精读失败：" + err : "精读完成 🎉", err ? 6000 : 2600);
      }
      wasDeepBusy = busy;
    }
    // 共识观点整理完（或失败）时刷新页面
    const insKey = JSON.stringify([STATE?.insights?.pending, STATE?.insights?.errors]);
    if (insKey !== lastInsKey) {
      if (lastInsKey !== null && r.name === "graph" && r.tab === "consensus") renderGraphPage(r.tab, r.category, true);
      lastInsKey = insKey;
    }
    // 分类跑完（或失败）时刷新收藏库
    const cbusy = !!STATE?.classify?.busy;
    if (wasClassifyBusy && !cbusy) {
      if (r.name === "favs") { renderFavs(); toast(STATE?.classify?.error ? "分类出错了：" + STATE.classify.error : "分类完成"); }
    }
    wasClassifyBusy = cbusy;
    const active = STATE?.worker?.busy || STATE?.deep?.item_id || STATE?.insights?.pending?.length
      || STATE?.classify?.busy;
    pollTimer = setTimeout(tick, active ? 1000 : 2500);
  };
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) return;
    clearTimeout(pollTimer);
    pollTimer = setTimeout(tick, 150);
  });
  pollTimer = setTimeout(tick, 1000);
}

/* ---------------------------------------------------------------- 路由 */
function route() {
  const h = decodeURIComponent(location.hash.slice(1) || "/favs");
  const p = h.split("/").filter(Boolean);
  if (p[0] === "item") return { name: "item", id: +p[1], tab: p[2] };
  if (p[0] === "trash") return { name: "trash" };
  if (p[0] === "favs") {
    let i = 1, plat = "";
    if (p[i] === "p") { plat = p[i + 1] || ""; i += 2; }
    const cat = p[i] === "cat" ? (p[i + 1] || "") : "";
    const sub = p[i + 2] === "sub" ? p.slice(i + 3).join("/") : "";
    return { name: "favs", platform: plat, category: cat, sub };
  }
  if (p[0] === "welcome") return { name: "welcome" };
  if (p[0] === "cache") return { name: "cache" };
  if (p[0] === "skills") return { name: "skills", tab: p[1] || "" };
  if (p[0] === "process") return { name: "process", tab: p[1] || "" };
  if (p[0] === "settings") return { name: "settings" };
  if (p[0] === "graph") return { name: "graph", tab: p[1] === "consensus" ? "consensus" : "map", category: p.slice(2).join("/") };
  if (p[0] === "weekly") return { name: "weekly", offset: Math.min(0, parseInt(p[1] || "0", 10) || 0) };
  if (p[0] === "library") return { name: "library", category: p[1] === "cat" ? p.slice(2).join("/") : "" };
  if (p[0] === "dups") return { name: "dups", tab: p[1] === "title" ? "title" : "content" };
  return { name: "favs", category: "", sub: "" };
}

async function render() {
  const r = route();
  $$(".nav > a").forEach((a) => a.classList.toggle("on", a.dataset.nav === (r.name === "item" ? "library" : r.name)));
  const curTab = r.name === "item" ? (favFilter.platform || "") : (r.name === "favs" ? (r.platform || "") : null);
  $$("#pfTabs .pf-tab").forEach((a) => {
    if (curTab === null) a.classList.remove("on");
    else a.classList.toggle("on", (a.dataset.p || "") === curTab);
  });
  if (!STATE) await refreshState();
  if (r.name === "library") { libFilter.category = r.category; await refreshState(); return renderLibrary(); }
  if (r.name === "favs") {
    favFilter.platform = r.platform || ""; favFilter.category = r.category; favFilter.sub = r.sub || "";
    if (STATE && STATE.stats) renderSideCats(STATE.stats);
    return renderFavs();
  }
  if (r.name === "trash") return renderTrash();
  if (r.name === "dups") return renderDups(r.tab);
  if (r.name === "item") return renderItem(r.id, r.tab);
  if (r.name === "welcome") return renderWelcome();
  if (r.name === "cache") return renderCache();
  if (r.name === "process") return renderProcess();
  if (r.name === "settings") return renderSettings();
  if (r.name === "skills") return renderSkills(r.tab);
  if (r.name === "graph") return renderGraphPage(r.tab, r.category);
  if (r.name === "weekly") return renderWeekly(r.offset);
}
window.addEventListener("hashchange", () => {
  window.scrollTo(0, 0);
  view.classList.remove("fade-in"); void view.offsetWidth; view.classList.add("fade-in");
  render();
});

/* ---------------------------------------------------------------- 学习库 */
function depsBanner() {
  const d = STATE.deps; if (!d) return "";
  const miss = [];
  if (!d.playwright) miss.push("读取抖音的组件（playwright）：粘贴链接和同步收藏夹都用不了");
  if (!d.asr) miss.push("语音转文字的组件：没有字幕的视频转不了文字");
  if (!miss.length) return "";
  return `<div class="banner warn"><div><b>安装没有完成，缺少：</b><br>${miss.map(esc).join("<br>")}
    <div class="small" style="margin-top:6px">${d.python_ok ? "" : `你用的是 Python ${esc(d.python)}，太新了，部分组件还不支持。请先安装 Python 3.12，`}关掉这个程序，删掉程序文件夹里的 .venv 文件夹，再重新运行安装脚本，看到「安装完成」后再启动。</div></div></div>`;
}

function bannerHtml() {
  const dep = depsBanner(); if (dep) return dep;
  const s = STATE.settings;
  if (!s.api_key_set) return `<div class="banner info"><div><b>还没配置 AI。</b> 没有它只能把视频转成文字，生成不了学习笔记。
    用「免费方案」两分钟就能配好，不花钱。</div><span class="spacer"></span><a class="btn sm primary" href="#/settings">去配置 →</a></div>`;
  if (weeklyDue?.due) return `<div class="banner info"><div><b>上周的学习周报出来了。</b> 看看上周学了什么，这周从哪条开始。</div>
    <span class="spacer"></span><a class="btn sm primary" href="#/weekly/-1">看周报 →</a></div>`;
  return "";
}

async function renderLibrary(soft = false) {
  entryHash = location.hash || "#/library";
  const st = STATE.stats;
  const doneN = st.by_status.done || 0;
  const pct = doneN ? Math.round((st.learned / doneN) * 100) : 0;
  const params = new URLSearchParams({ status: "done" });
  if (libFilter.q) params.set("q", libFilter.q);
  if (libFilter.learned) params.set("learned", libFilter.learned);
  if (libFilter.starred) params.set("starred", "1");
  if (libFilter.category) params.set("category", libFilter.category);
  if (!soft && !$("#libGrid")) view.innerHTML = skeletonLibrary();
  const items = await api("/api/items?" + params);
  lastItems = items;

  if (soft && $("#libGrid")) { paintGrid($("#libGrid"), items, gridHtml); updateProgress(st, doneN, pct); return; }

  view.innerHTML = `
    ${bannerHtml()}
    <div class="head">
      <div><h1>${libFilter.category ? `<i class="dot big-dot cat-${catColor(libFilter.category)}"></i>${esc(libFilter.category)}` : "学习库"}</h1>
      <div class="muted">${libFilter.category ? `<a href="#/library">← 全部分类</a>` : "收藏过的干货，在这里真正学会"}</div></div>
      <div class="spacer"></div>
      <button class="btn" id="randBtn" title="随机抽一条还没学的">${ico("shuffle")}随机学一条</button>
      <button class="btn primary" id="addBtn">${ico("plus")}添加</button>
    </div>
    <div class="card progress-card" id="progCard"></div>
    <div class="toolbar">
      <input class="search" id="q" placeholder="搜索标题、观点、文字稿、我的笔记…" value="${esc(libFilter.q)}">
      <div class="seg" id="segLearned">
        <button data-v="" class="${libFilter.learned === "" && !libFilter.starred ? "on" : ""}">全部</button>
        <button data-v="0" class="${libFilter.learned === "0" ? "on" : ""}">待学</button>
        <button data-v="1" class="${libFilter.learned === "1" ? "on" : ""}">已学</button>
        <button data-v="star" class="${libFilter.starred ? "on" : ""}">${ico("star", "ic sm")}星标</button>
      </div>
      <button class="btn" id="pdfAll" title="把当前列表里的笔记合并导出成一个 PDF">导出 PDF</button>
    </div>
    <div class="grid" id="libGrid"></div>`;
  paintGrid($("#libGrid"), items, gridHtml);
  updateProgress(st, doneN, pct);

  let t; $("#q").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { libFilter.q = e.target.value.trim(); renderLibrary(true); }, 250); });
  $$("#segLearned button").forEach((b) => b.onclick = () => {
    const v = b.dataset.v; libFilter.starred = v === "star" ? "1" : ""; libFilter.learned = v === "star" ? "" : v;
    $$("#segLearned button").forEach((x) => x.classList.toggle("on", x === b)); renderLibrary(true);
  });
  $("#addBtn").onclick = openAdd;
  $("#pdfAll").onclick = () => {
    if (!lastItems.length) return toast("当前列表是空的");
    window.open(`/print?ids=${lastItems.map((x) => x.id).join(",")}`, "_blank");
  };
  $("#randBtn").onclick = async () => {
    const todo = await api("/api/items?status=done&learned=0");
    if (!todo.length) return toast("全部学完啦 🎉");
    location.hash = "#/item/" + todo[Math.floor(Math.random() * todo.length)].id;
  };
}

function updateProgress(st, doneN, pct) {
  const el = $("#progCard"); if (!el) return;
  const pending = ACTIVE.reduce((n, k) => n + (st.by_status[k] || 0), 0);
  el.innerHTML = `
    <div class="big">${st.learned}<span class="muted" style="font-size:18px"> / ${doneN}</span></div>
    <div><div class="row small"><b>学习进度 ${pct}%</b><span class="spacer"></span>
      <span class="muted">${pending ? `还有 ${pending} 条在处理 · ` : ""}${st.starred ? `${ico("starFill", "ic sm star-ic")} ${st.starred} · ` : ""}共收录 ${doneN} 条笔记</span></div>
      <div class="bar" style="margin-top:8px"><i style="width:${pct}%"></i></div></div>`;
}

/* 列表分批渲染 + 滚到接近底部再加载下一批，几百张卡片也不会卡住首屏 */
const GRID_CHUNK = 60;
let gridMore = null;

function paintGrid(el, items, build) {
  if (!el) return;
  el.innerHTML = build(items.slice(0, GRID_CHUNK));
  bindQuick(el);
  let i = GRID_CHUNK;
  gridMore = () => {
    if (!el.isConnected || i >= items.length) { gridMore = null; return; }
    const mark = document.createElement("div");
    el.appendChild(mark);
    el.insertAdjacentHTML("beforeend", build(items.slice(i, i + GRID_CHUNK)));
    mark.remove();
    i += GRID_CHUNK;
    bindQuick(el);
  };
  // 内容不够一屏时自动补几批
  setTimeout(() => {
    let guard = 0;
    while (gridMore && document.body.scrollHeight <= innerHeight + 200 && guard++ < 4) gridMore();
  }, 30);
}

window.addEventListener("scroll", () => {
  if (!gridMore) return;
  if (innerHeight + window.scrollY >= document.body.scrollHeight - 900) gridMore();
}, { passive: true });

function gridHtml(items) {
  if (!items.length) {
    const any = STATE.stats.total;
    if (libFilter.q || libFilter.learned || libFilter.starred)
      return emptyHtml("search", "没有符合条件的笔记", "换个关键词，或者切回「全部」看看。");
    if (any) return emptyHtml("inbox", "笔记还在路上", "视频处理完会自动出现在这里。", `<a class="btn" href="#/process">查看处理进度</a>`);
    return emptyHtml("book", "学习库还是空的", "把抖音收藏里的干货搬进来，这里会变成你的知识库。",
      `<a class="btn primary" href="#/process">${ico("plus")}同步收藏夹</a><button class="btn" onclick="openAdd()">粘贴分享链接</button>`);
  }
  return items.map((it, i) => `
    <a class="vcard" data-id="${it.id}" href="#/item/${it.id}" style="--i:${Math.min(i, 14)}">
      <div class="cover">${it.cover ? `<img src="${esc(coverUrl(it))}" referrerpolicy="no-referrer" loading="lazy" onerror="window.imgFallback(this)">` : ""}
        <div class="ph cat-${catColor(it.category)}" ${it.cover ? 'style="z-index:-1"' : ""}>${ico(it.media_type === "note" ? "file" : "play", "ic ph-ic")}</div>
        ${it.learned ? `<span class="learned-tag">${ico("check", "ic sm")}已学</span>` : ""}
        ${it.duration ? `<span class="dur">${fmtDur(it.duration)}</span>` : ""}${quickActs(it)}</div>
      <div class="body">
        <div class="t">${it.starred ? ico("starFill", "ic star-ic") : ""}${esc(it.note_title || it.title)}</div>
        <div class="s">${esc(it.summary)}</div>
        <div class="foot">${catChip(it.category)}
          ${it.platform === "xhs" ? `<span class="chip warn">小红书</span>` : ""}
          ${it.difficulty ? `<span class="chip gray">${esc(it.difficulty)}</span>` : ""}
          ${it.media_type === "note" ? `<span class="chip gray">图文</span>` : ""}
          ${it.has_deep ? `<span class="chip teal">${ico("cap", "ic sm")}已精读</span>` : ""}
          <span class="spacer"></span><span class="a" title="${esc(it.author || "")}">${esc(it.author || "")}</span></div>
      </div></a>`).join("");
}

/* 列表视图：一行一条，967 条时更好扫 */
function listHtml(items) {
  if (!items.length) return gridHtml(items);
  return items.map((it) => `
    <a class="lrow" data-id="${it.id}" href="#/item/${it.id}">
      <span class="thumb">${it.cover ? `<img src="${esc(coverUrl(it))}" referrerpolicy="no-referrer" loading="lazy" onerror="this.remove()">` : ""}</span>
      <span class="mid">
        <b class="t">${it.starred ? ico("starFill", "ic star-ic") : ""}${esc(it.note_title || it.title)}</b>
        <span class="s">${esc(it.summary || "")}</span>
      </span>
      <span class="right">
        ${catChip(it.category)}${it.learned ? `<span class="chip teal">已学</span>` : ""}
        <span class="muted small">${esc(it.author || "")}</span>
        <span class="muted small">${it.duration ? fmtDur(it.duration) : ""}</span>
      </span></a>`).join("");
}

/* 卡片右上角的快捷操作：取消收藏 / 一键删除 */
function quickActs(it) {
  return `<div class="quick">
    <button data-quick="unfav" data-id="${it.id}" title="取消收藏（同时删掉本地缓存，记录进回收站）">${ico("x", "ic sm")}</button>
    <button data-quick="del" data-id="${it.id}" title="删除这条记录（同时删掉本地缓存，进回收站）">${ico("trash", "ic sm")}</button>
  </div>`;
}

function bindQuick(root) {
  root.querySelectorAll(".quick button").forEach((b) => {
    b.onclick = async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const id = +b.dataset.id;
      const act = b.dataset.quick === "unfav" ? "unfavorite" : "delete";
      if (act === "unfavorite" && !confirm("取消这条收藏？抖音里也会取消，本地缓存删掉，记录进回收站。")) return;
      b.disabled = true;
      try {
        await api(`/api/items/${id}/action`, { action: act });
        toast(act === "unfavorite" ? "已取消收藏，缓存已删除" : "已移进回收站，缓存已删除");
        await refreshState();
        if (route().name === "favs") renderFavs(true);
        else if (route().name === "library") renderLibrary();
      } finally {
        b.disabled = false;
      }
    };
  });
}

/* ---------------------------------------------------------------- 右键菜单 */
function showCtxMenu(x, y, id) {
  const it = (favItems || []).find((i) => i.id === id) || (lastItems || []).find((i) => i.id === id) || {};
  const menu = $("#ctxMenu");
  menu.innerHTML = `
    <button data-act="open">打开详情</button>
    ${it.aweme_id && it.media_type !== "note" && it.platform !== "bili" ? `<button data-act="play">播放原视频</button>` : ""}
    ${it.url ? `<button data-act="copy">复制原链接</button>` : ""}
    <button data-act="unfav" class="danger">取消收藏并删除（清缓存 · 进回收站）</button>`;
  menu.hidden = false;
  const w = menu.offsetWidth || 190, h = menu.offsetHeight || 200;
  menu.style.left = Math.max(8, Math.min(x, innerWidth - w - 8)) + "px";
  menu.style.top = Math.max(8, Math.min(y, innerHeight - h - 8)) + "px";
  menu.onclick = async (e) => {
    const b = e.target.closest("button[data-act]");
    if (!b) return;
    const act = b.dataset.act;
    menu.hidden = true;
    if (act === "open") location.hash = `#/item/${id}`;
    else if (act === "play") openPlayer(id, it.note_title || it.title || "", it.aweme_id || "");
    else if (act === "unfav") {
      const tip = it.aweme_id && it.platform !== "xhs"
        ? "取消收藏？抖音里也会取消，本地缓存会删掉，这条记录进回收站（可恢复）。"
        : "取消收藏？本地缓存会删掉，这条记录进回收站（可恢复）。";
      if (!confirm(tip)) return;
      await api(`/api/items/${id}/action`, { action: "unfavorite" });
      toast("已取消收藏，缓存已删除，记录在回收站");
      await refreshState();
      if (route().name === "favs") renderFavs(true);
      else if (route().name === "library") renderLibrary(true);
    }
    else if (act === "copy") copyText(it.url || "", "链接已复制");
  };
}

document.addEventListener("contextmenu", (e) => {
  const card = e.target.closest && e.target.closest(".vcard[data-id]");
  const m = $("#ctxMenu");
  if (!card) { if (m) m.hidden = true; return; }
  e.preventDefault();
  showCtxMenu(e.clientX, e.clientY, +card.dataset.id);
});
document.addEventListener("click", (e) => {
  const m = $("#ctxMenu");
  if (m && !m.hidden && !e.target.closest("#ctxMenu")) m.hidden = true;
});
document.addEventListener("scroll", () => { const m = $("#ctxMenu"); if (m) m.hidden = true; }, true);

/* ---------------------------------------------------------------- 回收站 */
async function renderTrash() {
  let d;
  try { d = await api("/api/trash"); } catch (e) { view.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  const items = d.items || [];
  view.innerHTML = `
    <div class="head">
      <div><h1>回收站</h1><div class="muted">删掉的内容先放这儿，随时能恢复；清空之后笔记文件也会一起删掉。</div></div>
      <div class="spacer"></div>
      ${items.length ? `<button class="btn" id="trashEmpty" style="color:var(--bad)">清空回收站（${items.length}）</button>` : ""}
    </div>
    ${items.length ? `
      <div class="card" style="padding:6px 20px">
        ${items.map((it) => `
          <div class="trash-row">
            ${it.cover ? `<img class="trash-thumb" src="${esc(coverUrl(it))}" referrerpolicy="no-referrer" onerror="this.removeAttribute('src')">` : `<div class="trash-thumb"></div>`}
            <div class="trash-meta">
              <div class="trash-t">${esc((it.title || "（无标题）").slice(0, 90))}</div>
              <div class="muted small">${esc(it.author || "")}${it.duration ? " · " + fmtDur(it.duration) : ""}${it.category ? " · " + esc(it.category) : ""} · 删于 ${fmtDay(it.deleted_at)}</div>
            </div>
            <button class="btn sm" data-restore="${it.id}">恢复</button>
            <button class="btn sm" data-hard="${it.id}" style="color:var(--bad)">彻底删除</button>
          </div>`).join("")}
      </div>`
      : emptyHtml("checkCircle", "回收站是空的", "删掉的内容会先放到这里，可以随时恢复。")}`;

  $$("#view [data-restore]").forEach((b) => b.onclick = async () => {
    await api(`/api/items/${b.dataset.restore}/action`, { action: "restore" });
    toast("已恢复"); await refreshState(); renderTrash();
  });
  $$("#view [data-hard]").forEach((b) => b.onclick = async () => {
    if (!confirm("彻底删除这条？笔记文件也会一起删，不能恢复。")) return;
    await api(`/api/items/${b.dataset.hard}/action`, { action: "purge" });
    toast("已彻底删除"); await refreshState(); renderTrash();
  });
  $("#trashEmpty") && ($("#trashEmpty").onclick = () => {
    $("#trashN").textContent = items.length;
    $("#trashSure").checked = false;
    $("#trashEmptyOk").disabled = true;
    $("#trashModal").hidden = false;
  });
  $("#trashSure") && ($("#trashSure").onchange = (e) => { $("#trashEmptyOk").disabled = !e.target.checked; });
  $("#trashEmptyOk") && ($("#trashEmptyOk").onclick = async () => {
    const r = await api("/api/trash/empty", {});
    $("#trashModal").hidden = true;
    toast(`已清空 ${r.deleted} 条`);
    await refreshState(); renderTrash();
  });
}

/* ---------------------------------------------------------------- 查重 */
async function openDups() {
  const m = $("#dupModal");
  m.hidden = false;
  $("#dupBody").innerHTML = `<div class="muted" style="padding:20px 0">正在比对 ${STATE?.stats?.total || ""} 条收藏…</div>`;
  let data;
  try { data = await api("/api/dups"); }
  catch (e) { $("#dupBody").innerHTML = `<div class="muted">${esc(e.message)}</div>`; return; }
  const groups = data.groups || [];
  if (!groups.length) {
    $("#dupBody").innerHTML = `<div class="empty" style="padding:30px 0">${ico("checkCircle")}
      <h3>没有发现重复</h3><p class="muted small">${STATE?.stats?.total || 0} 条全都比对过了：标题、同作者标题前缀、同作者时长+相似度，都没有撞上。</p></div>`;
    $("#dupFoot").textContent = "";
    return;
  }
  $("#dupFoot").textContent = `共 ${groups.length} 组 · 多出来 ${data.n} 条`;
  $("#dupBody").innerHTML = groups.map((g, gi) => `
    <div class="dup-group">
      <div class="dup-head"><b>第 ${gi + 1} 组</b><span class="muted small">${g.items.length} 条看起来是同一个内容</span></div>
      ${g.items.map((it) => `<div class="dup-row">
        <div class="dup-meta">
          <div class="dup-t">${esc((it.title || "").slice(0, 70))}</div>
          <div class="muted small">${esc(it.author || "")} · ${it.duration ? fmtDur(it.duration) : "图文"} · ${(STATUS[it.status] || [it.status])[0]} · ${fmtDay(it.created_at)}</div>
        </div>
        <a class="btn sm" href="#/item/${it.id}">打开</a>
        <button class="btn sm" data-del="${it.id}" style="color:var(--bad)">删除</button>
      </div>`).join("")}
    </div>`).join("");
  $$("#dupBody [data-del]").forEach((b) => b.onclick = async () => {
    if (!confirm("删除这条？笔记文件也会一起删。")) return;
    await api(`/api/items/${b.dataset.del}/action`, { action: "delete" });
    toast("已删除");
    await refreshState();
    openDups();
  });
}

/* ---------------------------------------------------------------- 收藏库 */
const fmtHours = (sec) => {
  const s = sec || 0, h = s / 3600;
  return h >= 1 ? `${h.toFixed(1)} 小时` : `${Math.round(s / 60)} 分钟`;
};

/* 收藏时间 / 发布时间：只显示月-日，跨年的带上年份 */
const fmtDay = (t) => {
  if (!t) return "";
  const d = new Date(t * 1000), now = new Date();
  const p = (n) => String(n).padStart(2, "0");
  const md = `${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  return d.getFullYear() === now.getFullYear() ? md : `${d.getFullYear()}-${md}`;
};
/* 完成时间：今天只显示时:分，昨天/更早带日期 */
const fmtDayTime = (t) => {
  if (!t) return "";
  const d = new Date(t * 1000), now = new Date();
  const hm = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  const sameDay = d.toDateString() === now.toDateString();
  const yst = new Date(now.getTime() - 86400000);
  if (sameDay) return hm;
  if (d.toDateString() === yst.toDateString()) return `昨天 ${hm}`;
  return `${fmtDay(t)} ${hm}`;
};
/* 时间筛选：按「什么时候收藏/入库」算（抖音列表不带收藏时间，用入库时间兜底） */
function sinceOf(v) {
  const now = new Date();
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() / 1000;
  if (v === "today") return startOfDay;
  if (v === "3d") return startOfDay - 2 * 86400;
  if (v === "7d") return startOfDay - 6 * 86400;
  return 0;
}

const timeLabel = (it) => {
  if (it.collected_at) return `收藏 ${fmtDay(it.collected_at)}`;
  // 抖音收藏列表不带收藏时间，就用「什么时候进到库里」当依据，别让用户以为这是旧视频
  const added = it.created_at || 0;
  if (added) {
    const days = Math.floor((Date.now() / 1000 - added) / 86400);
    if (days <= 0) return "今天加入";
    if (days === 1) return "昨天加入";
    if (days <= 7) return `${days} 天前加入`;
  }
  return it.published_at ? `发布 ${fmtDay(it.published_at)}` : "";
};

function favGrid(items) {
  if (!items.length) return emptyHtml("search", "这个筛选下没有收藏", "换一个分类或时长看看。");
  const cut = (s, n = 58) => { s = s || ""; return s.length > n ? s.slice(0, n) + "…" : s; };
  return items.map((it, i) => {
    const [stText] = STATUS[it.status] || [it.status, "gray"];
    const ready = it.status === "done";
    return `
    <a class="vcard" data-id="${it.id}" href="#/item/${it.id}" style="--i:${Math.min(i, 14)}">
      <div class="cover">${it.cover ? `<img src="${esc(coverUrl(it))}" referrerpolicy="no-referrer" loading="lazy" onerror="window.imgFallback(this)">` : ""}
        <div class="ph cat-${catColor(it.category)}" ${it.cover ? 'style="z-index:-1"' : ""}>${ico(it.media_type === "note" ? "file" : "play", "ic ph-ic")}</div>
        <span class="dur">${it.duration ? fmtDur(it.duration) : (it.media_type === "note" ? "图文" : "—")}</span>
        ${it.media_type !== "note" && it.aweme_id && it.platform !== "bili" ? `<button class="play-ovr" data-play="${it.id}" data-aweme="${esc(it.aweme_id || "")}" data-title="${esc(it.note_title || it.title || "")}" title="播放原视频">${ico("play", "ic sm")}</button>` : ""}
        ${ready ? (it.learned ? `<span class="learned-tag">${ico("check", "ic sm")}已学</span>` : "")
          : `<span class="learned-tag">${esc(stText)}</span>`}${quickActs(it)}</div>
      <div class="body">
        <div class="t">${esc(cut(it.note_title || it.title || "未命名"))}</div>
        <div class="s">${esc(it.summary || (ready ? "" : "还没整理成笔记，先攒着"))}</div>
        <div class="foot">${catChip(it.category)}
          ${it.subcategory ? `<span class="chip gray">${esc(it.subcategory)}</span>` : ""}
          ${it.media_type === "note" ? `<span class="chip gray">图文</span>` : ""}
          ${timeLabel(it) ? `<span class="chip gray">${timeLabel(it)}</span>` : ""}
          <span class="spacer"></span><span class="a" title="${esc(it.author || "")}">${esc(it.author || "")}</span></div>
      </div></a>`;
  }).join("");
}

async function renderFavs(soft = false) {
  entryHash = location.hash || "#/favs";
  const st = STATE.stats;
  const dur = st.duration || { total: 0, n: 0, avg: 0, buckets: {} };
  const cls = st.classify || { classified: 0, unclassified: 0 };
  const cf = STATE.classify || {};
  const params = new URLSearchParams({ status: "all", sort: favFilter.sort });
  if (favFilter.q) params.set("q", favFilter.q);
  if (favFilter.category) params.set("category", favFilter.category);
  if (favFilter.sub) params.set("sub", favFilter.sub);
  if (favFilter.dur) params.set("dur", favFilter.dur);
  if (favFilter.stage) params.set("stage", favFilter.stage);
  if (favFilter.scope) params.set("scope", favFilter.scope);
  const sinceTs = sinceOf(favFilter.since);
  if (sinceTs) params.set("since", String(sinceTs));
  if (favFilter.platform) params.set("platform", favFilter.platform);
  if (!soft && !$("#favGrid")) view.innerHTML = skeletonLibrary();
  const items = await api("/api/items?" + params);
  favItems = items;
  // 选了平台就显示这个平台自己的数字，不跟另一个平台混在一起
  const ps = favFilter.platform
    ? ((st.platform_stats || {})[favFilter.platform] || { total: 0, done: 0, dur_total: 0, dur_avg: 0, classified: 0 })
    : null;
  const sc = ps ? { total: ps.total, durTotal: ps.dur_total, durAvg: ps.dur_avg, classified: ps.classified } : {
    total: st.total, durTotal: dur.total, durAvg: dur.avg, classified: cls.classified };
  const nDone = ps ? ps.done : ((st.by_status || {}).done || 0);
  const nTodo = Math.max(0, sc.total - nDone);

  const statHtml = `
    <div class="stat"><b>${sc.total}</b><span>条收藏</span></div>
    <div class="stat"><b>${fmtHours(sc.durTotal)}</b><span>合计时长</span></div>
    <div class="stat"><b>${sc.durAvg ? fmtDur(sc.durAvg) : "—"}</b><span>平均时长</span></div>
    <div class="stat"><b>${sc.classified}</b><span>已分类${sc.total - sc.classified > 0 ? `（还有 ${sc.total - sc.classified} 条没分）` : " · 全部搞定"}</span></div>`;

  if (soft && $("#favGrid")) {
    paintGrid($("#favGrid"), items, favView === "list" ? listHtml : favGrid);
    $("#favStats").innerHTML = statHtml;
    $("#favCount").textContent = `${items.length} 条`;
    $$("#segStage button").forEach((b) => {
      const el = b.querySelector(".n");
      if (el) el.textContent = b.dataset.v === "done" ? nDone : b.dataset.v === "todo" ? nTodo : sc.total;
    });
    return;
  }


  view.innerHTML = `
    ${bannerHtml()}
    <div class="head">
      <div><h1>${favFilter.category ? `<i class="dot big-dot cat-${catColor(favFilter.category)}"></i>${esc(favFilter.category)}${favFilter.sub ? ` <span class="muted" style="font-size:22px">› ${esc(favFilter.sub)}</span>` : ""}` : (favFilter.platform === "xhs" ? "小红书" : favFilter.platform === "douyin" ? "抖音" : "汇总")}</h1>
        <div class="muted">${favFilter.category ? `<a href="#/favs${favFilter.platform ? "/p/" + favFilter.platform : ""}">← 全部分类</a>${favFilter.sub ? ` · <a href="#/favs${favFilter.platform ? "/p/" + favFilter.platform : ""}/cat/${encodeURIComponent(favFilter.category)}">看「${esc(favFilter.category)}」全部</a>` : ""}` : (favFilter.platform === "xhs" ? "只看小红书的收藏：分类、时长、拆解进度都只算小红书" : favFilter.platform === "douyin" ? "只看抖音的收藏：分类、时长、拆解进度都只算抖音" : (favFilter.platform === "bili" ? "只看 B 站的收藏：只解析你手动粘贴的那些，不做自动同步" : "抖音 + 小红书 + B站 全部收藏的总览：三个平台的内容都在这儿"))}</div></div>
      <div class="spacer"></div>
      <button class="btn" id="favDup" title="看看有没有重复收藏">${ico("search")}查重</button>
      <button class="btn" id="favRule" title="只看标题和话题标签，不花钱、不用 AI，几百条也是秒出">${ico("shuffle")}按标题分类</button>
      <button class="btn primary" id="favAi" title="用 AI 逐条判断，会花一点点额度">${ico("sparkles")}AI 精分类</button>
    </div>
    ${cf.busy ? `<div class="banner info"><div><b>正在用 AI 分类…</b> ${cf.done || 0} / ${cf.total || 0} 条</div></div>` : ""}
    <div class="card fav-stat" id="favStats">${statHtml}</div>
    <div class="toolbar">
      <input class="search" id="q" placeholder="搜索标题、作者…" value="${esc(favFilter.q)}">
      <select class="sortsel" id="favScope" title="搜哪里">
        <option value="" ${!favFilter.scope ? "selected" : ""}>全文搜</option>
        <option value="title" ${favFilter.scope === "title" ? "selected" : ""}>只搜标题</option>
        <option value="author" ${favFilter.scope === "author" ? "selected" : ""}>只搜作者</option>
        <option value="body" ${favFilter.scope === "body" ? "selected" : ""}>只搜笔记正文</option>
      </select>
      <div class="seg seg-view" id="segView">
        <button data-v="grid" class="${favView === "grid" ? "on" : ""}">网格</button>
        <button data-v="list" class="${favView === "list" ? "on" : ""}">列表</button>
      </div>
      <div class="seg seg-stage" id="segStage">
        ${[["", "全部"], ["done", "已拆解"], ["todo", "未拆解"]]
        .map(([v, l]) => `<button data-v="${v}" class="${favFilter.stage === v ? "on" : ""}">${l}<span class="n">${v === "done" ? nDone : v === "todo" ? nTodo : sc.total}</span></button>`).join("")}
      </div>
      <div class="seg" id="segSince">
        ${[["", "全部时间"], ["today", "今天加的"], ["3d", "近三天"], ["7d", "近一周"]]
        .map(([v, l]) => `<button data-v="${v}" class="${favFilter.since === v ? "on" : ""}">${l}</button>`).join("")}
      </div>
      <div class="seg" id="segDur">
        ${[["", "全部时长"], ["s", "≤1 分"], ["m", "1-5 分"], ["l", "5-15 分"], ["xl", "15 分以上"]]
        .map(([v, l]) => `<button data-v="${v}" class="${favFilter.dur === v ? "on" : ""}">${l}</button>`).join("")}
      </div>
      <select class="sortsel" id="favSort">
        <option value="new" ${favFilter.sort === "new" ? "selected" : ""}>最新入库（推荐）</option>
        <option value="time_desc" ${favFilter.sort === "time_desc" ? "selected" : ""}>发布时间新→旧</option>
        <option value="done" ${favFilter.sort === "done" ? "selected" : ""}>最近处理完的</option>
        <option value="time_desc" ${favFilter.sort === "time_desc" ? "selected" : ""}>时间从新到旧</option>
        <option value="time_asc" ${favFilter.sort === "time_asc" ? "selected" : ""}>时间从旧到新</option>
        <option value="long" ${favFilter.sort === "long" ? "selected" : ""}>时长从长到短</option>
        <option value="short" ${favFilter.sort === "short" ? "selected" : ""}>时长从短到长</option>
      </select>
      <span class="muted small" id="favCount">${items.length} 条</span>
    </div>
    <div class="grid" id="favGrid"></div>`;

  const buildFav = favView === "list" ? listHtml : favGrid;
  $("#favGrid").className = favView === "list" ? "grid as-list" : "grid";
  paintGrid($("#favGrid"), items, buildFav);
  let t;
  $("#q").addEventListener("input", (e) => {
    clearTimeout(t);
    t = setTimeout(() => {
      favFilter.q = e.target.value.trim();
      const ss = $("#sideSearch");
      if (ss && ss.value !== favFilter.q) ss.value = favFilter.q;
      renderFavs(true);
    }, 250);
  });
  $$("#segSince button").forEach((b) => b.onclick = () => {
    favFilter.since = b.dataset.v;
    $$("#segSince button").forEach((x) => x.classList.toggle("on", x === b));
    renderFavs(true);
  });
  $$("#segDur button").forEach((b) => b.onclick = () => {
    favFilter.dur = b.dataset.v;
    $$("#segDur button").forEach((x) => x.classList.toggle("on", x === b));
    renderFavs(true);
  });
  $$("#segStage button").forEach((b) => b.onclick = () => {
    favFilter.stage = b.dataset.v;
    $$("#segStage button").forEach((x) => x.classList.toggle("on", x === b));
    renderFavs(true);
  });
  $("#favSort").onchange = (e) => { favFilter.sort = e.target.value; renderFavs(true); };
  $("#favScope") && ($("#favScope").onchange = (e) => { favFilter.scope = e.target.value; renderFavs(true); });
  $$("#segView button").forEach((b) => b.onclick = () => {
    favView = b.dataset.v;
    try { localStorage.setItem("favView", favView); } catch (e) {}
    renderFavs();
  });
  bindQuick(view);
  $("#favDup").onclick = () => { location.hash = "#/dups"; };
  $("#favRule").onclick = async () => {
    const r = await api("/api/classify", { mode: "rule", platform: favFilter.platform || undefined });
    toast(r.n ? `已按标题分好 ${r.n} 条` : "没有需要分类的条目了");
    await refreshState(); renderFavs();
  };
  $("#favAi").onclick = async () => {
    if (!STATE.settings.api_key_set) return toast("先在设置里配好 AI");
    await api("/api/classify", { mode: "ai", scope: "others", platform: favFilter.platform || undefined });
    toast("AI 开始补分类（只处理「其他」和不认识的），一两分钟");
    await refreshState(); renderFavs();
  };
}

/* ---------------------------------------------------------------- 重复内容（确认后只留一条） */
let dupTab = "content";
let dupPlat = "";
let dupData = { content: null, title: null };

function dupCard(it, groupKey) {
  const title = it.note_title || it.title || "未命名";
  const summary = (it.summary || "").replace(/\s+/g, " ").slice(0, 120);
  const meta = [it.author, it.duration ? fmtDur(it.duration) : "", it.collected_at ? "收藏 " + fmtDay(it.collected_at) : ""]
    .filter(Boolean).join(" · ");
  return `<label class="dupr">
    <input type="radio" name="dup-${groupKey}" value="${it.id}">
    ${it.cover ? `<img class="dupi" src="${esc(coverUrl(it))}" referrerpolicy="no-referrer" loading="lazy">`
      : `<span class="dupi empty">${ico("file", "ic sm")}</span>`}
    <span class="dupc">
      <b>${esc(title)}</b>
      ${summary ? `<span class="muted small">${esc(summary)}${summary.length >= 120 ? "…" : ""}</span>` : ""}
      <span class="muted small">${esc(meta)}${it.n_points ? ` · 观点 ${it.n_points} 条` : ""}</span>
    </span>
    <a class="dupo" href="#/item/${it.id}" onclick="event.stopPropagation()">打开</a>
  </label>`;
}

function dupGroupsHtml(groups, tab) {
  if (!groups.length) {
    return `<div class="empty" style="padding:44px">
      ${tab === "content"
        ? "没找到拆解内容重复的收藏。<br><span class=\"muted small\">处理得越多，越容易查出搬运、重复投稿的条目。</span>"
        : "没找到标题/作者重复的收藏。"}
    </div>`;
  }
  return groups.map((g, gi) => {
    const key = `${gi}`;
    const dup = g.tier !== "near";
    return `<div class="card dupg" data-key="${key}">
      <div class="dupg-head">
        ${tab === "content"
          ? `<span class="chip ${dup ? "bad" : "warn"}">${dup ? "几乎重复" : "内容相近"}</span>
             <b>这 ${g.items.length} 条拆解的是同一件事</b>
             <span class="muted small">相似度 ${Math.round((g.score || 0) * 100)}%</span>`
          : `<span class="chip warn">标题/作者重复</span>
             <b>这 ${g.items.length} 条可能是同一条视频</b>`}
      </div>
      <div class="dupg-list">${g.items.map((it) => dupCard(it, key)).join("")}</div>
      <div class="dupg-foot">
        <span class="muted small" data-tip>选一条留下，其余 ${g.items.length - 1} 条移到回收站</span>
        <span class="spacer"></span>
        <button class="btn sm primary" data-keep disabled>保留选中的这条</button>
      </div>
    </div>`;
  }).join("");
}

async function renderDups(tab = "content") {
  dupTab = tab;
  view.innerHTML = `<div class="head"><div><h1>重复内容</h1>
      <div class="muted">内容相近的收藏在这里排好组：选一条留下，其余移到回收站（回收站里能恢复）。</div></div>
      <div class="spacer"></div>
      <button class="btn" id="dupReload">${ico("shuffle")}重新查找</button>
    </div>
    <div class="seg" id="dupTabs">
      <button data-t="content" class="${tab === "content" ? "on" : ""}">按拆解内容</button>
      <button data-t="title" class="${tab === "title" ? "on" : ""}">按标题 / 作者</button>
    </div>
    <div class="seg" id="dupPlat" style="margin-top:10px">
      <button data-p="" class="${!dupPlat ? "on" : ""}">全部</button>
      <button data-p="douyin" class="${dupPlat === "douyin" ? "on" : ""}">抖音</button>
      <button data-p="xhs" class="${dupPlat === "xhs" ? "on" : ""}">小红书</button>
    </div>
    <div id="dupWrap"><div class="empty" style="padding:44px">正在比对内容…</div></div>`;

  $$("#dupTabs button").forEach((b) => b.onclick = () => { location.hash = b.dataset.t === "title" ? "#/dups/title" : "#/dups"; });
  $$("#dupPlat button").forEach((b) => b.onclick = () => { dupPlat = b.dataset.p; renderDups(tab); });

  let res;
  try {
    const qs = `mode=${tab === "title" ? "title" : "content"}${dupPlat ? `&platform=${dupPlat}` : ""}`;
    res = dupData[tab + (dupPlat || "")] || await api(`/api/dups?${qs}`);
  } catch (e) {
    $("#dupWrap").innerHTML = `<div class="empty" style="padding:40px">${esc(e.message)}</div>`;
    return;
  }
  dupData[tab + (dupPlat || "")] = res;
  const groups = res.groups || [];
  const wrap = $("#dupWrap");
  wrap.innerHTML = groups.length
    ? `<div class="dupg-meta">${groups.length} 组 · 确认后最多清掉 ${res.n} 条</div>` + dupGroupsHtml(groups, tab)
    : dupGroupsHtml([], tab);

  $$(".dupg", wrap).forEach((box) => {
    const radios = $$(`input[name="dup-${box.dataset.key}"]`, box);
    const btn = $("[data-keep]", box);
    const tip = $("[data-tip]", box);
    const sync = () => {
      const picked = radios.find((r) => r.checked);
      btn.disabled = !picked;
      $$(".dupr", box).forEach((row) => row.classList.toggle("picked", row.contains(picked)));
      const n = radios.length - 1;
      tip.textContent = picked ? `其余 ${n} 条移到回收站` : `选一条留下，其余 ${n} 条移到回收站`;
    };
    radios.forEach((r) => r.onchange = sync);
    if (radios[0]) radios[0].checked = true;
    sync();
    btn.onclick = async () => {
      const keep = +radios.find((r) => r.checked).value;
      const drop = radios.map((r) => +r.value).filter((x) => x !== keep);
      const keepTitle = radios.find((r) => r.checked).closest(".dupr").querySelector("b").textContent;
      if (!confirm(`只保留《${keepTitle}》？\n\n其余 ${drop.length} 条会移到回收站，随时可以恢复。`)) return;
      btn.disabled = true;
      try {
        const r = await api("/api/dups/keep", { keep, drop });
        toast(`已保留一条，${r.trashed} 条移进回收站`);
        dupData = { content: null, title: null };
        box.remove();
        await refreshState();
        renderDups(dupTab);
      } catch (e) {
        toast(e.message);
        btn.disabled = false;
      }
    };
  });

  $("#dupReload").onclick = () => { dupData = { content: null, title: null }; renderDups(dupTab); };
}

/* ---------------------------------------------------------------- 笔记详情 */
/* 交给 DSH 的指令：整段笔记拼成的可复制指令 */
function dshHtml(it) {
  if (!it.dsh) return "";
  return `<section class="dsh-card">
    <div class="row"><h2>交给 DSH 的指令</h2><span class="spacer"></span>
      <button class="btn sm primary" id="dshCopy2">${ico("copy", "ic sm")}复制指令</button></div>
    <p class="muted small">复制后直接粘到 DSH 的对话框里，它就会照这条笔记动手（装依赖、改文件、跑命令）。</p>
    <pre class="dsh-pre">${esc(it.dsh)}</pre>
  </section>`;
}

function noteBody(it) {
  const n = it.note || {};
  const sec = (title, html) => (html ? `<section><h2>${title}</h2>${html}</section>` : "");
  return `
    ${sec("一句话总结", n.summary ? `<div class="summary">${esc(n.summary)}</div>` : "")}
    ${sec("核心观点", n.points?.length ? `<ol class="points">${n.points.map((p) => `<li>${esc(p)}</li>`).join("")}</ol>` : "")}
    ${sec("照着做", n.steps?.length ? `<ol class="steps">${n.steps.map((p) => `<li><div>${esc(p)}</div></li>`).join("")}</ol>` : "")}
    ${sec("提到的工具", n.tools?.length ? `<div class="kv">${n.tools.map((t) => `<div><b>${esc(t.name)}</b><span>${esc(t.use)}</span></div>`).join("")}</div>` : "")}
    ${sec("关键概念", n.concepts?.length ? `<div class="kv">${n.concepts.map((t) => `<div><b>${esc(t.term)}</b><span>${esc(t.explain)}</span></div>`).join("")}</div>` : "")}
    ${sec("自测一下", n.quiz?.length ? `<div class="quiz">${n.quiz.map((q, i) => `<div class="q"><b>${i + 1}. ${esc(q.q)}</b>
        <div class="row" style="margin-top:6px"><button class="btn sm" data-reveal>看答案</button></div><div class="a">${ico("check", "ic sm")} ${esc(q.a)}</div></div>`).join("")}</div>` : "")}`;
}

let itemTab = "note";
let curItem = null;
let quizState = {};

const fmtEta = (s) => {
  s = Math.max(0, Math.round(s || 0));
  if (s < 10) return "马上就好";
  if (s < 60) return `约 ${s} 秒`;
  const m = Math.floor(s / 60), r = s % 60;
  if (m < 60) return `约 ${m} 分${r >= 30 && m < 10 ? "半" : ""}钟`;
  return `约 ${Math.floor(m / 60)} 小时 ${m % 60} 分`;
};
const fmtTs = (sec) => { sec = Math.round(sec || 0); const h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60;
  return (h ? h + ":" + String(m).padStart(2, "0") : String(m).padStart(2, "0")) + ":" + String(s).padStart(2, "0"); };
const mdLite = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\n/g, "<br>");

async function copyText(text, msg = "已复制") {
  try { await navigator.clipboard.writeText(text); }
  catch { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); }
  toast(msg);
}

function deepBusy(id) {
  const d = STATE?.deep || {};
  return d.item_id === id || (d.pending || []).includes(id);
}

/* 优先处理之后盯着这一条，处理完自动把页面刷新成笔记 */
let itemWatchTimer = null;
function watchItem(id) {
  if (itemWatchTimer) clearInterval(itemWatchTimer);
  const started = Date.now();
  itemWatchTimer = setInterval(async () => {
    if (Date.now() - started > 30 * 60 * 1000) { clearInterval(itemWatchTimer); return; }
    let cur;
    try { cur = await api("/api/items/" + id); } catch { return; }
    if (!cur || !cur.id) return;
    const live = document.getElementById("itemLiveMsg");
    if (live) live.textContent = cur.reason || (STATE.worker && STATE.worker.item_id === id ? (STATE.worker.stage || "") : "");
    if (["fetching", "downloading", "transcribing", "extracting"].includes(cur.status) && !document.getElementById("itemLive")) {
      clearInterval(itemWatchTimer); itemWatchTimer = null; renderItem(id); return;
    }
    if (cur.status === "done") {
      clearInterval(itemWatchTimer); itemWatchTimer = null;
      toast("处理完了，笔记已经出来");
      renderItem(id);
    } else if (["failed", "skipped", "irrelevant"].includes(cur.status)) {
      clearInterval(itemWatchTimer); itemWatchTimer = null;
      const msg = cur.status === "irrelevant"
        ? "处理完了，但 AI 判断它和你的关注主题无关，已收进「主题无关」（觉得有用可以点开收回）"
        : (cur.reason || "这条没能处理成功");
      toast(msg, 7000);
      renderItem(id);
    }
  }, 3000);
}
window.watchItem = watchItem;

async function renderItem(id, tab) {
  let it;
  if (curItem?.id !== id) view.innerHTML = skeletonItem();
  try { it = await api(`/api/items/${id}`); } catch (e) { view.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  if (tab) itemTab = tab;
  if (curItem?.id !== id && !tab) { itemTab = "note"; quizState = {}; }
  if (it.source === "paste" && itemTab === "note" && !tab && curItem?.id !== id) itemTab = "deep";
  curItem = it;
  const n = it.note || {};
  const cats = [...new Set([...(STATE.settings.categories || []), ...(STATE.stats.categories || []).map((c) => c.category)].filter(Boolean))];
  const [stText, stCls] = STATUS[it.status] || [it.status, "gray"];
  const isNote = it.media_type === "note";
  const tabs = [["note", "笔记"], ["deep", "带我精读" + (it.deep ? " ✓" : "")], ["text", isNote ? "原图与文字" : "文字稿"]];
  if (it.aweme_id && !isNote && !["xhs", "bili"].includes(it.platform)) tabs.push(["cmt", "评论"]);
  view.innerHTML = `
    <a class="back" href="javascript:history.length>1?history.back():location.hash='#/favs'">← 返回</a>
    <div class="watch">
      <div class="watch-main${it.aweme_id && !isNote && it.platform !== "bili" ? " has-video" : ""}" id="watchMain">
        ${it.aweme_id && !isNote && it.platform !== "bili"
          ? `<video id="watchVideo" class="watch-video" controls playsinline preload="none"
               ${it.cover ? `poster="${esc(coverUrl(it))}"` : ""} src="/api/items/${it.id}/video"></video>
             <button class="watch-play" id="watchPlay">${ico("play", "ic")}<span>播放原视频</span></button>
             <button class="pm-nav prev" id="watchPrev" data-step="prev" title="上一个（↑）">‹</button>
             <button class="pm-nav next" id="watchNext" data-step="next" title="下一个（↓）">›</button>
             <div class="watch-err" id="watchErr" hidden>
               <b>视频没拉下来</b>
               <span>抖音那边可能限流或这条已失效，点重试；想看原界面就去抖音。</span>
               <div class="row" style="justify-content:center">
                 <button class="btn sm" id="watchRetry">重试</button>
                 ${it.url ? `<a class="btn sm" href="${esc(it.url)}" target="_blank" rel="noopener">抖音里看</a>` : ""}
               </div>
             </div>
`
          : (it.cover
              ? `<img src="${esc(coverUrl(it))}" referrerpolicy="no-referrer" onerror="window.imgFallback(this)">`
              : `<div class="watch-empty">${ico(isNote ? "file" : "play", "ic")}</div>`)}
      </div>
      <aside class="watch-side">
        <h1>${esc(n.title || (it.deep || {}).title || it.title || "未命名")}</h1>
        <div class="meta">
          ${it.status !== "done" ? `<span class="chip ${stCls}">${stText}</span>` : ""}
          ${catChip(it.category || n.category || "未分类")}
          ${it.subcategory ? `<span class="chip gray">${esc(it.subcategory)}</span>` : ""}
          ${n.difficulty ? `<span class="chip gray">${esc(n.difficulty)}</span>` : ""}
        </div>
        <div class="small muted">${it.platform === "xhs" ? "小红书 · " : ""}${esc(it.author || "")}${it.duration ? " · " + fmtDur(it.duration) : ""}${it.published_at ? " · 发布 " + fmtDay(it.published_at) : ""}</div>
        ${it.title && it.title !== n.title && it.source !== "paste" ? `<div class="muted small orig-title" title="点击展开 / 收起">原标题：${esc(it.title)}</div>` : ""}
        ${it.reason ? `<div class="banner warn" style="margin:0">${esc(it.reason)}</div>` : ""}
        ${it.aweme_id && !["xhs", "bili"].includes(it.platform) ? `<div class="side-acts">
          <button id="dyLike" title="点赞 / 取消点赞">${ico("heart", "ic")}<span>赞</span><b class="dy-n" id="dyLikeN"></b></button>
          <button id="dyCollect" title="收藏 / 取消收藏">${ico("star", "ic")}<span>收藏</span><b class="dy-n" id="dyCollectN"></b></button>
          <button id="dyComment" title="看评论 / 发评论">${ico("message", "ic")}<span>评论</span><b class="dy-n" id="dyCommentN"></b></button>
        </div>` : ""}
        ${(() => {
          const busy = ["fetching", "downloading", "transcribing", "extracting"].includes(it.status);
          if (busy) return `<div class="item-live" id="itemLive"><span class="spinner"></span><b>正在处理这条…</b><span class="muted small" id="itemLiveMsg"></span></div>`;
          // 已完成 / 已判定无关（笔记其实已经生成，只需「收进学习库」）就不用再插队
          if (it.status === "done" || it.status === "irrelevant") return "";
          return `<div class="item-jump"><button class="btn primary" id="jumpBtn">${ico("zap")}优先处理这条</button>
            <span class="muted small">点了就插到队首，马上开始，处理完这里直接出笔记</span></div>`;
        })()}
        <div class="side-btns">
          ${it.dsh ? `<button class="btn primary" id="dshCopy">${ico("sparkles")}复制 DSH 指令</button>` : ""}
          ${it.status === "done" ? `<button class="btn ${it.learned ? "" : "accent"}" id="learnBtn">${it.learned ? ico("check") + "已学会（点击取消）" : "标记为已学会"}</button>` : ""}
          ${it.aweme_id && !isNote ? `<button class="btn ghost" id="dyPlay">${ico("play")}大屏播放</button>` : ""}
        </div>
        <div class="side-btns side-mini">
          ${it.url ? `<a class="btn sm" href="${esc(it.url)}" target="_blank" rel="noopener">${isNote ? "原图文" : "原视频"}</a>` : ""}
          <button class="btn sm" id="starBtn">${it.starred ? "已星标" : "星标"}</button>
          <button class="btn sm" id="pdfBtn">PDF</button>
          <a class="btn sm" href="/api/items/${it.id}/md">MD</a>
          ${it.md_path ? `<button class="btn sm" id="revealBtn">文件夹</button>` : ""}
        </div>
        ${it.status === "irrelevant" ? `<button class="btn accent" id="includeBtn">我觉得有用，收进学习库</button>` : ""}
        ${["failed", "skipped", "need_key", "irrelevant", "done"].includes(it.status) && it.transcript && it.source !== "paste"
          ? `<button class="btn sm" id="reBtn">${ico("sparkles")}重新 AI 提炼</button>` : ""}
        ${(it.status === "failed" || it.status === "skipped") && !it.transcript ? `<button class="btn sm" id="retryBtn">${it.status === "skipped" ? "还是处理这条" : "重试"}</button>` : ""}
        ${it.status === "done" ? `<div class="field"><label>分类</label><select id="catSel">${cats.map((c) => `<option ${c === (it.category || n.category) ? "selected" : ""}>${esc(c)}</option>`).join("")}${cats.includes(it.category || n.category) || !(it.category || n.category) ? "" : `<option selected>${esc(it.category || n.category)}</option>`}</select></div>` : ""}
        <div class="row" style="gap:8px;align-self:flex-start;flex-wrap:wrap">
          <button class="btn ghost sm" id="unfavBtn">取消收藏并删除${it.aweme_id && !["xhs", "bili"].includes(it.platform) ? "（抖音也取消）" : ""}</button>
          <button class="btn ghost sm" id="delBtn" style="color:var(--bad)">一键删除</button>
        </div>
      </aside>
    </div>
    <div class="note-area">
      <div class="tabs itabs" id="itabs">${tabs.map(([k, l]) => `<button data-t="${k}" class="${itemTab === k ? "on" : ""}">${l}</button>`).join("")}</div>
      <div id="tabBody"></div>
      <div class="mynote"><div class="row"><b>我的笔记</b><span class="spacer"></span><span class="saved" id="saved"></span></div>
        <textarea id="myNote" placeholder="写下自己的理解、实践结果、想法……（自动保存，也会写进 MD 笔记）">${esc(it.my_note)}</textarea></div>
    </div>`;



  $$("#itabs button").forEach((b) => b.onclick = () => { itemTab = b.dataset.t; $$("#itabs button").forEach((x) => x.classList.toggle("on", x === b)); renderTab(); });
  renderTab();

  // 页面顶上的播放器：走本地代理，能拖进度，不会像抖音 iframe 那样白屏
  warmNeighbors(it.id);
  const wv = $("#watchVideo");
  if (wv) {
    const box = wv.closest(".watch-main");
    // 竖屏视频按视频自己的比例铺满高度（之前误删了，导致又变回小黑框）
    const applyRatio = (vw2, vh2) => {
      if (!box || !vw2 || !vh2) return;
      const portrait = vh2 > vw2;
      box.classList.toggle("portrait", portrait);
      box.style.aspectRatio = `${vw2} / ${vh2}`;
      if (portrait) {
        box.style.height = "82vh";
        box.style.maxHeight = "82vh";
        box.style.width = "auto";
        box.style.maxWidth = "100%";
      } else {
        box.style.height = "";
        box.style.maxHeight = "";
        box.style.width = "100%";
        box.style.maxWidth = "";
      }
    };
    const fitBox = () => applyRatio(wv.videoWidth, wv.videoHeight);
    window.__watchFit = fitBox;
    wv.addEventListener("loadedmetadata", fitBox);
    if (wv.readyState >= 1) fitBox();
    if (!wv.videoWidth && it.cover) {
      const im = new Image();
      im.onload = () => { if (!wv.videoWidth) applyRatio(im.naturalWidth, im.naturalHeight); };
      im.src = it.cover;
    }
    const btn = () => $("#watchPlay");
    const start = () => {
      const b = btn();
      if (b) b.hidden = true;
      // 浏览器有时会按自动播放策略把元素静音，用户点了就一定要出声
      try { wv.muted = false; if (!wv.volume) wv.volume = 1; } catch (e) {}
      wv.play().catch(() => { const b2 = btn(); if (b2) b2.hidden = false; });
    };
    btn() && (btn().onclick = start);
    wv.addEventListener("playing", () => {
      const b = btn(); if (b) b.hidden = true;
      // 播了两秒还没有音频数据 → 多半这条视频本身就是无声的
      setTimeout(() => {
        try {
          if (wv.webkitAudioDecodedByteCount === 0 && !wv.dataset.noaudio) {
            wv.dataset.noaudio = "1";
            toast("这条视频本身没有声音（文件里没有音轨）", 4000);
          }
        } catch (e) {}
      }, 2000);
    });
    wv.addEventListener("error", () => {
      const e = $("#watchErr");
      if (e) e.hidden = false;
      const b = btn();
      if (b) b.hidden = true;
    });
    const retry = $("#watchRetry");
    if (retry) retry.onclick = () => {
      $("#watchErr").hidden = true;
      const b = btn();
      if (b) b.hidden = false;
      wv.src = `/api/items/${id}/video?t=${Date.now()}`;
      try { wv.load(); } catch (e) {}
      start();
    };
  }

  const act = (action, extra = {}) => api(`/api/items/${id}/action`, { action, ...extra });
  $("#learnBtn") && ($("#learnBtn").onclick = async () => { await act("learned", { value: !it.learned }); toast(it.learned ? "已取消" : "太棒了，又学会一条 🎉"); refreshState(); renderItem(id, itemTab); });
  $("#starBtn").onclick = async () => { await act("star", { value: !it.starred }); renderItem(id, itemTab); };
  $("#dshCopy") && ($("#dshCopy").onclick = () => copyText(it.dsh, "已复制，粘到 DSH 就行"));
  $("#dyPlay") && ($("#dyPlay").onclick = () => openPlayer(id, n.title || it.title || "", it.aweme_id || ""));
  $("#dyLike") && ($("#dyLike").onclick = () => { dyItem = id; dyAct("like"); });
  $("#dyCollect") && ($("#dyCollect").onclick = () => { dyItem = id; dyAct("collect"); });
  $("#dyComment") && ($("#dyComment").onclick = () => {
    itemTab = "cmt";
    $$("#itabs button").forEach((x) => x.classList.toggle("on", x.dataset.t === "cmt"));
    renderTab();
  });
  if (it.aweme_id && !isNote && !["xhs", "bili"].includes(it.platform)) loadDyStats(it.id);
  $("#pdfBtn").onclick = () => window.open(`/print?ids=${id}`, "_blank");
  $("#revealBtn") && ($("#revealBtn").onclick = () => api("/api/open", { what: "item", id }).catch((e) => toast(e.message)));
  $("#includeBtn") && ($("#includeBtn").onclick = async () => { await act("include"); toast("已收进学习库"); refreshState(); renderItem(id, itemTab); });
  $("#reBtn") && ($("#reBtn").onclick = async () => { await act("reextract"); toast("已加入队列，稍等片刻"); location.hash = "#/process"; });
  $("#jumpBtn") && ($("#jumpBtn").onclick = async () => {
    const b = $("#jumpBtn");
    b.disabled = true; b.textContent = "正在插队…";
    try {
      await api(`/api/items/${it.id}/action`, { action: "jump" });
      toast("已插到队首，马上处理这条");
      watchItem(it.id);
      renderItem(it.id, tab);
    } catch (e) {
      toast(e.message, 4000);
      b.disabled = false; b.innerHTML = "优先处理这条";
    }
  });
  $("#retryBtn") && ($("#retryBtn").onclick = async () => { await act("retry"); toast("已重新加入队列"); location.hash = "#/process"; });
  $("#catSel") && ($("#catSel").onchange = async (e) => { await act("category", { value: e.target.value }); toast("分类已修改"); refreshState(); });
  $("#delBtn").onclick = async () => {
    await act("delete"); toast("已移进回收站（能恢复）"); location.hash = "#/favs";
  };
  $("#unfavBtn") && ($("#unfavBtn").onclick = async () => {
    if (!confirm("取消这条收藏？抖音里也会取消，本地缓存删掉，记录进回收站。")) return;
    await act("unfavorite"); toast("已取消收藏，缓存已删除"); location.hash = "#/favs";
  });
  let t; $("#myNote").addEventListener("input", (e) => {
    $("#saved").textContent = "编辑中…"; clearTimeout(t);
    t = setTimeout(async () => { await act("note", { text: e.target.value }); $("#saved").textContent = "已保存"; }, 800);
  });
}

function renderTab() {
  const it = curItem, el = $("#tabBody");
  if (!el) return;
  el.classList.remove("fade-in"); void el.offsetWidth; el.classList.add("fade-in");
  if (itemTab === "note") {
    el.innerHTML = (it.images?.length ? galleryHtml(it.images, it.updated_at) : "") +
      (it.note ? noteBody(it) + dshHtml(it)
        : `<div class="empty" style="padding:30px">这条还没有笔记。${it.transcript ? "可以直接去「带我精读」。" : ""}</div>`);
    const dc = $("#dshCopy2");
    if (dc) dc.onclick = () => copyText(it.dsh, "已复制，粘到 DSH 就行");
    bindGallery(el, it.images);
    $$("[data-reveal]", el).forEach((b) => b.onclick = () => { b.closest(".q").classList.add("open"); b.remove(); });
  } else if (itemTab === "text") {
    renderTextTab(el);
  } else if (itemTab === "cmt") {
    renderCommentsTab(el);
  } else {
    renderDeepTab(el);
  }
}

/* 抖音评论：走后台那个已登录的浏览器去读取，第一次要几秒 */
async function renderCommentsTab(el) {
  const it = curItem;
  if (!it?.aweme_id) { el.innerHTML = `<div class="empty" style="padding:30px">这条没有抖音来源</div>`; return; }
  el.innerHTML = `<div class="cmt-head">
      <b>抖音评论</b><span class="muted small" id="cmtStat"></span><span class="spacer"></span>
      <button class="btn sm" id="cmtSend">写评论</button>
    </div>
    <div class="cmt-list" id="cmtList"><div class="muted small" style="padding:14px">正在从抖音读评论…（第一次要几秒）</div></div>`;
  $("#cmtSend").onclick = () => openComment(it.id, (it.note || {}).title || it.title || "");
  try {
    const r = await api(`/api/items/${it.id}/comments`);
    const list = r.comments || [];
    const s = r.stats || {};
    const st = $("#cmtStat");
    if (st) st.textContent = s.comment ? `共 ${fmtCnt(s.comment)} 条 · 赞 ${fmtCnt(s.digg || 0)} · 收藏 ${fmtCnt(s.collect || 0)}` : "";
    const box = $("#cmtList");
    if (!box) return;
    if (!list.length) {
      box.innerHTML = `<div class="empty" style="padding:26px">没读到评论（可能被抖音限流，或者这条没人评论）</div>`;
      return;
    }
    box.innerHTML = list.map((c) => `<div class="cmt">
        ${c.avatar ? `<img class="cmt-av" src="${esc(c.avatar)}" referrerpolicy="no-referrer" loading="lazy">`
          : `<span class="cmt-av"></span>`}
        <div class="cmt-body">
          <div class="cmt-name">${esc(c.user)}${c.likes ? `<b class="cmt-like">♥ ${fmtCnt(c.likes)}</b>` : ""}</div>
          <div class="cmt-text">${esc(c.text)}</div>
          ${c.replies ? `<div class="muted small">${c.replies} 条回复</div>` : ""}
        </div>
      </div>`).join("");
  } catch (e) {
    const box = $("#cmtList");
    if (box) box.innerHTML = `<div class="empty" style="padding:26px">${esc(e.message)}<br>
      <span class="muted small">点「原视频」去抖音里看评论更稳</span></div>`;
  }
}

const fmtCnt = (n) => {
  n = Number(n) || 0;
  return n >= 10000 ? (n / 10000).toFixed(1).replace(/\.0$/, "") + "万" : String(n);
};

async function loadDyStats(id) {
  try {
    const r = await api(`/api/items/${id}/dycheck`);
    const s = r.stats || {};
    const put = (sel, v) => { const el = $(sel); if (el) el.textContent = v == null ? "" : fmtCnt(v); };
    put("#dyLikeN", s.digg);
    put("#dyCollectN", s.collect);
    put("#dyCommentN", s.comment);
    if (s.liked) $("#dyLike")?.classList.add("on");
  } catch (e) { /* 读不到就不显示数字，不打扰 */ }
}

function renderTextTab(el, focusSec) {
  const it = curItem;
  if (!it.transcript) { el.innerHTML = `<div class="empty" style="padding:30px">还没有文字稿</div>`; return; }
  const segs = it.segments || [];
  if (it.images?.length) {
    const parts = {}; let intro = "";
    it.transcript.split(/\n\n(?=【)/).forEach((blk) => {
      const m = blk.match(/^【图(\d+)】\n?([\s\S]*)$/);
      if (m) parts[+m[1]] = m[2]; else intro += blk.replace(/^【正文】\n?/, "") + "\n";
    });
    el.innerHTML = `<div class="row" style="margin:14px 0 10px"><span class="muted small">图文 · ${it.images.length} 张图 · 图片里的文字由本机识别，可能有错字</span>
        <span class="spacer"></span><button class="btn sm" id="cpTr">复制全部文字</button></div>
      ${intro.trim() ? `<div class="summary" style="margin-bottom:14px;white-space:pre-wrap">${esc(intro.trim())}</div>` : ""}
      <div class="ocr-list">${it.images.map((src, i) => `<div class="ocr-row">
        <img src="/files/${encodeURI(src)}?v=${Math.floor((it.updated_at || 0) * 1000)}" data-g="${i}" loading="lazy">
        <div class="ocr-text"><div class="muted small">图 ${i + 1}</div>${parts[i + 1] ? esc(parts[i + 1]) : '<span class="muted">（这张图没有识别到文字）</span>'}</div></div>`).join("")}</div>`;
    $("#cpTr").onclick = () => copyText(it.transcript, "文字已复制");
    bindGallery(el, it.images);
    return;
  }
  el.innerHTML = `<div class="row" style="margin:14px 0 10px"><span class="muted small">${it.transcript.length} 字${segs.length ? " · 在精读大纲里点时间，会跳到这里对应的位置" : ""}</span>
      <span class="spacer"></span><button class="btn sm" id="cpTr">复制全文</button></div>
    ${segs.length ? `<div class="tsegs">${segs.map((s, i) => `<div class="tseg" id="seg-${i}" data-start="${s.start}"><span class="ts">${fmtTs(s.start)}</span><span>${esc(s.text)}</span></div>`).join("")}</div>`
      : `<div class="transcript" style="max-height:none">${esc(it.transcript)}</div>`}`;
  $("#cpTr").onclick = () => copyText(it.transcript, "文字稿已复制");
  if (focusSec != null && segs.length) {
    let idx = 0;
    segs.forEach((s, i) => { if (s.start <= focusSec + 0.5) idx = i; });
    const row = $(`#seg-${idx}`);
    if (row) { row.classList.add("hl"); row.scrollIntoView({ block: "center", behavior: "smooth" }); setTimeout(() => row.classList.remove("hl"), 2500); }
  }
}

function deepModelName() {
  const s = STATE.settings;
  return s.deep_same ? s.model : s.deep_model;
}

function renderDeepTab(el) {
  const it = curItem, d = it.deep, chat = it.chat || {};
  const busy = deepBusy(it.id);
  if (busy) {
    const ds = STATE.deep || {};
    const mine = ds.item_id === it.id;
    el.innerHTML = `<div class="card deep-run" id="deepRun" style="margin-top:16px">
        <div class="row"><div class="spinner"></div><b>${mine ? esc(ds.label || "精读中") : "排队等待精读……"}</b><span class="spacer"></span>
        <span class="muted small">${mine ? `第 ${ds.step}/${ds.steps} 步 · ${fmtEta(ds.eta)}` : ""}</span></div>
        <div class="bar" style="margin-top:10px"><i style="width:${mine ? ds.pct : 2}%"></i></div>
        <div class="muted small" style="margin-top:8px">用 ${esc(deepModelName())} 生成核心结论、章节大纲、概念、理解检查题、测验、Anki 卡片和思维导图。可以先去看别的，好了会自动显示。</div></div>`;
    return;
  }
  if (!d) {
    el.innerHTML = `
      ${chat.deep_error ? `<div class="banner warn" style="margin-top:14px">上次精读失败：${esc(chat.deep_error)}</div>` : ""}
      <div class="card" style="margin-top:16px">
        <h2>有人带着读</h2>
        <p class="muted">让 AI 像老师一样带你读这段内容：先给 5 句核心结论，再按章节列大纲（带时间戳，点击跳到原文），解释关键概念；
          然后不直接给答案，用提问检查你是否真懂（你写回答，AI 点评）；最后出 10 道测验题，做成 Anki 卡片，画思维导图。</p>
        <p class="muted small">使用模型：<b>${esc(deepModelName() || "未设置")}</b>（在设置 → 精读 里可以换成 Claude 等）。文稿很长时会自动分段预读再合并。</p>
        <div class="row" style="margin-top:12px">
          <button class="btn primary" id="deepGo" ${it.transcript ? "" : "disabled"}>开始精读</button>
          <button class="btn" id="copyPrompt" ${it.transcript ? "" : "disabled"}>${ico("copy")}复制提示词+文稿（粘贴到豆包 / Kimi / 千问 / Claude）</button>
        </div>
        ${it.transcript ? "" : `<div class="muted small" style="margin-top:8px">这条还没有文字稿，处理完才能精读。</div>`}
      </div>`;
    $("#deepGo") && ($("#deepGo").onclick = startDeep);
    $("#copyPrompt") && ($("#copyPrompt").onclick = copyPrompt);
    return;
  }

  const checks = chat.checks || {};
  const qs = quizState[it.id] || (quizState[it.id] = {});
  el.innerHTML = `
    ${chat.deep_error ? `<div class="banner warn" style="margin-top:14px">上次重新精读失败：${esc(chat.deep_error)}（下面是之前的结果）</div>` : ""}
    <div class="row deep-head"><span class="muted small">由 ${esc(d.model || "")} 生成${d.chunks > 1 ? ` · 分 ${d.chunks} 段预读后合并` : ""}</span><span class="spacer"></span>
      <button class="btn sm" id="copyPrompt">${ico("copy")}复制给其他 AI</button><button class="btn sm ghost" id="deepRedo">重新精读</button></div>

    ${d.conclusions.length ? `<section><h2>核心结论</h2><ol class="points">${d.conclusions.map((c) => `<li>${esc(c)}</li>`).join("")}</ol></section>` : ""}

    ${d.mindmap ? `<section><h2>思维导图</h2>
      <div class="row" style="margin-bottom:10px"><a class="btn sm" href="/api/items/${it.id}/mindmap.html" target="_blank">${ico("external")}新窗口全屏</a>
        <a class="btn sm" href="/api/items/${it.id}/mindmap.html?download=1">${ico("download")}下载网页</a>
        <button class="btn sm" id="cpMind">${ico("copy")}复制 Markmap 文本</button></div>
      <iframe class="mindmap" src="/api/items/${it.id}/mindmap.html"></iframe></section>` : ""}

    ${d.outline.length ? `<section><h2>章节大纲</h2><div class="outline">${d.outline.map((o) => `
      <div class="ol-item"><div class="ol-head">${o.time ? `<button class="ts-btn" data-sec="${o.sec ?? ""}" title="跳到文字稿这里">${esc(o.time)}</button>` : ""}<b>${esc(o.title)}</b></div>
      ${o.points.length ? `<ul>${o.points.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>` : ""}</div>`).join("")}</div></section>` : ""}

    ${d.concepts.length ? `<section><h2>关键概念与术语</h2><div class="kv">${d.concepts.map((c) => `<div><b>${esc(c.term)}</b><span>${esc(c.explain)}</span></div>`).join("")}</div></section>` : ""}

    ${d.check_questions.length ? `<section><h2>你真的懂了吗？</h2>
      <p class="muted small" style="margin-top:-4px">不直接给答案。用自己的话回答，老师会点评并继续追问。</p>
      ${d.check_questions.map((q, i) => { const c = checks[i]; return `
        <div class="cq card" data-i="${i}">
          <div><b>${i + 1}. ${esc(q.q)}</b></div>
          <div class="row" style="margin:8px 0"><button class="btn sm ghost" data-hint>${ico("bulb")}给点提示</button>${c ? `<button class="btn sm ghost" data-key>${ico("eye")}看参考要点</button>` : ""}</div>
          <div class="hint-box" hidden>${ico("bulb")}${esc(q.hint)}</div>
          <div class="key-box" hidden>${ico("eye")}${esc(q.key)}</div>
          <textarea rows="3" placeholder="用自己的话写下你的理解……">${esc(c?.answer || "")}</textarea>
          <div class="row" style="margin-top:8px"><span class="spacer"></span><button class="btn sm" data-submit>${c ? "再答一次" : "提交给老师"}</button></div>
          <div class="feedback" ${c ? "" : "hidden"}>${c ? mdLite(c.feedback) : ""}</div>
        </div>`; }).join("")}</section>` : ""}

    ${d.quiz.length ? `<section><h2>测验（${d.quiz.length} 题）</h2><div id="quizBox"></div></section>` : ""}

    ${d.anki.length ? `<section><h2>Anki 卡片（${d.anki.length} 张）</h2>
      <div class="row" style="margin-bottom:10px"><a class="btn sm" href="/api/items/${it.id}/anki.txt">${ico("download")}下载 .txt</a>
        <button class="btn sm" id="cpAnki">${ico("copy")}复制「问题⇥答案」</button>
        <span class="muted small">Anki 里选「文件 → 导入」，分隔符选 Tab</span></div>
      <table class="anki"><thead><tr><th>问题</th><th>答案</th></tr></thead><tbody>
        ${d.anki.map((c) => `<tr><td>${esc(c.q)}</td><td>${esc(c.a)}</td></tr>`).join("")}</tbody></table></section>` : ""}



    <section><h2>问老师</h2>
      <div class="asklog" id="askLog">${(chat.ask || []).map((a) => `<div class="qa"><div class="q-me">${esc(a.q)}</div><div class="a-ai">${mdLite(a.a)}</div></div>`).join("")}</div>
      <div class="row ask-row"><input id="askIn" class="search" placeholder="哪里没看懂？随便问，比如「第二章那个方法具体怎么做？」"><button class="btn primary" id="askBtn">提问</button></div>
    </section>`;

  $("#copyPrompt").onclick = copyPrompt;
  $("#deepRedo").onclick = () => { if (confirm("重新精读会覆盖现在的结果（答题记录保留），确定？")) startDeep(); };
  $$(".ts-btn", el).forEach((b) => b.onclick = () => {
    const sec = b.dataset.sec === "" ? null : +b.dataset.sec;
    if (!(it.segments || []).length) return toast("这条文字稿没有时间信息");
    itemTab = "text"; $$("#itabs button").forEach((x) => x.classList.toggle("on", x.dataset.t === "text"));
    renderTextTab($("#tabBody"), sec);
  });
  $$(".cq", el).forEach((card) => {
    const i = +card.dataset.i;
    $("[data-hint]", card).onclick = () => { $(".hint-box", card).hidden = false; };
    // 只有写了回答，「提交」才变成主按钮：一页里不会同时有六个蓝按钮
    const ta = $("textarea", card), sb = $("[data-submit]", card);
    const syncBtn = () => sb.classList.toggle("primary", !!ta.value.trim() && !curItem.chat?.checks?.[i]);
    ta.addEventListener("input", syncBtn); syncBtn();
    $("[data-key]", card) && ($("[data-key]", card).onclick = () => { $(".key-box", card).hidden = false; });
    $("[data-submit]", card).onclick = async (e) => {
      const ans = $("textarea", card).value.trim();
      if (!ans) return toast("先写下你的回答");
      const btn = e.target; btn.disabled = true; btn.textContent = "老师在看……";
      const fb = $(".feedback", card); fb.hidden = false; fb.innerHTML = `<span class="muted">思考中……</span>`;
      try {
        const r = await api(`/api/items/${it.id}/check`, { idx: i, answer: ans });
        fb.innerHTML = mdLite(r.feedback);
        (curItem.chat ||= {}).checks ||= {}; curItem.chat.checks[i] = r;
        if (!$("[data-key]", card)) $("[data-hint]", card).insertAdjacentHTML("afterend", `<button class="btn sm ghost" data-key>${ico("eye")}看参考要点</button>`);
        $("[data-key]", card).onclick = () => { $(".key-box", card).hidden = false; };
      } catch (err) { fb.innerHTML = `<span style="color:var(--bad)">${esc(err.message)}</span>`; }
      btn.disabled = false; btn.textContent = "再答一次";
    };
  });
  if (d.quiz.length) renderQuiz(it, d.quiz, qs);
  $("#cpAnki") && ($("#cpAnki").onclick = () => copyText(d.anki.map((c) => `${c.q}\t${c.a}`).join("\n"), "Anki 卡片已复制"));
  $("#cpMind") && ($("#cpMind").onclick = () => copyText(d.mindmap, "Markmap 文本已复制"));
  const ask = async () => {
    const q = $("#askIn").value.trim(); if (!q) return;
    const log = $("#askLog"); $("#askIn").value = "";
    log.insertAdjacentHTML("beforeend", `<div class="qa"><div class="q-me">${esc(q)}</div><div class="a-ai muted" id="pendingA">老师在想……</div></div>`);
    $("#askBtn").disabled = true;
    try { const r = await api(`/api/items/${it.id}/ask`, { q }); $("#pendingA").outerHTML = `<div class="a-ai">${mdLite(r.a)}</div>`;
      ((curItem.chat ||= {}).ask ||= []).push(r);
    } catch (e) { $("#pendingA").outerHTML = `<div class="a-ai" style="color:var(--bad)">${esc(e.message)}</div>`; }
    $("#askBtn").disabled = false;
  };
  $("#askBtn").onclick = ask;
  $("#askIn").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.isComposing) ask(); });
}

function renderQuiz(it, quiz, qs) {
  const box = $("#quizBox"); if (!box) return;
  const answered = Object.keys(qs).length;
  const score = Object.entries(qs).filter(([i, a]) => quiz[i] && a === quiz[i].answer).length;
  box.innerHTML = quiz.map((q, i) => {
    const pick = qs[i];
    return `<div class="quiz-q card" data-i="${i}"><b>${i + 1}. ${esc(q.q)}</b>
      <div class="opts">${q.options.map((o, j) => {
        let cls = "";
        if (pick !== undefined) cls = j === q.answer ? "right" : (j === pick ? "wrong" : "dim");
        return `<button class="opt ${cls}" data-j="${j}" ${pick !== undefined ? "disabled" : ""}>${"ABCDEFGH"[j]}. ${esc(o)}</button>`; }).join("")}</div>
      ${pick !== undefined ? `<div class="explain">${pick === q.answer ? `<span class="ok-t">${ico("checkCircle")}答对了</span>` : `<span class="bad-t">${ico("xCircle")}正确答案是</span> ${"ABCDEFGH"[q.answer]}`}${q.explain ? "　" + esc(q.explain) : ""}</div>` : ""}</div>`;
  }).join("") + `<div class="row quiz-score"><b>${answered === quiz.length ? `${ico("trophy")} 完成！得分 ${score} / ${quiz.length}` : `已答 ${answered} / ${quiz.length}，答对 ${score} 题`}</b>
      <span class="spacer"></span>${answered ? `<button class="btn sm" id="quizReset">重做</button>` : ""}</div>`;
  $$(".opt", box).forEach((b) => b.onclick = () => {
    const i = +b.closest(".quiz-q").dataset.i; qs[i] = +b.dataset.j;
    const y = window.scrollY; renderQuiz(it, quiz, qs); window.scrollTo(0, y);
    if (Object.keys(qs).length === quiz.length) {
      const sc = Object.entries(qs).filter(([k, a]) => a === quiz[k].answer).length;
      api(`/api/items/${it.id}/quiz`, { score: sc, total: quiz.length }).catch(() => {});
    }
  });
  $("#quizReset") && ($("#quizReset").onclick = () => { for (const k in qs) delete qs[k]; renderQuiz(it, quiz, qs); });
}

async function startDeep() {
  const it = curItem;
  try {
    const r = await api(`/api/items/${it.id}/deep`, {});
    wasDeepBusy = true;
    toast(`开始精读（${r.model || ""}），长文稿需要几分钟`);
    await refreshState(); itemTab = "deep"; renderTab();
  } catch (e) { toast(e.message, 4000); }
}

async function copyPrompt() {
  try { const r = await api(`/api/items/${curItem.id}/prompt`); copyText(r.text, "提示词和文稿已复制，可以粘贴到任意 AI 对话里"); }
  catch (e) { toast(e.message); }
}

/* ---------------------------------------------------------------- 添加与处理 */
function openAdd() { $("#addModal").hidden = false; setTimeout(() => $("#addText").focus(), 30); }
$$("#addModal [data-close]").forEach((b) => b.addEventListener("click", () => ($("#addModal").hidden = true)));
$("#addModal").addEventListener("click", (e) => { if (e.target.id === "addModal") e.target.hidden = true; });
// 原标题点一下展开 / 收起
document.addEventListener("click", (e) => { const o = e.target.closest(".orig-title"); if (o) o.classList.toggle("open"); });
$("#addSubmit").onclick = async () => {
  const text = $("#addText").value;
  try {
    const r = await api("/api/links", { text });
    $("#addText").value = ""; $("#addModal").hidden = true;
    toast(r.added ? `找到 ${r.found} 个链接，新增 ${r.added} 条，开始处理` : `找到 ${r.found} 个链接，都已经添加过了`);
    location.hash = "#/process";
  } catch (e) { toast(e.message, 4000); }
};

/* ---------------------------------------------------------------- 新手教程 */
async function renderWelcome() {
  view.innerHTML = `
    <div class="welcome">
      <div class="welcome-hero">
        <div class="mark big">书</div>
        <h1>收藏变笔记</h1>
        <p class="muted">把抖音、小红书、B站的收藏，自动变成能读、能学、能复习的笔记。</p>
      </div>

      <div class="steps">
        <div class="step-card"><b class="n">1</b><h3>填 AI Key</h3>
          <p>设置 → AI 提炼，填一个模型服务的 Key（DeepSeek / 通义 / OpenAI 都行）。它负责把文字稿提炼成笔记、自动分类。</p></div>
        <div class="step-card"><b class="n">2</b><h3>登录账号</h3>
          <p>添加与处理 → 「登录抖音」「登录小红书」扫码即可（各一次，登录态存在本机）。<b>B站不用登录</b>：把视频地址粘进「粘贴分享链接」就解析，需要更高清晰度时再点「登录 B 站」。</p></div>
        <div class="step-card"><b class="n">3</b><h3>同步收藏</h3>
          <p>抖音/小红书点一次「同步收藏」后就是<b>全自动</b>：每 10 分钟自动同步、有新条目自动开跑。B站按需手动粘贴。流程：读取信息 → 下载 → 转文字 / 读画面文字 → AI 提炼 → 自动分类。</p></div>
        <div class="step-card"><b class="n">4</b><h3>开始学习</h3>
          <p>左侧「汇总 / 抖音 / 小红书」三个视图浏览收藏；点开任意一条看笔记；学习库按分类复习；本地缓存里能直接播放原视频。</p></div>
      </div>

      <div class="card welcome-tips">
        <h2>几个好用的小功能</h2>
        <ul>
          <li><b>视频上一/下一个：</b>详情页或播放器里点左右箭头，或直接按 <kbd>↑</kbd> <kbd>↓</kbd>；<kbd>Esc</kbd> 退出返回列表。</li>
          <li><b>右键卡片：</b>取消收藏并删除（平台取消 + 清本地缓存 + 进回收站）、播放、复制原链接。</li>
          <li><b>顶部搜索：</b>随时搜标题和作者，输入即筛。</li>
          <li><b>三套外观：</b>左侧栏底部的小圆钮（或设置 → 外观）切换 浅色 / 纯白 / 深色。</li>
          <li><b>今日汇总：</b>添加与处理页顶部，看今天拆了多少、都进了哪些分类。</li>
          <li><b>没有跳过：</b>所有内容都会出笔记（没旁白就按画面文字、标题、简介兜底），不满意的直接删。</li>
          <li><b>数据都在本机：</b>笔记是 Markdown，存在你的笔记文件夹；缓存视频在 data/media，可随时清空。</li>
        </ul>
      </div>

      <div class="row welcome-actions">
        <a class="btn" href="#/welcome" hidden></a>
        <button class="btn" id="wlSkip">先随便看看</button>
        <span class="spacer"></span>
        <button class="btn primary" id="wlStart">开始使用</button>
      </div>
    </div>`;

  const done = async (go) => {
    try { await api("/api/settings", { welcome_done: true }); } catch (e) {}
    if (STATE && STATE.settings) STATE.settings.welcome_done = true;
    location.hash = go;
  };
  $("#wlStart").onclick = () => done(STATE.settings.api_key_set ? "#/favs" : "#/settings");
  $("#wlSkip").onclick = () => done("#/favs");
}

/* ---------------------------------------------------------------- 本地缓存 */
async function loadCachePage() {
  let c;
  try { c = await api("/api/cache"); } catch { return; }
  if (!$("#cachePage")) return;
  const max = c.max_bytes || 0, used = c.bytes || 0;
  const al = c.all || {};
  const acts = c.active || [];
  const files = c.files || [];
  $("#cN1").textContent = c.count || 0;
  $("#cN2").textContent = fmtBytes(used);
  $("#cN3").textContent = al.on ? `${al.done}/${al.total}` : acts.length;
  $("#cN4").textContent = al.on ? Math.max(0, al.total - al.done) : "—";
  $("#cNums").textContent = `${fmtBytes(used)} / ${fmtBytes(max)}`;
  $("#cBar").style.width = (max ? Math.min(100, used * 100 / max) : 0).toFixed(1) + "%";
  const btn = $("#cAll");
  if (btn) {
    btn.dataset.on = al.on ? "1" : "";
    btn.textContent = al.on ? `停止缓存（${al.done}/${al.total}）` : "缓存全部视频";
    btn.classList.toggle("primary", !!al.on);
  }
  $("#cHint").textContent = al.total
    ? `全部视频：已缓存 ${al.done} / ${al.total}${al.failed ? ` · 失败 ${al.failed}` : ""}${al.on ? " · 进行中" : ""}`
    : "点「缓存全部视频」把收藏里所有视频都存到本地，之后点播放就是本地文件，秒开。";

  $("#cActive").innerHTML = acts.length
    ? acts.map((a) => {
        const p = a.total ? Math.min(100, a.pct || 0) : 0;
        return `<div class="dl-item">
          <div class="row"><span class="dl-name">${esc((a.title || "视频").slice(0, 60))}</span><span class="spacer"></span>
            <span class="muted small">${a.total ? `${fmtBytes(a.done)} / ${fmtBytes(a.total)}` : fmtBytes(a.done)}${a.speed ? ` · ${fmtBytes(a.speed)}/s` : ""}</span></div>
          <div class="bar sm" style="margin-top:6px"><i style="width:${p}%"></i></div></div>`;
      }).join("")
    : `<div class="muted small">现在没有正在下载的视频</div>`;

  $("#cCount").textContent = files.length ? `（${files.length} 个）` : "";
  // 列表没变化就不重画，免得每秒刷新把点击和滚动打断
  const sig = files.map((f) => f.name + ":" + f.bytes).join("|");
  if (sig === window.__cacheSig) return;
  window.__cacheSig = sig;
  $("#cFiles").innerHTML = files.length ? files.map((f) => `
    <div class="trash-row">
      ${f.cover ? `<img class="trash-thumb" src="${esc(f.cover)}" referrerpolicy="no-referrer" onerror="this.removeAttribute('src')">` : `<div class="trash-thumb"></div>`}
      <div class="trash-meta">
        <div class="trash-t">${esc((f.title || f.name).slice(0, 90))}</div>
        <div class="muted small">${fmtBytes(f.bytes)}${f.duration ? " · " + fmtDur(f.duration) : ""}${f.platform === "xhs" ? " · 小红书" : ""} · ${fmtDay(f.mtime)}</div>
      </div>
      ${f.id ? `<button class="btn sm cf-play" data-id="${f.id}" data-title="${esc((f.title || "").slice(0, 60))}">播放</button>` : ""}
      <button class="btn sm cf-del" data-name="${esc(f.name)}" style="color:var(--bad)">删除</button>
    </div>`).join("") : emptyHtml("download", "还没有缓存的视频", "点右上角「缓存全部视频」，把收藏里的视频都存到本地。");

  $$(".cf-play", view).forEach((b) => b.onclick = (e) => {
    e.preventDefault(); e.stopPropagation();
    openPlayer(+b.dataset.id, b.dataset.title || "");
  });
  $$(".cf-del", view).forEach((b) => b.onclick = async (e) => {
    e.preventDefault(); e.stopPropagation();
    if (!confirm("删掉这个本地文件？下次播放要重新下载。")) return;
    await api("/api/cache/del", { name: b.dataset.name });
    toast("已删除"); window.__cacheSig = ""; loadCachePage();
  });
}

async function renderCache() {
  view.innerHTML = `
    <div class="head"><div><h1>本地缓存</h1>
      <div class="muted">下载过的视频都放在这里，点「播放」直接读本地文件，秒开、不卡、不费流量。</div></div>
      <div class="spacer"></div>
      <button class="btn" id="cOpen">打开文件夹</button>
      <button class="btn" id="cClear">清空缓存</button>
      <button class="btn primary" id="cAll" data-on="">缓存全部视频</button>
    </div>
    <div class="card fav-stat" id="cachePage">
      <div class="stat"><b id="cN1">—</b><span>个视频已缓存</span></div>
      <div class="stat"><b id="cN2">—</b><span>占用空间</span></div>
      <div class="stat"><b id="cN3">—</b><span>正在下载</span></div>
      <div class="stat"><b id="cN4">—</b><span>还没缓存</span></div>
    </div>
    <div class="card" style="margin-bottom:16px;padding:18px 20px">
      <div class="row" style="margin-bottom:10px"><h2 style="margin:0;font-size:16px">缓存占用</h2><span class="spacer"></span><span class="muted small" id="cNums"></span></div>
      <div class="bar big"><i id="cBar" style="width:0%"></i></div>
      <div class="muted small" id="cHint" style="margin-top:10px"></div>
      <div id="cActive" style="margin-top:16px"></div>
    </div>
    <div class="card" style="padding:6px 20px">
      <h2 style="margin:16px 0 4px;font-size:17px">已缓存的视频 <span class="muted small" id="cCount"></span></h2>
      <div id="cFiles"></div>
    </div>`;

  $("#cOpen").onclick = () => api("/api/open", { what: "media" }).catch((e) => toast(e.message));
  $("#cClear").onclick = async () => {
    if (!confirm("清空本地视频缓存？已经转好文字的笔记不受影响，只是下次播放要重新下载。")) return;
    const r = await api("/api/cache/clear", {});
    toast(`已清空，释放 ${fmtBytes(r.freed || 0)}`);
    window.__cacheSig = ""; loadCachePage();
  };
  $("#cAll").onclick = async () => {
    const on = $("#cAll").dataset.on === "1";
    if (on) {
      await api("/api/cache/all", { on: false });
      toast("已停止全部缓存");
    } else {
      const r = await api("/api/cache/all", { on: true });
      toast(r.queued ? `开始缓存全部视频，还剩 ${r.queued} 条没下` : "所有视频都已经在本地了");
    }
    loadCachePage();
  };
  await loadCachePage();
  clearInterval(window.__cacheTimer);
  window.__cacheTimer = setInterval(() => {
    if (!$("#cachePage")) { clearInterval(window.__cacheTimer); return; }
    loadCachePage();
  }, 1200);
}

async function renderProcess() {
  await refreshState();
  const rt = route();
  if (rt.tab && TABS.some((t) => t[0] === rt.tab)) procTab = rt.tab;
  const s = STATE.settings;
  view.innerHTML = `
    <div class="acct-bar" id="acctBar">
      <span class="acct" id="acctDouyin"><i class="dot ok"></i><b>抖音</b><em>检测中…</em></span>
      <span class="acct" id="acctXhs"><i class="dot ok"></i><b>小红书</b><em>检测中…</em></span>
      <span class="spacer"></span>
      <button class="btn sm" id="acctCheck">刷新登录状态</button>
    </div>
    <div class="head"><div><h1>添加与处理</h1><div class="muted">视频：读取信息 → 下载 → 本地转文字 → AI 提炼；图文：下载图片 → 识别图片文字 → AI 提炼</div></div></div>
    ${bannerHtml()}
    <div class="card sync-card">
      <div class="sync-intro">
        <h2>同步抖音收藏夹 <span class="chip gray" id="dyLoginChip">未检测</span></h2>
        <p class="muted small">会弹出浏览器窗口，第一次需要用抖音 App 扫码登录（只登录一次）。读取时会自动慢慢滚动，请不要关闭那个窗口。之前失败的视频会自动重新排队。</p>
      </div>
      <div class="sync-form">
        <div class="field"><label>读取哪个列表</label><select id="sKind"><option value="collection">我的收藏</option><option value="like">我的喜欢</option></select></div>
        <div class="row sync-btns"><button class="btn" id="loginBtn">只登录抖音</button><button class="btn primary" id="syncBtn">开始同步</button></div>
      </div>
    </div>
    <div class="card sync-card">
      <div class="sync-intro">
        <h2>小红书 <span class="chip gray" id="xhsLoginChip">未检测</span></h2>
        <p class="muted small">第一次要点「登录小红书」用小红书 App 扫码（只登录一次）。之后可以一键同步你的「收藏」，和抖音一样本地转文字 + AI 提炼 + 自动分类。也支持直接粘贴小红书链接。</p>
      </div>
      <div class="sync-form">
        <div class="field"><label>同步方式</label><select id="xhsLimit"><option value="50">最近 50 条</option><option value="0">全部</option></select></div>
        <div class="row sync-btns"><button class="btn" id="xhsLogin">登录小红书</button><button class="btn primary" id="xhsSync">同步收藏</button></div>
      </div>
    </div>
    <div class="card sync-card">
      <div class="sync-intro">
        <h2>B站 <span class="chip gray" id="biliLoginChip">未登录</span></h2>
        <p class="muted small">B 站<b>不做自动同步</b>（账号是共用的），只解析你手动粘贴的链接。登录是可选的：公开视频不登录也能解析；登录后能拿到更高清晰度、会员内容。</p>
      </div>
      <div class="sync-form">
        <div class="field"><label>登录后</label><span class="muted small">cookie 存本机 data/bili_cookies.txt，只用于下视频</span></div>
        <div class="row sync-btns"><button class="btn" id="biliLogin">登录 B 站（扫码）</button><button class="btn" id="biliPaste">粘贴 B 站链接</button></div>
      </div>
    </div>
    <div class="card" style="margin-bottom:16px"><div class="row"><b>本地缓存</b>
      <span class="spacer"></span><span class="muted small" id="cacheQuick">看下载进度和已缓存视频</span>
      <a class="btn sm" href="#/cache">打开缓存页</a></div></div>
    <div class="panels">
      <div class="card col-card">
        <h2>粘贴分享链接</h2>
        <p class="muted small">抖音、小红书、B站 都可以：视频页复制地址粘进来，视频和图文都能识别，一次能贴很多条。</p>
        <p class="muted small" style="margin-top:-4px">B站是<strong>手动解析</strong>：B站号是共用的，所以不做自动同步，只解析你贴过来的这一条（有官方字幕就用字幕，没有就下音频转文字）。</p>
        <textarea id="pText" rows="5" placeholder="粘贴抖音 / 小红书 / B站 链接……"></textarea>
        <div class="row" style="margin-top:12px"><button class="btn" id="pasteDoc" title="把公众号文章、文档里的文字直接变成笔记">${ico("file")}粘贴文稿</button><span class="spacer"></span><button class="btn" id="pAddJump" title="只加进队列，按普通优先级排">只加入队列</button><button class="btn primary" id="pAdd">${ico("zap")}添加并插队</button></div>
      </div>
      <div class="card col-card">
        <h2>导入本地视频</h2>
        <p class="muted small">链接解析不了时的备用办法：把视频文件（mp4 / mov / mp3 等）放进「收件箱」文件夹，再点扫描。原文件不会被删除。</p>
        <div class="inbox-box"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5.5 5h13L21 13v6H3v-6z"/></svg>
          <span class="muted small">收件箱文件夹</span></div>
        <div class="row" style="margin-top:12px"><span class="spacer"></span><button class="btn" id="inboxOpen">打开收件箱文件夹</button><button class="btn" id="inboxScan">扫描并处理</button></div>
      </div>
    </div>
    <div class="card today-card-wrap" id="todayCard" style="margin-bottom:16px"></div>
    <div class="card status-card" id="statusCard" style="margin-bottom:20px"></div>
    <div class="card">
      <div class="row" style="margin-bottom:8px"><div class="tabs" id="tabs" style="margin:0"></div>
        <span class="spacer"></span><button class="btn sm" id="doneSort" hidden>${ico("clock")}最新完成在前</button>
        <button class="btn sm" id="retryFailed" hidden>${ico("shuffle")}全部重试</button></div>
      <div id="irrBar" class="irr-bar" hidden></div>
      <div id="failGroups" class="fail-groups" hidden></div>
      <div class="qlist" id="qlist"></div>
    </div>
    <div class="row" style="margin-top:22px;margin-bottom:12px"><h2 style="margin:0">运行日志</h2><span class="spacer"></span>
      <button class="btn sm" id="copyLogs">${ico("copy")}一键复制日志</button></div>
    <div class="logs" id="logs"></div>`;

  $("#acctCheck") && ($("#acctCheck").onclick = async () => {
    toast("正在检查两个平台的登录状态，稍等十几秒…");
    await api("/api/login/check", {});
  });
  $("#retryFailed") && ($("#retryFailed").onclick = async () => {
    const r = await api("/api/retry_failed", {});
    toast(r.n ? `已把 ${r.n} 条失败的重新排队` : "没有失败的条目");
    await refreshState(); renderProcessLive();
  });
  (async () => {
    const chip = $("#biliLoginChip");
    if (!chip) return;
    try {
      const r = await api("/api/bili/status");
      chip.textContent = r.logged_in ? "已登录" : "未登录（可选）";
      chip.className = "chip " + (r.logged_in ? "teal" : "gray");
    } catch (e) {}
  })();
  $("#biliLogin") && ($("#biliLogin").onclick = async () => {
    try {
      const r = await api("/api/bili/login", {});
      toast(r.msg || "已打开 B 站登录页，请扫码", 6000);
    } catch (e) { toast(e.message, 5000); }
  });
  $("#biliPaste") && ($("#biliPaste").onclick = () => {
    const box = $("#pText");
    if (box) { box.focus(); box.scrollIntoView({ block: "center", behavior: "smooth" }); }
    toast("把 B 站视频地址粘到上面的「粘贴分享链接」里，点「添加并插队」");
  });
  $("#xhsLogin") && ($("#xhsLogin").onclick = async () => {
    const limit = parseInt(($("#xhsLimit") || {}).value || "50", 10);
    $("#qrModal").hidden = false;
    $("#qrHint").textContent = "正在打开登录页…";
    $("#qrImg").removeAttribute("src");
    await api("/api/xhs/login", { sync: true, limit });
    openQrWatch();
  });
  $("#xhsSync") && ($("#xhsSync").onclick = async () => {
    const limit = parseInt($("#xhsLimit").value || "50", 10);
    await api("/api/xhs/sync", { limit, process: true });
    toast("开始读取小红书收藏，会打开浏览器慢慢滚动，别关它", 5000);
    refreshState().then(renderProcessLive);
  });
  $("#cacheOpen") && ($("#cacheOpen").onclick = () => api("/api/open", { what: "media" }).catch((e) => toast(e.message)));
  $("#cacheAllBtn") && ($("#cacheAllBtn").onclick = async () => {
    const on = $("#cacheAllBtn").dataset.on === "1";
    if (on) {
      await api("/api/cache/all", { on: false });
      toast("已停止全部缓存");
    } else {
      const r = await api("/api/cache/all", { on: true });
      toast(r.queued ? `开始缓存全部视频，还剩 ${r.queued} 条没下` : "所有视频都已经在本地了");
    }
    loadCache();
  });
  $("#cacheClear") && ($("#cacheClear").onclick = async () => {
    if (!confirm("清空本地视频缓存？已经转好文字的笔记不受影响，只是下次播放要重新下载。")) return;
    const r = await api("/api/cache/clear", {});
    toast(`已清空，释放 ${fmtBytes(r.freed || 0)}`);
    loadCache();
  });
  loadCache();
  clearInterval(window.__cacheTimer);
  window.__cacheTimer = setInterval(() => { if (!$("#cacheCard")) { clearInterval(window.__cacheTimer); return; } loadCache(); }, 1200);
  const addLinks = async (text, jump) => {
    const r = await api("/api/links", { text, jump });
    toast(r.added ? `新增 ${r.added} 条${jump ? "，已插到队首" : "，已加入队列"}` : "这些链接都已经添加过了");
    return r;
  };
  $("#pasteDoc") && ($("#pasteDoc").onclick = openPasteDoc);
  $("#pAdd").onclick = async () => {
    try { await addLinks($("#pText").value, true); $("#pText").value = ""; renderProcessLive(); }
    catch (e) { toast(e.message, 4000); }
  };
  $("#pAddJump") && ($("#pAddJump").onclick = async () => {
    try { await addLinks($("#pText").value, false); $("#pText").value = ""; renderProcessLive(); }
    catch (e) { toast(e.message, 4000); }
  });
  $("#syncBtn").onclick = async () => {
    await api("/api/sync", { kind: $("#sKind").value });
    toast("开始同步（整份列表都会读完），请留意弹出的浏览器窗口"); renderProcessLive();
  };
  $("#loginBtn").onclick = async () => { await api("/api/login", {}); toast("请在弹出的浏览器窗口里扫码登录"); };
  $("#copyLogs").onclick = async () => {
    const text = (STATE.logs || []).map((l) => `${fmtTime(l.t)} ${l.msg}`).join("\n");
    if (!text) return toast("还没有日志");
    try { await navigator.clipboard.writeText(text); }
    catch {
      const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta);
      ta.select(); document.execCommand("copy"); ta.remove();
    }
    toast(`已复制 ${STATE.logs.length} 行日志，可以直接粘贴发给我`);
  };
  $(".inbox-box").onclick = () => api("/api/open", { what: "inbox" }).catch((e) => toast(e.message));
  $("#inboxOpen").onclick =() => api("/api/open", { what: "inbox" }).catch((e) => toast(e.message));
  $("#inboxScan").onclick = async () => { const r = await api("/api/inbox", {}); toast(r.added ? `新增 ${r.added} 个文件，开始处理` : "收件箱里没有新文件"); renderProcessLive(); };
  paintLoginChips();
  renderProcessLive();
}

const TABS = [
  ["active", "处理中", ACTIVE], ["failed", "失败", ["failed"]], ["need_key", "待提炼", ["need_key"]],
  ["done", "已完成", ["done"]],
];

async function loadCache() {
  let c;
  try { c = await api("/api/cache"); } catch { return; }
  if (!$("#cacheCard")) return;
  const max = c.max_bytes || 0;
  const pct = max ? Math.min(100, (c.bytes || 0) * 100 / max) : 0;
  $("#cacheBar").style.width = pct.toFixed(1) + "%";
  $("#cacheNums").textContent = `已缓存 ${c.count || 0} 个 · ${fmtBytes(c.bytes)}` + (max ? ` / ${fmtBytes(max)}` : "");
  const al = c.all || {};
  const btn = $("#cacheAllBtn");
  if (btn) {
    btn.dataset.on = al.on ? "1" : "";
    btn.textContent = al.on ? "停止缓存" : "缓存全部视频";
    btn.classList.toggle("primary", !!al.on);
  }
  const an = $("#cacheAllN");
  if (an) {
    an.textContent = al.total
      ? `${al.done || 0} / ${al.total}${al.failed ? ` · 失败 ${al.failed}` : ""}${al.on ? " · 进行中" : al.done + (al.failed || 0) >= al.total ? " · 已完成" : ""}`
      : "未开始";
  }
  const hint = $("#cacheHint");
  if (hint && max) hint.textContent = `下载过的视频会留一份在本地，点播放秒开；超过 ${fmtBytes(max)} 自动清最老的。`;
  const ab = $("#cacheAllBar");
  if (ab) ab.style.width = (al.total ? Math.min(100, (al.done || 0) * 100 / al.total) : 0) + "%";
  const acts = c.active || [];
  $("#cacheActive").innerHTML = acts.length
    ? acts.map((a) => {
        const p = a.total ? Math.min(100, a.pct || 0) : 0;
        return `<div class="cache-item">
          <div class="row"><span class="ct">${esc((a.title || "视频").slice(0, 40))}</span>
            <span class="spacer"></span><span class="muted small">${a.total ? `${fmtBytes(a.done)} / ${fmtBytes(a.total)}` : fmtBytes(a.done)}${a.speed ? ` · ${fmtBytes(a.speed)}/s` : ""}</span></div>
          <div class="bar sm"><i style="width:${p}%"></i></div></div>`;
      }).join("")
    : `<div class="muted small">现在没有正在缓存的视频</div>`;
}

function paintAcctBar() {
  const L = (STATE && STATE.login) || {};
  const paint = (sel, st) => {
    const box = $(sel);
    if (!box) return;
    const em = box.querySelector("em");
    const dot = box.querySelector(".dot");
    const t = st && st.ts ? new Date(st.ts * 1000) : null;
    const hhmm = t ? `${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}` : "";
    if (!st) { em.textContent = "未检测"; dot.className = "dot"; return; }
    if (st.ok) {
      em.textContent = `已登录${st.name ? " · " + st.name : ""}${hhmm ? "（" + hhmm + " 确认）" : ""}`;
      dot.className = "dot ok";
    } else {
      em.textContent = "未登录，点右边按钮登录";
      dot.className = "dot bad";
    }
  };
  paint("#acctDouyin", L.douyin);
  paint("#acctXhs", L.xhs);
}

function paintLoginChips() {
  paintAcctBar();
  const L = (STATE && STATE.login) || {};
  const paint = (el, st) => {
    if (!el) return;
    if (!st) { el.className = "chip gray"; el.textContent = "未检测"; return; }
    el.className = "chip " + (st.ok ? "teal" : "gray");
    const t = st.ts ? new Date(st.ts * 1000) : null;
    const hhmm = t ? `${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}` : "";
    el.textContent = st.ok ? `已登录${st.name ? " · " + st.name : (hhmm ? " · " + hhmm : "")}` : "未登录";
    if (st.name) el.title = `最近确认：${hhmm}`;
  };
  paint($("#dyLoginChip"), L.douyin);
  paint($("#xhsLoginChip"), L.xhs);
}

/* 小红书扫码：弹窗里轮询二维码，登录成功后自动关闭 */
let qrTimer = null;
async function refreshQr() {
  try {
    const r = await fetch("/api/xhs/qr?t=" + Date.now());
    if (r.ok) {
      const blob = await r.blob();
      $("#qrImg").src = URL.createObjectURL(blob);
      $("#qrHint").textContent = "二维码已就绪，用小红书 App 扫码";
    } else {
      $("#qrHint").textContent = "正在打开登录页…";
    }
  } catch {}
}
function openQrWatch() {
  clearInterval(qrTimer);
  refreshQr();
  qrTimer = setInterval(async () => {
    if ($("#qrModal").hidden) { clearInterval(qrTimer); return; }
    const st = STATE && STATE.login && STATE.login.xhs;
    if (st && st.ok) {
      clearInterval(qrTimer);
      $("#qrModal").hidden = true;
      toast("登录成功，开始读取小红书收藏");
      await refreshState();
      renderProcessLive();
      return;
    }
    refreshQr();
  }, 2500);
  $("#qrRefresh").onclick = refreshQr;
  $$("#qrModal [data-close]").forEach((b) => b.onclick = () => {
    clearInterval(qrTimer);
    $("#qrModal").hidden = true;
  });
}

async function paintToday() {
  const box = $("#todayCard");
  if (!box) return;
  let t;
  try { t = await api("/api/today"); } catch { return; }
  const cats = (t.cats || []).map((c) => `<span class="chip cat">${esc(c.cat)} ${c.n}</span>`).join(" ");
  box.innerHTML = `<div class="row" style="margin-bottom:6px"><b>今日汇总</b><span class="muted small">每天零点重新统计</span></div>
    <div class="today-card">
      <span>今天新增 <b>${t.added}</b> 条</span>
      <span>拆解完成 <b>${t.done}</b> 条</span>
      <span>跳过/无关 <b>${t.skipped}</b> 条</span>
    </div>
    ${cats ? `<div class="row" style="margin-top:10px;gap:6px;flex-wrap:wrap">${cats}</div>` : ""}`;
}

async function renderProcessLive() {
  paintToday();
  paintLoginChips();
  if (!$("#statusCard")) return;
  const w = STATE.worker, st = STATE.stats.by_status;
  const rf = $("#retryFailed"); if (rf) rf.hidden = !((st.failed || 0) > 0);
  const ds = $("#doneSort");
  if (ds) {
    ds.hidden = procTab !== "done";
    ds.innerHTML = `${ico("clock")}${doneSort === "desc" ? "最新完成在前" : "最早完成在前"}`;
    ds.onclick = () => {
      doneSort = doneSort === "desc" ? "asc" : "desc";
      try { localStorage.setItem("doneSort", doneSort); } catch (e) {}
      renderProcessLive();
    };
  }
  const pg = STATE.progress || {};
  $("#statusCard").innerHTML = w.busy
    ? (pg.item_id ? `<div class="pcard">
        <div class="row"><div class="spinner"></div><b class="ptitle">${esc(pg.title || "处理中")}</b><span class="spacer"></span>
        ${STATE.worker.paused ? `<button class="btn sm primary" id="resumeBtn">继续</button>` : `<button class="btn sm" id="pauseBtn">暂停</button>`}
        <button class="btn sm" id="stopBtn">停止</button></div>
        <div class="stepper">${["fetching", "downloading", "transcribing", "extracting"].map((k) => {
            const lbl = (pg.is_note ? { fetching: "读取图文", downloading: "下载图片", transcribing: "识别图片文字", extracting: "AI 提炼" }
              : { fetching: "读取信息", downloading: "下载", transcribing: "转文字", extracting: "AI 提炼" })[k];
            const order = ["fetching", "downloading", "transcribing", "extracting"];
            const cls = k === pg.stage ? "now" : (order.indexOf(k) < order.indexOf(pg.stage) ? "done" : "");
            return `<span class="step ${cls}">${cls === "done" ? "✓ " : ""}${lbl}${k === pg.stage ? ` ${pg.stage_pct}%` : ""}</span>`; }).join('<span class="arrow">›</span>')}</div>
        <div class="bar big-bar"><i style="width:${pg.pct}%"></i></div>
        <div class="row small"><b>${pg.pct}%</b><span class="muted">这一条预计还剩 ${fmtEta(pg.eta)}${pg.real ? "" : "（估算）"}</span><span class="spacer"></span>
          <span class="muted">${w.total ? `本批 ${w.done + 1} / ${w.total}` : ""}${pg.batch_eta > pg.eta + 5 ? ` · 全部预计还剩 ${fmtEta(pg.batch_eta)}` : ""}</span></div>
      </div>`
      : `<div class="spinner"></div><div style="flex:1"><b>${esc(w.stage || "处理中…")}</b>
        <div class="muted small">${w.total ? `本批进度 ${w.done} / ${w.total}` : ""}</div></div>
        ${w.paused ? `<button class="btn primary" id="resumeBtn">继续处理</button>` : `<button class="btn" id="pauseBtn" ${(st.queued || 0) ? "" : "disabled"}>暂停</button>`}
        <button class="btn" id="stopBtn">停止</button>`)
    : `<div class="idle-ic">${ico("coffee")}</div><div style="flex:1"><b>空闲中</b><div class="muted small">
        ${(st.queued || 0) ? `队列里还有 ${st.queued} 条等待处理` : "添加视频后会自动开始处理"}</div></div>
        ${(st.failed || 0) ? `<button class="btn" id="retryFailed">${ico("retry")}重试失败的 ${st.failed} 条</button>` : ""}
        ${(st.queued || 0) ? `<button class="btn primary" id="goBtn">开始处理</button>` : ""}`;
  $("#retryFailed") && ($("#retryFailed").onclick = async () => {
    const failed = await api("/api/items?status=failed");
    for (const it of failed) await api(`/api/items/${it.id}/action`, { action: "retry" });
    toast(`${failed.length} 条已重新排队，开始处理`); await refreshState(); renderProcessLive();
  });
  $("#stopBtn") && ($("#stopBtn").onclick = () => api("/api/stop", {}));
  $$("#failGroups [data-clean]").forEach((b) => b.onclick = async () => {
    const ids = (b.dataset.clean || "").split(",").filter(Boolean);
    if (!confirm(`把这 ${ids.length} 条已删除的内容移进回收站？（可恢复）`)) return;
    b.disabled = true;
    try {
      const r = await api("/api/failures/clean", { ids: ids.map(Number) });
      toast(`已移入回收站 ${r.n} 条`);
      await refreshState(); renderProcessLive();
    } catch (e) { toast(e.message, 4000); b.disabled = false; }
  });
  $$("#failGroups [data-g]").forEach((b) => b.onclick = async () => {
    const ids = (b.dataset.ids || "").split(",").filter(Boolean);
    b.disabled = true;
    for (const id of ids) { try { await api(`/api/items/${id}/action`, { action: "retry" }); } catch (e) {} }
    toast(`已把 ${ids.length} 条放回队列重试`);
    await refreshState(); renderProcessLive();
  });
  $("#pauseBtn") && ($("#pauseBtn").onclick = async () => { await api("/api/pause", {}); toast("已暂停，点「继续」接着跑"); refreshState().then(renderProcessLive); });
  $("#resumeBtn") && ($("#resumeBtn").onclick = async () => { await api("/api/resume", {}); toast("继续处理"); refreshState().then(renderProcessLive); });
  $("#goBtn") && ($("#goBtn").onclick = async () => { await api("/api/process", {}); refreshState().then(renderProcessLive); });

  $("#tabs").innerHTML = TABS.map(([k, label, ss]) => {
    const n = ss.reduce((a, s) => a + (st[s] || 0), 0);
    return `<button data-k="${k}" class="${procTab === k ? "on" : ""}">${label} ${n ? `(${n})` : ""}</button>`;
  }).join("");
  $$("#tabs button").forEach((b) => b.onclick = () => {
    procTab = b.dataset.k;
    try { history.replaceState(null, "", "#/process/" + procTab); } catch (e) {}
    renderProcessLive();
  });

  const ib = $("#irrBar");
  if (ib) {
    ib.hidden = procTab !== "irrelevant";
    if (!ib.hidden) {
      ib.innerHTML = `<span class="muted small">之前「关注主题」只写了 AI，摄影后期、美食、健身这些干货被误判成无关。可以按内容重新分一次类，够格的直接放回学习库。</span>
        <span class="spacer"></span><button class="btn sm primary" id="irrRecheck">重新审查这些内容</button>`;
      $("#irrRecheck").onclick = async () => {
        const btn = $("#irrRecheck");
        btn.disabled = true;
        btn.textContent = "正在审查…";
        try {
          const r = await api("/api/irrelevant/recheck", {});
          const parts = Object.entries(r.by_cat || {}).map(([k, v]) => `${k} ${v}`);
          toast(r.moved
            ? `放回学习库 ${r.moved} 条${parts.length ? "（" + parts.join("、") + "）" : ""}，还有 ${r.stayed} 条确实无关`
            : `没有能放回的，${r.stayed} 条确实和主题无关`, 6000);
          await refreshState();
          renderProcessLive();
        } catch (e) {
          toast(e.message, 5000);
          btn.disabled = false;
          btn.textContent = "重新审查这些内容";
        }
      };
    }
  }

  const ss = TABS.find((t) => t[0] === procTab)[2];
  // 处理中按「插队优先 + 原有优先级」排，已完成按完成时间倒序（最新做完的在最上面）
  const sortKey = procTab === "active" ? "queue" : (procTab === "done" && doneSort === "asc" ? "done_asc" : "done");
  const items = await api("/api/items?status=" + ss.join(",") + "&sort=" + sortKey);
  // 手动添加 / 插队的条目带 queue_prio；同步收藏夹进来的没有 → 用来标「刚添加」
  const isNew = (it) => !!it.queue_prio;
  // 失败页：按原因归类，支持一组一组重试
  const fg = $("#failGroups");
  if (fg) {
    if (procTab === "failed" && items.length) {
      const key = (r) => {
        r = r || "";
        if (/余额|402/.test(r)) return "AI 余额不足";
        if (/超时|Timeout|goto/i.test(r)) return "页面加载超时";
        if (/播放地址|没有画面|只下到音频/.test(r)) return "视频地址/画面取不到";
        if (/连不上|网络|URLError/i.test(r)) return "网络连不上";
        if (/浏览器|context or browser/i.test(r)) return "浏览器中断";
        if (/no such|找不到|404/i.test(r)) return "内容已被删除";
        return "其他原因";
      };
      const groups = {};
      items.forEach((it) => { (groups[key(it.reason)] = groups[key(it.reason)] || []).push(it.id); });
      fg.hidden = false;
      fg.innerHTML = Object.entries(groups).map(([k, ids]) => {
        const clean = k === "内容已被删除"
          ? ` <button class="btn sm ghost" data-clean="${ids.join(",")}">移入回收站</button>` : "";
        return `<span class="fg"><button class="btn sm" data-g="${k}" data-ids="${ids.join(",")}">${esc(k)} · ${ids.length} 条 · 重试</button>${clean}</span>`;
      }).join(" ");
    } else {
      fg.hidden = true; fg.innerHTML = "";
    }
  }
  let qpos = 0;
  $("#qlist").innerHTML = items.length ? items.slice(0, 300).map((it) => {
    const [label, cls] = STATUS[it.status] || [it.status, "gray"];
    let btns = "";
    let meta = "";
    if (it.status === "failed") btns = `<button class="btn sm" data-a="retry" data-id="${it.id}">重试</button>`;
    if (it.status === "need_key") btns = `<button class="btn sm" data-a="reextract" data-id="${it.id}">提炼</button>`;
    if (it.status === "irrelevant") btns = `<button class="btn sm" data-a="include" data-id="${it.id}">收进学习库</button>`;
    if (it.status === "retry_wait") {
      const due = (STATE.worker.retry_at || {})[String(it.id)] || 0;
      const left = Math.max(0, Math.round(due - Date.now() / 1000));
      btns = `<button class="btn sm" data-a="retry" data-id="${it.id}">立即重试</button>`;
      meta = `<span class="qnum">${left ? left + " 秒后自动重试" : "马上重试"}</span>`;
    }
    if (it.status === "queued") {
      qpos += 1;
      btns += `<button class="btn sm" data-a="jump" data-id="${it.id}" title="排到队首，下一个就处理它">${ico("arrowUp")}插队</button>`;
    }
    if (["failed", "skipped", "irrelevant", "need_key", "queued"].includes(it.status)) btns += ` <button class="btn sm ghost" data-a="delete" data-id="${it.id}">删除</button>`;
    // 队列序号 / 完成时间 / 刚添加
    if (it.status === "queued") meta = `<span class="qnum">第 ${qpos} 位</span>`;
    if (it.status === "done") meta = `<span class="qnum">${fmtDayTime(it.done_at || it.updated_at)} 完成</span>`;
    const newBadge = isNew(it) ? `<span class="chip teal" style="margin-right:6px">刚添加</span>` : "";
    return `<div class="qrow${it.status === "queued" && isNew(it) ? " fresh" : ""}"><div style="min-width:0">
        <div class="t">${newBadge}<a href="#/item/${it.id}" style="color:inherit">${esc(it.note_title || it.title || it.url || "（解析中）")}</a></div>
        <div class="r"><span class="chip ${cls}">${label}</span> ${meta} ${esc(it.reason || "")}</div></div>
        <div class="row">${btns}</div></div>`;
  }).join("") : `<div class="empty" style="padding:30px">这里是空的</div>`;
  $$("#qlist [data-a]").forEach((b) => b.onclick = async () => {
    const a = b.dataset.a;
    if (a === "delete" && !confirm("删除这条？")) return;
    if (a === "jump") {
      b.disabled = true;
      try {
        await api(`/api/items/${b.dataset.id}/action`, { action: "jump" });
        toast("已插队，下一个就处理它");
      } catch (e) { toast(e.message, 4000); b.disabled = false; return; }
    } else {
      await api(`/api/items/${b.dataset.id}/action`, { action: a });
    }
    await refreshState(); renderProcessLive();
  });
  if (procTab === "need_key" && items.length > 1 && STATE.settings.api_key_set) {
    $("#qlist").insertAdjacentHTML("afterbegin", `<div class="row" style="padding:8px 4px"><span class="muted small">AI Key 已填好，可以一次全部提炼</span><span class="spacer"></span><button class="btn sm primary" id="allRe">全部提炼</button></div>`);
    $("#allRe").onclick = async () => { for (const it of items) await api(`/api/items/${it.id}/action`, { action: "reextract" }); toast("已全部加入队列"); };
  }
  if (procTab === "failed" && items.length >= 1) {
    $("#qlist").insertAdjacentHTML("afterbegin", `<div class="row" style="padding:8px 4px"><span class="spacer"></span><button class="btn sm" id="allRetry">全部重试</button></div>`);
    $("#allRetry").onclick = async () => { for (const it of items) await api(`/api/items/${it.id}/action`, { action: "retry" }); toast("已全部重新排队，开始处理"); await refreshState(); renderProcessLive(); };
  }
  const logs = $("#logs");
  const atBottom = logs.scrollTop + logs.clientHeight >= logs.scrollHeight - 20;
  logs.innerHTML = (STATE.logs || []).map((l) => `<div><span>${fmtTime(l.t)}</span>${esc(l.msg)}</div>`).join("") || `<div class="muted">暂无日志</div>`;
  if (atBottom) logs.scrollTop = logs.scrollHeight;
}

/* ---------------------------------------------------------------- 设置 */
async function renderSettings() {
  if (!window.__META) {
    try { window.__META = await api("/api/meta"); } catch (e) { window.__META = {}; }
  }
  await refreshState();
  const s = STATE.settings, P = STATE.providers || (window.__META || {}).providers || {};
  view.innerHTML = `
    <div class="head"><div><h1>设置</h1><div class="muted">所有设置和数据都只保存在你自己的电脑上</div></div>
      <div class="spacer"></div><a class="btn" href="#/welcome">使用教程</a></div>
    ${freePlanHtml(s)}
    <div class="card form" style="margin-bottom:16px">
      <h2>AI 提炼</h2>
      <div class="grid2">
        <div class="field"><label>AI 服务商</label><select id="provider">${Object.entries(P).map(([k, v]) => `<option value="${k}" ${s.provider === k ? "selected" : ""}>${esc(v.name)}</option>`).join("")}</select>
          <div class="hint" id="keyLink"></div></div>
        <div class="field"><label>API Key ${s.api_key_set ? `<span class="chip teal">已保存 ${esc(s.api_key_hint)}</span>` : ""}</label>
          <input id="apiKey" type="password" placeholder="${s.api_key_set ? "留空表示不修改" : "sk-..."}" autocomplete="off">
          <div class="hint">Key 只存在本机 data/settings.json，不会上传到别处。</div></div>
        <div class="field"><label>接口地址（Base URL）</label><input id="baseUrl" value="${esc(s.base_url)}"></div>
        <div class="field"><label>模型</label><div class="model-pick"><input id="model" value="${esc(s.model)}" placeholder="选择或输入模型名" autocomplete="off">
          <select id="modelPick" title="从列表选择模型"></select></div>
          <div class="hint"><span id="mHint">点右边的箭头从列表选择；也可以直接输入。</span> <a href="javascript:void 0" id="mLoad">刷新模型列表</a></div></div>
      </div>
      <div class="row" style="margin:10px 0"><div class="field" style="max-width:200px;margin:0">
          <label>并行分析条数</label><input id="par" type="number" min="1" max="8" value="${s.parallel || 4}"></div>
        <span class="muted small" style="margin-left:12px">同时让几个模型一起提炼；取信息、下载、转文字仍按顺序做。改完下一批就生效。</span></div>
      <div class="row"><button class="btn" id="testBtn">测试连接</button><span class="small" id="testRes"></span>
        <span class="spacer"></span><span class="muted small">累计消耗约 ${(s.tokens_used || 0).toLocaleString()} tokens</span></div>
    </div>
    <div class="card form" style="margin-bottom:16px">
      <h2>备用模型 <span class="chip gray">主模型超时就自动切过去</span></h2>
      <p class="muted small">主模型连不上、超时、被限速，或者那家没余额时，自动改用下面这个模型继续跑，不会把整批任务卡死。</p>
      <div class="row" style="margin-bottom:10px"><label class="switch"><input type="checkbox" id="fbOn" ${s.fb_on ? "checked" : ""}> 启用备用模型</label></div>
      <div class="grid2">
        <div class="field"><label>服务商</label><select id="fbProvider">${Object.entries(P).map(([k, v]) => `<option value="${k}" ${s.fb_provider === k ? "selected" : ""}>${esc(v.name)}</option>`).join("")}</select></div>
        <div class="field"><label>API Key ${s.fb_api_key_set ? `<span class="chip teal">已保存</span>` : ""}</label>
          <input id="fbKey" type="password" placeholder="${s.fb_api_key_set ? "留空表示不修改" : "sk-..."}" autocomplete="off"></div>
        <div class="field"><label>接口地址（Base URL）</label><input id="fbBase" value="${esc(s.fb_base_url || "")}"></div>
        <div class="field"><label>模型</label><input id="fbModel" value="${esc(s.fb_model || "")}" placeholder="deepseek-flash"></div>
      </div>
    </div>
    <div class="card form" style="margin-bottom:16px">
      <h2>精读（有人带着读）</h2>
      <div class="field"><label class="check"><input type="checkbox" id="deepSame" ${s.deep_same ? "checked" : ""}> 精读和上面的 AI 提炼用同一个模型</label>
        <div class="hint">日常批量提炼用便宜的模型（比如 DeepSeek），精读用更强的模型（比如 Claude）——取消勾选就能单独设置。</div></div>
      <div id="deepCfg" ${s.deep_same ? "hidden" : ""}>
        <div class="grid2">
          <div class="field"><label>精读用的服务商</label><select id="dProvider">${Object.entries(P).map(([k, v]) => `<option value="${k}" ${s.deep_provider === k ? "selected" : ""}>${esc(v.name)}</option>`).join("")}</select>
            <div class="hint" id="dKeyLink"></div></div>
          <div class="field"><label>API Key ${s.deep_api_key_set ? `<span class="chip teal">已保存 ${esc(s.deep_api_key_hint)}</span>` : ""}</label>
            <input id="dKey" type="password" placeholder="${s.deep_api_key_set ? "留空表示不修改" : "sk-ant-... / sk-..."}" autocomplete="off"></div>
          <div class="field"><label>接口地址</label><input id="dBase" value="${esc(s.deep_base_url)}"></div>
          <div class="field"><label>模型</label><div class="model-pick"><input id="dModel" value="${esc(s.deep_model)}" placeholder="选择或输入模型名" autocomplete="off">
            <select id="dModelPick" title="从列表选择模型"></select></div>
            <div class="hint"><span id="dmHint">点右边的箭头从列表选择；也可以直接输入。</span> <a href="javascript:void 0" id="dmLoad">刷新模型列表</a></div></div>
        </div>
        <div class="row" style="margin:12px 0 14px"><button class="btn" id="dTest">测试精读模型</button><span class="small" id="dTestRes"></span></div>
      </div>
      <div class="field"><label>精读提示词</label><textarea id="dPrompt" rows="4">${esc(s.deep_prompt)}</textarea>
        <div class="hint">告诉 AI 你想怎么被带着读。输出格式（结论/大纲/概念/检查题/测验/Anki/思维导图）由程序固定，这里写学习要求就行。
          <a href="javascript:void 0" id="dPromptReset">恢复默认</a></div></div>
      <div class="field" style="max-width:340px"><label>文稿超过多少字就分段预读</label><input id="dChunk" type="number" min="3000" max="100000" step="1000" value="${s.deep_chunk_chars}">
        <div class="hint">模型上下文小就调小。12000 字大约是 40 分钟的口播。</div></div>
    </div>
    <div class="card form" style="margin-bottom:16px">
      <h2>学什么</h2>
      <div class="field"><label>我关注的主题</label><textarea id="focus" rows="2">${esc(s.focus_topic)}</textarea>
        <div class="hint">AI 会按这个判断视频是否相关。想学别的（比如理财、健身）直接改这里。</div></div>
      <div class="field"><label class="check"><input type="checkbox" id="onlyRel" ${s.only_relevant ? "checked" : ""}> 和主题无关的视频自动收起（在「主题无关」里还能找回）</label></div>
      <div class="field"><label>分类（用逗号分隔，AI 会优先从这里选）</label><input id="cats" value="${esc((s.categories || []).join("，"))}"></div>
    </div>
    <div class="card form" style="margin-bottom:16px">
      <h2>语音转文字（在本机运行）</h2>
      <div class="grid2">
        <div class="field"><label>识别引擎</label><select id="engine">
          ${[["auto", "自动（苹果芯片 Mac 用加速版，其他用通用版）"], ["mlx", "Mac 加速版（mlx-whisper large-v3-turbo）"], ["faster", "通用版（faster-whisper）"]]
            .map(([k, l]) => `<option value="${k}" ${s.asr_engine === k ? "selected" : ""}>${l}</option>`).join("")}</select>
          <div class="hint">${STATE.asr.apple_silicon ? (STATE.asr.mlx_available ? "✓ 检测到苹果芯片，Mac 加速版可用（第一次会下载约 1.6GB 模型）" : "检测到苹果芯片，但还没装加速组件：请重新运行一次安装脚本") : "这台电脑用通用版"}</div></div>
        <div class="field"><label class="check" style="margin-top:26px"><input type="checkbox" id="useSubs" ${s.use_subtitles ? "checked" : ""}> 视频自带字幕时直接用字幕（更快，跳过下载和转写）</label></div>
        <div class="field"><label>通用版的模型大小</label><select id="wm">
          ${[["tiny", "tiny：最快，准确率低"], ["base", "base：较快，够用"], ["small", "small：推荐，准确率和速度平衡"], ["medium", "medium：更准，但慢很多"]]
            .map(([k, l]) => `<option value="${k}" ${s.whisper_model === k ? "selected" : ""}>${l}</option>`).join("")}</select>
          <div class="hint">只在用通用版时生效。第一次使用会自动下载（small 约 480MB）。</div></div>
        <div class="field"><label>超长视频只转录前几分钟</label><input id="maxMin" type="number" min="1" max="120" value="${s.max_minutes}"></div>
      </div>
      <div class="field"><label>图片文字识别（图文用）</label>
        <div class="${STATE.ocr?.backend ? "" : "banner warn"}" style="${STATE.ocr?.backend ? "" : "margin:0"}">${STATE.ocr?.backend ? `✓ ${esc(STATE.ocr.label)}（在本机运行，图片不上传）` : "还没安装文字识别组件：请重新运行一次安装脚本。没装的话，图文只会用正文文字。"}</div></div>
      <div class="field"><label class="check"><input type="checkbox" id="mirror" ${s.use_hf_mirror ? "checked" : ""}> 使用国内镜像下载模型（人在中国大陆时勾选；在海外不要勾）</label></div>
      <div class="field"><label class="check"><input type="checkbox" id="keepVideo" ${s.keep_video ? "checked" : ""}> 转录后保留视频文件（默认删除，节省空间）</label></div>
    </div>
    <div class="card form" style="margin-bottom:16px">
      <h2>外观</h2>
      <div class="seg" id="segTheme" style="max-width:520px">
        ${[["auto", "跟随系统"], ["light", "浅色（默认）"], ["white", "纯白"], ["dark", "深色"]]
          .map(([v, l]) => `<button data-v="${v}" class="${(localStorage.getItem("theme") || "auto") === v ? "on" : ""}">${l}</button>`).join("")}
      </div>
      <p class="muted small" style="margin-top:8px">纯白：页面底色纯白、卡片靠细边框区分，白天看着更干净；深色：晚上护眼。</p>
    </div>
    <div class="card form" style="margin-bottom:16px">
      <h2>自动化 <span class="chip teal">推荐全开</span></h2>
      <p class="muted small">打开后你只需要做一件事：删掉不想要的。同步、排队、拆解都不用点。</p>
      <div class="row" style="margin-bottom:10px"><label class="switch"><input type="checkbox" id="autoSync" ${s.auto_sync ? "checked" : ""}> 自动同步收藏</label>
        <span class="muted small" style="margin-left:12px">每</span>
        <input id="autoMin" type="number" min="5" max="180" value="${s.auto_sync_min || 10}" style="max-width:90px;margin:0 6px">
        <span class="muted small">分钟检查一次新收藏</span></div>
      <div class="row" style="margin-bottom:10px"><label class="switch"><input type="checkbox" id="autoProc" ${s.auto_process ? "checked" : ""}> 有新条目就自动开始拆解</label></div>
      <div class="row"><span class="muted small">可选：每天固定时间再同步一次</span>
        <input id="autoSyncAt" type="time" value="${esc(s.auto_sync_at || "")}" style="max-width:150px;margin-left:10px"></div>
      <div class="row" style="margin-top:12px"><label class="switch"><input type="checkbox" id="asrAuto" ${s.asr_auto ? "checked" : ""}> 语音模型按视频长短自动选</label>
        <span class="muted small" style="margin-left:12px">5 分钟以内用 medium（更准），长视频用 small（更快）</span></div>
      <div class="row" style="margin-top:12px"><button class="btn" id="auditCats">${ico("search")}自查分类</button>
        <span class="muted small" id="auditRes" style="margin-left:12px">按关键词体检一遍，找出明显分错的条目（不花钱）</span></div>
    </div>
    <div class="card form" style="margin-bottom:16px" id="backupCard">
      <h2>备份与恢复</h2>
      <p class="muted" style="margin:-6px 0 0">把全部数据（笔记、文字稿、精读、学习进度、设置）打包成一个文件。换电脑时，在新电脑上装好学习台，导入这个文件就恢复原样。
        抖音登录状态和语音模型不打包：换电脑后重新扫码、模型会自动重新下载。</p>
      <div class="row" style="gap:12px">
        <a class="btn primary" id="bkDown" href="/api/backup?keys=1">${ico("download")}下载完整备份</a>
        <label class="check small"><input type="checkbox" id="bkKeys" checked style="accent-color:var(--accent)"> 备份里包含 AI Key</label>
        <span class="spacer"></span>
        <label class="btn" for="bkFile">恢复备份…</label>
        <input type="file" id="bkFile" accept=".zip,application/zip" hidden>
      </div>
      <div class="hint" id="bkHint">备份文件里如果包含 AI Key，请当作密码一样保管，别发给别人。恢复会覆盖当前数据，恢复前程序会先自动把当前数据备份一份。</div>
      <div id="bkAuto"></div>
    </div>
    <div class="card form" style="margin-bottom:16px">
      <h2>存储与浏览器</h2>
      <div class="field"><label>笔记保存位置（可以直接用 Obsidian 打开这个文件夹；留空 = 默认位置）</label>
        <div class="row"><input id="libDir" value="${esc(s.library_dir)}" placeholder="${esc(STATE.library_dir)}" style="flex:1"><button class="btn" id="openLib">打开文件夹</button></div></div>
      <div class="field"><label>用哪个浏览器登录抖音</label><select id="browser">
        ${[["auto", "自动（先找 Edge，再找 Chrome）"], ["msedge", "Microsoft Edge"], ["chrome", "Google Chrome"], ["chromium", "内置 Chromium（需单独安装）"]]
          .map(([k, l]) => `<option value="${k}" ${s.browser === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    </div>
    <div class="card form" style="margin-bottom:16px">
      <h2>运行方式</h2>
      <p class="muted" style="margin:-6px 0 0">这个程序是常驻后台的：<b>关掉窗口后，处理队列、AI 提炼、精读、分类都会继续跑</b>（左下角状态条还在动就说明在干活）。想回到界面，再双击一次桌面图标就行。</p>
      <div class="row" style="margin-top:14px">
        <button class="btn" id="quitBtn" style="color:var(--bad)">退出程序</button>
        <span class="muted small">退出后正在处理的那一条会停住，进度都保留，下次打开从队列继续。</span>
      </div>
    </div>
    <div class="row"><span class="spacer"></span>${s.api_key_set ? `<button class="btn ghost" id="clearKey">清除已保存的 Key</button>` : ""}<button class="btn primary" id="saveBtn">保存设置</button></div>`;

  const showKeyLink = () => {
    const p = P[$("#provider").value];
    $("#keyLink").innerHTML = p.key_url ? `<a href="${esc(p.key_url)}" target="_blank" rel="noopener">去 ${esc(p.name)} 申请 Key →</a>` : "填写任意 OpenAI 兼容接口的地址和模型名";
  };
  showKeyLink();
  const showDKeyLink = () => {
    const p = P[$("#dProvider").value];
    $("#dKeyLink").innerHTML = p.key_url ? `<a href="${esc(p.key_url)}" target="_blank" rel="noopener">去 ${esc(p.name)} 申请 Key →</a>` : "";
  };
  showDKeyLink();
  $("#deepSame").onchange = (e) => { $("#deepCfg").hidden = e.target.checked; };
  $("#dProvider").onchange = () => {
    const p = P[$("#dProvider").value];
    if (p.base_url) { $("#dBase").value = p.base_url; $("#dModel").value = p.model; }
    modelCache.deep = null; fillPick("dModelPick", "dModel", p.models || [p.model].filter(Boolean), "dmHint", false);
    showDKeyLink();
  };
  $("#dPromptReset").onclick = () => { $("#dPrompt").value = s.default_deep_prompt; };
  $("#quitBtn").onclick = async () => {
    if (!confirm("确定退出收藏变笔记？\n\n后台任务会停住，进度都保留，下次打开会从队列继续。")) return;
    try { await api("/api/quit", {}); } catch (e) {}
    document.body.innerHTML = `<div style="display:grid;place-items:center;height:100vh;text-align:center;gap:8px">
      <div><h2 style="margin:0 0 6px">收藏变笔记已退出</h2>
      <p class="muted">这个窗口可以直接关掉；下次双击桌面图标就会重新启动。</p></div></div>`;
  };
  $("#dTest").onclick = async () => {
    $("#dTestRes").textContent = "测试中…";
    const r = await api("/api/test_llm", { purpose: "deep", provider: $("#dProvider").value, base_url: $("#dBase").value, model: $("#dModel").value, api_key: $("#dKey").value });
    if (r.ok) {
      if (r.models?.length) modelCache.deep = r.models;
      toast("连接成功，精读设置已自动保存");
      await renderSettings();
      $("#dTestRes").innerHTML = `<span style="color:var(--ok)">✓ 连接成功，已保存（AI 回复：${esc(r.reply)}）</span>`;
    } else $("#dTestRes").innerHTML = `<span style="color:var(--bad)">✗ ${esc(r.error)}</span>`;
  };
  $("#provider").onchange = () => {
    const p = P[$("#provider").value];
    if (p.base_url) { $("#baseUrl").value = p.base_url; $("#model").value = p.model; }
    modelCache.main = null; fillPick("modelPick", "model", p.models || [p.model].filter(Boolean), "mHint", false);
    showKeyLink();
  };
  $("#testBtn").onclick = async () => {
    $("#testRes").textContent = "测试中…";
    const r = await api("/api/test_llm", { provider: $("#provider").value, base_url: $("#baseUrl").value, model: $("#model").value, api_key: $("#apiKey").value });
    if (r.ok) {
      if (r.models?.length) modelCache.main = r.models;
      toast("连接成功，已自动保存");
      await renderSettings();
      $("#testRes").innerHTML = `<span style="color:var(--ok)">✓ 连接成功，已保存（AI 回复：${esc(r.reply)}）</span>`;
    } else $("#testRes").innerHTML = `<span style="color:var(--bad)">✗ ${esc(r.error)}</span>`;
  };
  // 模型下拉：有缓存用缓存，没有就用预设，并在后台去服务商拉一次真实列表
  const initPick = (purpose, pickId, inputId, hintId, provId) => {
    const p = P[$("#" + provId).value] || {};
    const cached = modelCache[purpose];
    fillPick(pickId, inputId, cached || p.models || [], hintId, !!cached);
    const load = async (quiet) => {
      const body = purpose === "deep"
        ? { purpose, provider: $("#dProvider").value, base_url: $("#dBase").value, api_key: $("#dKey").value }
        : { purpose, provider: $("#provider").value, base_url: $("#baseUrl").value, api_key: $("#apiKey").value };
      try { const r = await api("/api/models", body); modelCache[purpose] = r.models; fillPick(pickId, inputId, r.models, hintId, true);
        if (!quiet) toast(`读取到 ${r.models.length} 个模型`); }
      catch (e) { if (!quiet) toast(e.message, 4000); }
    };
    $("#" + (purpose === "deep" ? "dmLoad" : "mLoad")).onclick = () => load(false);
    const keySet = purpose === "deep" ? s.deep_api_key_set : s.api_key_set;
    if (!cached && keySet && (purpose === "main" || !s.deep_same)) load(true);
  };
  initPick("main", "modelPick", "model", "mHint", "provider");
  initPick("deep", "dModelPick", "dModel", "dmHint", "dProvider");
  setupBackup();
  setupFreePlan();
  $$("#segTheme button").forEach((b) => b.onclick = () => {
    applyTheme(b.dataset.v);
    $$("#segTheme button").forEach((x) => x.classList.toggle("on", x === b));
    toast("外观已切换：" + b.textContent.trim());
  });
  $("#auditCats") && ($("#auditCats").onclick = async () => {
    const btn = $("#auditCats");
    btn.disabled = true;
    try {
      const r = await api("/api/audit_cats");
      const box = $("#auditRes");
      if (box) box.textContent = `已完成 ${r.total} 条，疑似分错 ${r.suspicious_n} 条 · 报告：${r.file || "data/tmp/cat_audit.md"}`;
    } catch (e) {
      toast(e.message, 5000);
    }
    btn.disabled = false;
  });
  $("#openLib").onclick = () => api("/api/open", { what: "library" }).catch((e) => toast(e.message));
  $("#clearKey") && ($("#clearKey").onclick = async () => { if (confirm("清除已保存的 API Key？")) { await api("/api/settings", { clear_key: true }); toast("已清除"); renderSettings(); } });
  $("#saveBtn").onclick = async () => {
    await api("/api/settings", {
      provider: $("#provider").value, base_url: $("#baseUrl").value.trim(), model: $("#model").value.trim(), api_key: $("#apiKey").value.trim(),
      deep_same: $("#deepSame").checked, deep_provider: $("#dProvider").value, deep_base_url: $("#dBase").value.trim(),
      deep_model: $("#dModel").value.trim(), deep_api_key: $("#dKey").value.trim(), deep_prompt: $("#dPrompt").value.trim(),
      deep_chunk_chars: +$("#dChunk").value,
      fb_on: $("#fbOn").checked, fb_provider: $("#fbProvider").value,
      parallel: Math.max(1, Math.min(8, +$("#par").value || 4)),
      fb_base_url: $("#fbBase").value.trim(), fb_model: $("#fbModel").value.trim(),
      fb_api_key: $("#fbKey").value.trim(),
      focus_topic: $("#focus").value.trim(), only_relevant: $("#onlyRel").checked, categories: $("#cats").value,
      auto_sync: $("#autoSync").checked, auto_sync_min: Math.max(5, Math.min(180, +$("#autoMin").value || 10)),
      auto_process: $("#autoProc").checked, auto_sync_at: $("#autoSyncAt").value || "",
      asr_auto: $("#asrAuto").checked,
      whisper_model: $("#wm").value, asr_engine: $("#engine").value, use_subtitles: $("#useSubs").checked, max_minutes: +$("#maxMin").value, use_hf_mirror: $("#mirror").checked,
      keep_video: $("#keepVideo").checked, library_dir: $("#libDir").value.trim(), browser: $("#browser").value, welcome_done: true,
    });
    toast("已保存"); renderSettings();
  };
}

/* ---------------------------------------------------------------- 启动 */
let weeklyDue = null;
(async () => {
  try {
    const meta = await api("/api/meta");
    window.__META = meta || {};
  } catch (e) { window.__META = {}; }
  const sideSearch = $("#sideSearch");
  if (sideSearch) {
    let st = null;
    const apply = (v) => {
      favFilter.q = v.trim();
      const pf = favFilter.platform;
      const want = `#/favs${pf ? "/p/" + pf : ""}${favFilter.category ? "/cat/" + encodeURIComponent(favFilter.category) : ""}`;
      if (location.hash !== want) location.hash = want;
      else renderFavs(true);
    };
    sideSearch.addEventListener("input", (e) => {
      clearTimeout(st);
      st = setTimeout(() => apply(e.target.value), 320);
    });
    sideSearch.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { clearTimeout(st); apply(e.target.value); }
    });
  }
  const foldBtn = $("#navFavFold");
  if (foldBtn) {
    foldBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      localStorage.setItem("favFold2", favFolded() ? "0" : "1");
      applyFavFold();
    });
  }
  await refreshState();
  try { weeklyDue = await api("/api/weekly/due"); $("#navWeekly").hidden = !weeklyDue.due; } catch {}
  if (!location.hash) {
    if (!STATE.settings.welcome_done) location.hash = "#/welcome";
    else location.hash = STATE.settings.api_key_set || STATE.stats.total ? "#/favs" : "#/settings";
  }
  render();
  startPolling();
})();

/* ---------------------------------------------------------------- 备份与恢复 */
const fmtSize = (n) => n > 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB";

async function setupBackup() {
  const keys = $("#bkKeys"), down = $("#bkDown");
  keys.onchange = () => { down.href = "/api/backup?keys=" + (keys.checked ? "1" : "0"); };
  down.onclick = () => toast("正在打包备份，稍等几秒浏览器就会开始下载");
  $("#bkFile").onchange = async (e) => {
    const file = e.target.files[0]; e.target.value = "";
    if (!file) return;
    try {
      toast("正在检查备份文件……");
      const r1 = await fetch("/api/restore?dry=1", { method: "POST", body: file });
      const m = await r1.json();
      if (!r1.ok) throw new Error(m.error || "检查失败");
      const msg = `要从这个备份恢复吗？\n\n备份时间：${m.created}\n视频：${m.items} 条（笔记 ${m.done} 条，已学 ${m.learned} 条）\nMarkdown 笔记文件：${m.notes_in_zip} 个\n${m.has_keys ? "包含 AI Key" : "不含 AI Key（会保留你现在的 Key）"}\n\n恢复会覆盖当前数据；当前数据会先自动备份一份，选错了还能找回。`;
      if (!confirm(msg)) return;
      toast("正在恢复……", 10000);
      const r2 = await fetch("/api/restore", { method: "POST", body: file });
      const res = await r2.json();
      if (!r2.ok) throw new Error(res.error || "恢复失败");
      toast(`✓ 恢复完成：${res.items} 条视频，${res.done} 条笔记`, 4000);
      await refreshState(); renderSettings();
    } catch (err) { toast(err.message, 5000); }
  };
  try {
    const r = await api("/api/backups");
    if (r.files.length) {
      $("#bkAuto").innerHTML = `<details style="margin-top:4px"><summary class="small">恢复前的自动备份（${r.files.length} 个，可以用来撤销恢复）</summary>
        <div class="qlist" style="margin-top:8px">${r.files.map((f) => `<div class="qrow"><div><div class="t">${esc(f.name)}</div>
          <div class="r">${new Date(f.mtime * 1000).toLocaleString("zh-CN", { hour12: false })} · ${fmtSize(f.size)}</div></div>
          <button class="btn sm" data-auto="${esc(f.name)}">恢复到这个</button></div>`).join("")}</div>
        <div class="hint">保存在 ${esc(r.dir)}，只保留最近 5 个。</div></details>`;
      $$("[data-auto]").forEach((b) => b.onclick = async () => {
        if (!confirm("恢复到这个自动备份？当前数据同样会先自动备份一份。")) return;
        try { const res = await api("/api/restore_auto", { name: b.dataset.auto }); toast(`✓ 已恢复：${res.items} 条视频`); await refreshState(); renderSettings(); }
        catch (e) { toast(e.message, 5000); }
      });
    }
  } catch {}
}

/* ---------------------------------------------------------------- 模型下拉 */
const modelCache = { main: null, deep: null };
function fillPick(pickId, inputId, models, hintId, live) {
  const sel = $("#" + pickId), inp = $("#" + inputId);
  if (!sel) return;
  const cur = inp.value.trim();
  const list = [...new Set([...(models || []), cur].filter(Boolean))];
  sel.innerHTML = `<option value="">${list.length ? "选择…" : "无列表"}</option>` + list.map((m) => `<option value="${esc(m)}" ${m === cur ? "selected" : ""}>${esc(m)}</option>`).join("");
  sel.onchange = () => { if (sel.value) { inp.value = sel.value; toast(`已选择 ${sel.value}，记得点「测试连接」或「保存设置」`); } };
  const h = $("#" + hintId);
  if (h) h.textContent = live ? `已从服务商读取到 ${models.length} 个可用模型，点右边的箭头选择。` : "点右边的箭头从常用模型里选；填好 Key 后会自动读取完整列表。";
}

/* ---------------------------------------------------------------- 图文：画廊与大图 */
function galleryHtml(images, ver) {
  const v = ver ? `?v=${Math.floor(ver * 1000)}` : "";
  return `<div class="gallery">${images.map((src, i) => `<img src="/files/${encodeURI(src)}${v}" data-g="${i}" loading="lazy" alt="图 ${i + 1}">`).join("")}</div>`;
}
function bindGallery(root, images) {
  if (!images?.length) return;
  $$("[data-g]", root).forEach((img) => img.onclick = () => openLightbox(images, +img.dataset.g));
}
function openLightbox(images, idx) {
  let box = $("#lightbox");
  if (!box) {
    box = document.createElement("div"); box.id = "lightbox"; box.className = "lightbox";
    box.innerHTML = `<button class="lb-btn lb-close" title="关闭 (Esc)">${ico("x")}</button><button class="lb-btn lb-prev" title="上一张 (←)">‹</button>
      <img alt=""><button class="lb-btn lb-next" title="下一张 (→)">›</button><div class="lb-count"></div>`;
    document.body.appendChild(box);
  }
  const show = () => {
    idx = (idx + images.length) % images.length;
    $("img", box).src = "/files/" + encodeURI(images[idx]);
    $(".lb-count", box).textContent = `${idx + 1} / ${images.length}`;
    $(".lb-prev", box).hidden = $(".lb-next", box).hidden = images.length < 2;
  };
  const close = () => { box.hidden = true; document.removeEventListener("keydown", onKey); };
  const onKey = (e) => { if (e.key === "Escape") close(); if (e.key === "ArrowLeft") { idx--; show(); } if (e.key === "ArrowRight") { idx++; show(); } };
  $(".lb-close", box).onclick = close;
  $(".lb-prev", box).onclick = (e) => { e.stopPropagation(); idx--; show(); };
  $(".lb-next", box).onclick = (e) => { e.stopPropagation(); idx++; show(); };
  box.onclick = (e) => { if (e.target === box) close(); };
  document.addEventListener("keydown", onKey);
  box.hidden = false; show();
}

/* ---------------------------------------------------------------- 免费方案 */
let freePick = null;
function freePlanHtml(s) {
  const FP = STATE.free_plans || {};
  const cur = s.free_plan && FP[s.free_plan];
  return `<div class="card form free-card" style="margin-bottom:16px" id="freeCard">
    <div class="row"><h2 style="margin:0">免费方案</h2><span class="chip">推荐新手</span><span class="spacer"></span>
      ${cur ? `<span class="chip teal">✓ 正在使用：${esc(cur.name)} · ${esc(s.model)}</span>` : ""}</div>
    <p class="muted" style="margin:-6px 0 0">用你自己账号的免费额度，不花钱。免费模型够日常提炼用；想要更好的效果（尤其是「带我精读」），可以在下面换成付费模型。</p>
    <div class="plans">${Object.entries(FP).map(([k, p]) => `
      <button class="plan ${freePick === k ? "on" : ""} ${s.free_plan === k ? "using" : ""}" data-plan="${k}">
        <div class="row" style="gap:6px"><b>${esc(p.name)}</b><span class="chip ${p.tag === "海外" ? "gray" : ""}">${esc(p.tag)}</span></div>
        <div class="muted small">${esc(p.desc)}</div></button>`).join("")}</div>
    <div id="freeSteps"></div>
  </div>`;
}
function setupFreePlan() {
  $$("#freeCard [data-plan]").forEach((b) => b.onclick = () => {
    freePick = b.dataset.plan;
    $$("#freeCard .plan").forEach((x) => x.classList.toggle("on", x === b));
    renderFreeSteps();
  });
  if (freePick) renderFreeSteps();
}
function renderFreeSteps() {
  const p = STATE.free_plans[freePick];
  $("#freeSteps").innerHTML = `<ol class="free-steps">
      <li><b>注册 / 登录</b>：<a href="${esc(p.signup)}" target="_blank" rel="noopener">打开 ${esc(p.name)} 官网 →</a></li>
      <li><b>创建 API Key 并复制</b>：<a href="${esc(p.key_url)}" target="_blank" rel="noopener">打开 API Key 页面 →</a>（点「创建」/「新建 API Key」，然后复制）</li>
      <li><b>粘贴到这里，点一键配置</b>
        <div class="row" style="margin-top:8px"><input id="freeKey" class="search" type="password" placeholder="粘贴 ${esc(p.name)} 的 API Key" autocomplete="off" style="flex:1">
          <button class="btn primary" id="freeGo">一键配置</button></div>
        <div class="small" id="freeRes" style="margin-top:8px"></div></li>
    </ol>`;
  $("#freeGo").onclick = async () => {
    const key = $("#freeKey").value.trim();
    if (!key) return toast("先把 Key 粘贴进来");
    $("#freeGo").disabled = true; $("#freeRes").innerHTML = `<span class="muted">正在测试并挑选免费模型……</span>`;
    try {
      const r = await api("/api/free_setup", { plan: freePick, api_key: key });
      toast(`配置好了：${r.name} · ${r.model}`, 3500);
      freePick = null; modelCache.main = null;
      await renderSettings();
    } catch (e) {
      $("#freeRes").innerHTML = `<span style="color:var(--bad)">✗ ${esc(e.message)}</span>`;
      $("#freeGo").disabled = false;
    }
  };
}

/* ---------------------------------------------------------------- 空状态与骨架屏 */
function emptyHtml(icon, title, desc, actions = "") {
  return `<div class="empty-state" style="grid-column:1/-1">
    <div class="es-art">${ico(icon, "ic es-ic")}</div>
    <h2>${title}</h2><p class="muted">${desc}</p>
    ${actions ? `<div class="row" style="justify-content:center;margin-top:6px">${actions}</div>` : ""}</div>`;
}
function skeletonLibrary() {
  const card = `<div class="sk-card"><div class="sk sk-cover"></div><div class="sk-body"><div class="sk sk-line w80"></div><div class="sk sk-line"></div><div class="sk sk-line w60"></div></div></div>`;
  return `<div class="head"><div><div class="sk sk-h1"></div><div class="sk sk-line w40"></div></div></div>
    <div class="sk sk-block"></div><div class="grid">${card.repeat(6)}</div>`;
}
function skeletonItem() {
  return `<div class="detail"><div><div class="sk sk-line w20" style="margin-bottom:22px"></div><div class="sk sk-h1 w70"></div>
      <div class="sk sk-line w30"></div><div class="sk sk-block" style="height:110px;margin-top:34px"></div>
      <div class="sk sk-block" style="height:220px"></div></div>
    <div><div class="sk sk-block" style="aspect-ratio:16/10;height:auto"></div><div class="sk sk-line"></div><div class="sk sk-line w60"></div></div></div>`;
}

/* ---------------------------------------------------------------- 知识网络：图谱 + 共识观点 */
Object.assign(ICONS, {
  flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  diamond: '<path d="M12 2.7 21.3 12 12 21.3 2.7 12z"/>',
});

let graphData = null, graphShowViews = true, graphSel = null;
let gView = { x: 0, y: 0, k: 1 };

async function renderGraphPage(tab, category, soft = false) {
  const tabs = `<div class="seg" id="gTabs">
      <a href="#/graph" class="${tab === "map" ? "on" : ""}">图谱</a>
      <a href="#/graph/consensus" class="${tab === "consensus" ? "on" : ""}">共识观点</a></div>`;
  const headHtml = `<div class="head"><div><h1>知识网络</h1>
      <div class="muted">${tab === "map" ? "有共同关键词（标签、概念、工具）的笔记连成线，线越粗关联越多" : "让 AI 把一个分类里的多条笔记放在一起看：哪些观点被多条视频互相印证，哪些说法不一致"}</div></div>
      <div class="spacer"></div>${tabs}</div>`;
  if (tab === "consensus") return renderConsensus(headHtml, category, soft);
  view.innerHTML = headHtml + `<div class="card graph-card"><div class="sk sk-block" style="height:420px;margin:0"></div></div>`;
  graphData = await api("/api/graph");
  drawGraph(headHtml);
}

function drawGraph(headHtml) {
  const g = graphData;
  if (g.nodes.length < 2 || (!g.links.length && !g.views.length)) {
    view.innerHTML = headHtml + `<div class="card">${emptyHtml("link", "笔记之间还没有连起来",
      g.nodes.length < 2 ? "学习库里至少要有两条笔记。" : "现在的笔记之间还没有共同的标签、概念或工具。笔记多起来以后，这里会自动连成网。",
      `<a class="btn" href="#/process">${ico("plus")}添加更多笔记</a>`)}</div>`;
    return;
  }
  const cats = [...new Set(g.nodes.map((n) => n.category))];
  view.innerHTML = headHtml + `
    <div class="graph-wrap">
      <div class="card graph-card">
        <div class="row graph-tools">
          <div class="legend">${cats.map((c) => `<span><i class="dot cat-${catColor(c)}"></i>${esc(c)}</span>`).join("")}
            ${g.views.length ? `<span><i class="gdia"></i>共识观点</span>` : ""}</div>
          <span class="spacer"></span>
          ${g.views.length ? `<label class="check small"><input type="checkbox" id="gViews" ${graphShowViews ? "checked" : ""}> 显示共识观点</label>` : ""}
          <button class="btn sm" id="gFit">复位</button>
        </div>
        <svg id="gSvg" class="gsvg" role="img" aria-label="笔记关系图"></svg>
        <div class="muted small graph-hint">滚轮缩放，拖动空白处移动；点一个圆点看它和谁有关，双击打开笔记</div>
      </div>
      <aside class="card graph-side" id="gSide"></aside>
    </div>`;
  $("#gViews") && ($("#gViews").onchange = (e) => { graphShowViews = e.target.checked; layoutAndPaint(); });
  $("#gFit").onclick = () => { gView = { x: 0, y: 0, k: 1 }; applyView(); };
  layoutAndPaint();
}

function applyView() { const z = $("#gZoom"); if (z) z.setAttribute("transform", `translate(${gView.x},${gView.y}) scale(${gView.k})`); }

/* 简单的力导向布局：同步算好再画（几百个点以内很快） */
function forceLayout(all, links, W, H) {
  // 没有任何连线的笔记不参与受力计算，最后沿外圈摆放；否则会被排斥力推到四个角上
  const linked = new Set(); links.forEach((l) => { linked.add(l.s); linked.add(l.t); });
  const nodes = all.filter((n) => linked.has(n)), lone = all.filter((n) => !linked.has(n));
  const byCat = {}; nodes.forEach((n) => (byCat[n.cat] ||= []).push(n));
  const cs = Object.keys(byCat);
  cs.forEach((c, ci) => {  // 同一分类先放在一起，布局收敛得快
    const a0 = (2 * Math.PI * ci) / cs.length, r = Math.min(W, H) * 0.28;
    byCat[c].forEach((n, i) => {
      const a = a0 + i * 0.9;
      n.x = W / 2 + Math.cos(a0) * r + Math.cos(a) * 18 * Math.sqrt(i + 1);
      n.y = H / 2 + Math.sin(a0) * r + Math.sin(a) * 18 * Math.sqrt(i + 1);
      n.vx = n.vy = 0;
    });
  });
  // Fruchterman–Reingold：点之间互相排斥、连线把两端拉近，每步移动距离逐渐变小（降温）
  const N = nodes.length, iters = N > 300 ? 150 : 300;
  const k = Math.min(90, Math.sqrt((W * H) / Math.max(all.length, 1)) * 0.7);
  const mx = 64, my = 28;  // 留出标签的位置
  let temp = W / 8;
  for (let it = 0; it < iters; it++) {
    for (const n of nodes) n.vx = n.vy = 0;
    for (let i = 0; i < N; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < N; j++) {
        const b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d = Math.sqrt(dx * dx + dy * dy) || 0.1;
        const f = (k * k) / d / d;
        a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
      }
    }
    for (const l of links) {
      const dx = l.t.x - l.s.x, dy = l.t.y - l.s.y, d = Math.sqrt(dx * dx + dy * dy) || 0.1;
      const f = (d / k) * (l.view ? 2 : 0.7 + Math.min(l.w, 4) * 0.2);  // 共同关键词越多拉得越紧；共识观点贴着它的笔记
      l.s.vx += dx * f; l.s.vy += dy * f; l.t.vx -= dx * f; l.t.vy -= dy * f;
    }
    for (const n of nodes) {
      n.vx += (W / 2 - n.x) * 0.06; n.vy += (H / 2 - n.y) * 0.06;  // 轻轻拉向中间，不相连的几团不会飘走
      const len = Math.sqrt(n.vx * n.vx + n.vy * n.vy) || 1, step = Math.min(len, temp);
      n.x = Math.max(mx, Math.min(W - mx, n.x + (n.vx / len) * step));
      n.y = Math.max(my, Math.min(H - my, n.y + (n.vy / len) * step));
    }
    temp = Math.max(0.5, temp * 0.975);
  }
  // 没连线的笔记：在外圈上逐个挑离已有点最远的位置
  const placed = [...nodes], rx = W / 2 - mx, ry = H / 2 - my;
  for (const n of lone) {
    let best = -1;
    for (let i = 0; i < 72; i++) {
      const a = (i / 72) * 2 * Math.PI, x = W / 2 + Math.cos(a) * rx, y = H / 2 + Math.sin(a) * ry;
      const d = placed.reduce((m, p) => Math.min(m, Math.hypot(p.x - x, p.y - y)), Infinity);
      if (d > best) { best = d; n.x = x; n.y = y; }
    }
    placed.push(n);
  }
}

function layoutAndPaint() {
  const svg = $("#gSvg"); if (!svg) return;
  // 画布用实际像素大小，文字不会被缩得看不清
  const W = Math.max(300, Math.round(svg.clientWidth || 800));
  const H = W < 600 ? Math.round(W * 1.15) : Math.max(420, Math.min(720, Math.round(W * 0.62)));
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const nodes = graphData.nodes.map((n) => ({ ...n, key: "n" + n.id, cat: n.category }));
  const byKey = new Map(nodes.map((n) => [n.key, n]));
  const links = graphData.links.map((l) => ({ ...l, s: byKey.get("n" + l.source), t: byKey.get("n" + l.target) }));
  if (graphShowViews) for (const v of graphData.views) {
    const vn = { ...v, key: v.id, cat: v.category, isView: true };
    nodes.push(vn); byKey.set(v.id, vn);
    for (const id of v.items) if (byKey.get("n" + id)) links.push({ s: vn, t: byKey.get("n" + id), view: true, w: 1 });
  }
  forceLayout(nodes, links, W, H);
  const nbr = new Map(nodes.map((n) => [n.key, new Set()]));
  links.forEach((l) => { nbr.get(l.s.key).add(l.t.key); nbr.get(l.t.key).add(l.s.key); });
  const rad = (n) => 5 + Math.min(n.deg || 0, 8) * 1.1;
  const pos = (n) => `translate(${n.x.toFixed(1)},${n.y.toFixed(1)})`;
  svg.innerHTML = `<g id="gZoom">
    ${links.map((l) => `<line class="glink${l.view ? " gl-view" : ""}" data-a="${esc(l.s.key)}" data-b="${esc(l.t.key)}" x1="${l.s.x.toFixed(1)}" y1="${l.s.y.toFixed(1)}" x2="${l.t.x.toFixed(1)}" y2="${l.t.y.toFixed(1)}" stroke-width="${l.view ? 1.2 : (0.8 + Math.min(l.w, 5) * 0.7).toFixed(1)}"/>`).join("")}
    ${nodes.map((n) => n.isView
      ? `<g class="gnode gn-view" data-k="${esc(n.key)}" transform="${pos(n)}" tabindex="0" role="button" aria-label="共识观点：${esc(n.view)}">
          <rect x="-7" y="-7" width="14" height="14" rx="2.5" transform="rotate(45)"/><title>${esc(n.view)}</title></g>`
      : `<g class="gnode cat-${catColor(n.cat)}${n.learned ? " learned" : ""}" data-k="${n.key}" transform="${pos(n)}" tabindex="0" role="button" aria-label="${esc(n.title)}">
          <circle r="${rad(n)}"/>${(n.deg || 0) >= 3 ? `<text y="${rad(n) + 13}">${esc(n.title.slice(0, 12))}</text>` : ""}<title>${esc(n.title)}</title></g>`).join("")}
  </g>`;
  applyView();

  const focus = (key) => {
    svg.classList.toggle("focus", !!key);
    const near = key ? nbr.get(key) : new Set();
    $$(".gnode", svg).forEach((el) => el.classList.toggle("hl", !!key && (el.dataset.k === key || near.has(el.dataset.k))));
    $$(".glink", svg).forEach((el) => el.classList.toggle("hl", !!key && (el.dataset.a === key || el.dataset.b === key)));
  };
  const select = (key) => { graphSel = key; focus(key); renderGraphSide(key ? byKey.get(key) : null, byKey, links); };
  $$(".gnode", svg).forEach((el) => {
    el.addEventListener("mouseenter", () => { if (!graphSel) focus(el.dataset.k); });
    el.addEventListener("mouseleave", () => { if (!graphSel) focus(null); });
    el.addEventListener("click", (e) => { e.stopPropagation(); select(graphSel === el.dataset.k ? null : el.dataset.k); });
    el.addEventListener("keydown", (e) => { if (e.key === "Enter") select(el.dataset.k); });
    el.addEventListener("dblclick", () => { const n = byKey.get(el.dataset.k); if (!n.isView) location.hash = "#/item/" + n.id; });
  });
  // 拖动空白处平移，滚轮缩放
  let drag = null;
  svg.onpointerdown = (e) => { if (e.target.closest(".gnode")) return; drag = { x: e.clientX, y: e.clientY, vx: gView.x, vy: gView.y, moved: false }; svg.setPointerCapture(e.pointerId); };
  svg.onpointermove = (e) => {
    if (!drag) return;
    const s = W / svg.clientWidth;
    gView.x = drag.vx + (e.clientX - drag.x) * s; gView.y = drag.vy + (e.clientY - drag.y) * s;
    drag.moved ||= Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) > 4; applyView();
  };
  svg.onpointerup = () => { if (drag && !drag.moved) select(null); drag = null; };
  svg.onwheel = (e) => {
    e.preventDefault();
    const rect = svg.getBoundingClientRect(), s = W / rect.width;
    const px = (e.clientX - rect.left) * s, py = (e.clientY - rect.top) * s;
    const k2 = Math.max(0.4, Math.min(4, gView.k * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
    gView.x = px - ((px - gView.x) * k2) / gView.k; gView.y = py - ((py - gView.y) * k2) / gView.k; gView.k = k2; applyView();
  };
  select(graphSel && byKey.has(graphSel) ? graphSel : null);
}

function renderGraphSide(n, byKey, links) {
  const side = $("#gSide"); if (!side) return;
  const g = graphData;
  if (!n) {
    const top = [...g.nodes].sort((a, b) => b.deg - a.deg).slice(0, 5).filter((x) => x.deg);
    side.innerHTML = `<h2>概况</h2>
      <div class="gstats"><div><b>${g.nodes.length}</b><span>条笔记</span></div><div><b>${g.links.length}</b><span>条关联</span></div><div><b>${g.views.length}</b><span>个共识</span></div></div>
      ${top.length ? `<h3>关联最多的笔记</h3><ol class="glist">${top.map((x) => `<li><a href="#/item/${x.id}">${esc(x.title)}</a><span class="muted small"> · ${x.deg} 条</span></li>`).join("")}</ol>` : ""}
      ${g.views.length ? "" : `<p class="muted small">到「共识观点」里整理一个分类，图里会多出菱形的共识观点，连着支持它的几条笔记。</p>`}`;
    return;
  }
  if (n.isView) {
    side.innerHTML = `<div class="small muted">共识观点 · ${esc(n.category)}</div>
      <h2 class="gside-title">${esc(n.view)}</h2>
      <h3>${n.items.length} 条视频都这么说</h3>
      <ul class="glist">${n.items.map((id) => byKey.get("n" + id)).filter(Boolean).map((x) => `<li><a href="#/item/${x.id}">${esc(x.title)}</a></li>`).join("")}</ul>
      <a class="btn sm" href="#/graph/consensus/${encodeURIComponent(n.category)}">看完整整理 →</a>`;
    return;
  }
  const rel = links.filter((l) => !l.view && (l.s.key === n.key || l.t.key === n.key))
    .map((l) => ({ other: l.s.key === n.key ? l.t : l.s, shared: l.shared || [], w: l.w })).sort((a, b) => b.w - a.w);
  const views = links.filter((l) => l.view && l.t.key === n.key).map((l) => l.s);
  side.innerHTML = `<div class="row" style="gap:6px">${catChip(n.category)}${n.learned ? `<span class="chip teal">${ico("check", "ic sm")}已学</span>` : ""}</div>
    <h2 class="gside-title">${esc(n.title)}</h2>
    <a class="btn sm primary" href="#/item/${n.id}">打开笔记</a>
    ${views.length ? `<h3>支持的共识观点</h3><ul class="glist">${views.map((v) => `<li>${esc(v.view)}</li>`).join("")}</ul>` : ""}
    <h3>${rel.length ? `和 ${rel.length} 条笔记有关` : "暂时没有关联的笔记"}</h3>
    <ul class="glist">${rel.map((x) => `<li><a href="#/item/${x.other.id}">${esc(x.other.title)}</a>
      <div class="muted small">共同：${x.shared.map(esc).join("、")}</div></li>`).join("")}</ul>`;
}

async function renderConsensus(headHtml, category, soft) {
  if (category) return renderConsensusDetail(headHtml, category, soft);
  if (!soft) view.innerHTML = headHtml + `<div class="sk sk-block" style="height:220px"></div>`;
  const r = await api("/api/insights");
  const ins = r.runner || {}, keyOk = STATE.settings.api_key_set;
  view.innerHTML = headHtml + `
    ${keyOk ? "" : `<div class="banner info"><div>整理共识观点要用 AI，先到设置里配好 AI Key。</div><span class="spacer"></span><a class="btn sm primary" href="#/settings">去配置 →</a></div>`}
    ${r.categories.length ? `<div class="cgrid">${r.categories.map((c) => {
      const running = ins.category === c.category, queued = !running && (ins.pending || []).includes(c.category);
      const err = (ins.errors || {})[c.category];
      const status = running ? `<span class="chip teal">整理中…</span>`
        : queued ? `<span class="chip gray">排队中</span>`
        : c.done ? `<span class="chip teal">${c.consensus} 条共识</span>${c.new ? `<span class="chip warn">新增 ${c.new} 条笔记</span>` : ""}`
        : `<span class="chip gray">未整理</span>`;
      const can = c.n >= 2 && keyOk && !running && !queued;
      return `<div class="card ccard">
        <div class="row"><i class="dot cat-${catColor(c.category)}"></i><b>${esc(c.category)}</b><span class="spacer"></span><span class="muted small">${c.n} 条笔记</span></div>
        <div class="row" style="gap:6px;flex-wrap:wrap">${status}</div>
        ${err ? `<div class="small" style="color:var(--bad)">${esc(err)}</div>` : ""}
        <div class="row ccard-foot">
          ${c.done ? `<a class="btn sm primary" href="#/graph/consensus/${encodeURIComponent(c.category)}">查看</a>` : ""}
          <span class="spacer"></span>
          ${c.n < 2 ? `<span class="muted small">至少 2 条笔记才能比较</span>`
            : `<button class="btn sm ${c.done ? "ghost" : ""}" data-build="${esc(c.category)}" ${can ? "" : "disabled"}>${c.done ? "重新整理" : "整理共识"}</button>`}
        </div></div>`; }).join("")}</div>
      <p class="muted small" style="margin-top:14px">每整理一个分类调用一次 AI（用「设置 → 精读」里的模型）。结果也会保存成 Markdown，放在笔记文件夹的「_共识观点」里，在 Obsidian 里能点链接跳回原笔记。</p>`
    : `<div class="card">${emptyHtml("book", "学习库还是空的", "先添加几条笔记，再来这里找它们之间的共识。")}</div>`}`;
  $$("[data-build]").forEach((b) => b.onclick = async () => {
    try { await api("/api/insights", { category: b.dataset.build }); toast("开始整理，一般需要半分钟到两分钟"); await refreshState(); renderConsensus(headHtml, "", true); }
    catch (e) { toast(e.message, 4000); }
  });
}

async function renderConsensusDetail(headHtml, category, soft) {
  if (!soft) view.innerHTML = headHtml + `<div class="sk sk-block" style="height:320px"></div>`;
  let ins;
  try { ins = await api("/api/insights/" + encodeURIComponent(category)); }
  catch (e) { view.innerHTML = headHtml + `<div class="card">${emptyHtml("search", esc(e.message), "", `<a class="btn" href="#/graph/consensus">← 返回分类列表</a>`)}</div>`; return; }
  const d = ins.data, T = ins.titles || {};
  const busy = STATE.insights?.category === category || (STATE.insights?.pending || []).includes(category);
  const src = (ids) => ids.map((id) => T[id] ? `<a class="src" href="#/item/${id}">${esc(T[id])}</a>` : "").join("");
  view.innerHTML = headHtml + `
    <a class="back" href="#/graph/consensus">← 全部分类</a>
    <div class="card cdetail">
      <div class="row"><h2 style="margin:0"><i class="dot big-dot cat-${catColor(category)}"></i>${esc(category)}</h2><span class="spacer"></span>
        <button class="btn sm" id="cReveal">${ico("folder")}在文件夹中显示</button>
        <button class="btn sm ghost" id="cRedo" ${busy ? "disabled" : ""}>${busy ? "整理中…" : "重新整理"}</button></div>
      <div class="muted small">由 ${esc(ins.model || "")} 从 ${ins.item_ids.length} 条笔记中整理 · ${new Date(ins.created_at * 1000).toLocaleString("zh-CN", { hour12: false })}</div>
      ${d.overview ? `<div class="summary" style="margin-top:14px">${esc(d.overview)}</div>` : ""}
    </div>
    <section><h2>共识观点 <span class="muted small">多条视频互相印证</span></h2>
      ${d.consensus.length ? `<ol class="cons-list">${d.consensus.map((c) => `<li class="card">
        <div class="cons-head"><b>${esc(c.view)}</b><span class="chip teal">${c.item_ids.length} 条视频</span></div>
        ${c.detail ? `<p>${esc(c.detail)}</p>` : ""}
        <div class="srcs">${src(c.item_ids)}</div></li>`).join("")}</ol>`
      : `<p class="muted">这个分类的笔记之间没有找到被多条视频共同支持的观点。笔记多起来以后再整理一次试试。</p>`}
    </section>
    ${d.conflicts.length ? `<section><h2>说法不一致的地方</h2>${d.conflicts.map((c) => `<div class="card conflict">
      <b>${esc(c.topic)}</b>
      <div class="sides">${c.sides.map((s) => `<div class="side-v"><div>${esc(s.view)}</div><div class="srcs">${src(s.item_ids)}</div></div>`).join("")}</div>
      ${c.advice ? `<div class="advice">${ico("bulb")}<span>${esc(c.advice)}</span></div>` : ""}</div>`).join("")}</section>` : ""}`;
  $("#cReveal").onclick = () => api("/api/open", { what: "insight", category }).catch((e) => toast(e.message));
  $("#cRedo").onclick = async () => {
    try { await api("/api/insights", { category }); toast("开始重新整理"); await refreshState(); renderConsensusDetail(headHtml, category, true); }
    catch (e) { toast(e.message, 4000); }
  };
}

/* ---------------------------------------------------------------- 每周周报 */
async function renderWeekly(offset) {
  view.innerHTML = `<div class="sk sk-h1"></div><div class="sk sk-block" style="height:140px"></div><div class="sk sk-block" style="height:260px"></div>`;
  const r = await api("/api/weekly?offset=" + offset);
  if (weeklyDue?.due && r.week === weeklyDue.week) {  // 看过了，不再提示
    weeklyDue.due = false; $("#navWeekly").hidden = true;
    api("/api/weekly/seen", { week: r.week }).catch(() => {});
  }
  const tile = (n, label, sub = "") => `<div class="wtile"><b>${n}</b><span>${label}</span>${sub ? `<em>${sub}</em>` : ""}</div>`;
  const maxCat = Math.max(1, ...r.categories.map((c) => c.n));
  const list = (items) => `<ul class="wlist">${items.map((it) => `<li><i class="dot cat-${catColor(it.category)}"></i><a href="#/item/${it.id}">${esc(it.title)}</a></li>`).join("")}</ul>`;
  const cheer = r.streak >= 4 ? "已经养成习惯了，继续保持" : r.streak >= 2 ? "连着好几周了，别断" : r.streak === 1 ? "开了个好头" : "这周学一条，就能开始计数";
  view.innerHTML = `
    <div class="head"><div><h1>学习周报</h1><div class="muted">${esc(r.label)}${r.is_current ? " · 本周（还在进行中）" : ""}</div></div>
      <div class="spacer"></div>
      <div class="row week-nav">
        <a class="btn sm" href="#/weekly/${r.offset - 1}">‹ 上一周</a>
        ${r.is_current ? "" : `<a class="btn sm" href="#/weekly">本周</a>`}
        ${r.is_current ? `<button class="btn sm" disabled>下一周 ›</button>` : `<a class="btn sm" href="#/weekly/${r.offset + 1}">下一周 ›</a>`}
      </div></div>
    <div class="card streak-card">
      <div class="streak-ic">${ico("flame")}</div>
      <div><div class="streak-n">连续学习 <b>${r.streak}</b> 周</div><div class="muted small">${cheer}。标记学会、精读、做测验、回答检查题都算学习。</div></div>
    </div>
    ${r.has_any ? `
    <div class="wtiles">
      ${tile(r.new, "条新笔记")}
      ${tile(r.learned, "条学会")}
      ${tile(r.deep, "条精读")}
      ${tile(r.quizzes, "次测验", r.quiz_accuracy != null ? `正确率 ${r.quiz_accuracy}%` : "")}
      ${tile(r.checks + r.asks, "次答题和提问", r.checks || r.asks ? `检查题 ${r.checks} · 问老师 ${r.asks}` : "")}
      ${tile(r.tokens.toLocaleString(), "AI tokens", r.tokens ? "" : "从这个版本开始统计")}
    </div>
    <div class="wgrid">
      ${r.categories.length ? `<div class="card"><h2>新笔记都在学什么</h2>
        <div class="wbars">${r.categories.map((c) => `<div class="wbar"><span class="wlabel">${esc(c.category)}</span>
          <span class="wtrack"><i class="cat-${catColor(c.category)}" style="width:${Math.round((c.n / maxCat) * 100)}%"></i></span><b>${c.n}</b></div>`).join("")}</div>
        ${r.top_tags.length ? `<h3>高频关键词</h3><div class="row" style="gap:6px;flex-wrap:wrap">${r.top_tags.map((t) => `<span class="chip gray">${esc(t)}</span>`).join("")}</div>` : ""}
      </div>` : ""}
      ${r.learned_items.length ? `<div class="card"><h2>这周学会了</h2>${list(r.learned_items)}</div>` : ""}
      ${r.insights.length ? `<div class="card"><h2>整理了共识观点</h2><ul class="wlist">${r.insights.map((i) => `<li><i class="dot cat-${catColor(i.category)}"></i><a href="#/graph/consensus/${encodeURIComponent(i.category)}">${esc(i.category)}</a><span class="muted small"> · ${i.consensus} 条</span></li>`).join("")}</ul></div>` : ""}
    </div>` : `<div class="card">${emptyHtml("coffee", r.is_current ? "这周还没开始" : "这周没有学习记录", r.is_current ? "随便挑一条笔记学一下，周报就会热闹起来。" : "休息一下也没关系。")}</div>`}
    ${r.suggest.length ? `<div class="card" style="margin-top:16px"><div class="row"><h2 style="margin:0">接下来先学这几条</h2><span class="spacer"></span><span class="muted small">还有 ${r.unlearned} 条没学，这几条收进来最久</span></div>${list(r.suggest)}</div>` : ""}
    <div class="row" style="margin-top:18px"><span class="spacer"></span>
      <button class="btn" id="wSave">${ico("download")}保存为 Markdown 到笔记文件夹</button></div>`;
  $("#wSave").onclick = async () => {
    try { await api("/api/weekly/save", { offset: r.offset }); toast("已保存到「_周报」文件夹"); }
    catch (e) { toast(e.message, 4000); }
  };
}

/* ======================================================== 技能库（只碰 AI / 学习类） ======================================================== */
let SKILLS = null, skillsTab = "do", skillsBusy = false;

function skCover(src, name) {
  // 只画确实存在的本地封面；没有就用色块，绝不放会裂的远程图
  if (src && src.startsWith("/files/")) {
    return `<span class="sk-cover"><img src="${esc(src)}" loading="lazy" alt="" onerror="this.parentNode.innerHTML='<b>'+${JSON.stringify((name || "技")[0] || "技")}+'</b>'"></span>`;
  }
  return `<span class="sk-cover sk-cover-ph"><b>${esc((name || "技")[0] || "技")}</b></span>`;
}
function skTime(t) { return t ? new Date(t * 1000).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "还没审查"; }

function skCard(s, rank) {
  // 取第一个真正有本地封面的来源（都已校验过属于该条，不会张冠李戴）
  const c = ((s.sources || []).find(x => x.cover && x.cover.startsWith("/files/")) || {}).cover || null;
  const p = s.priority || 1;
  return `<div class="sk-card${rank === 1 ? " sk-first" : ""}" data-sid="${esc(s.id)}">
    <div class="sk-row">
      ${skCover(c, s.name)}
      <div class="sk-main">
        <div class="sk-title"><b>${esc(s.name)}</b>${rank === 1 ? `<span class="chip teal">今天就做这个</span>` : ""}
          ${s.status === "later" ? `<span class="chip gray">暂缓</span>` : `<span class="chip ${p >= 4 ? "warn" : "gray"}">P${p}</span>`}
          <span class="chip gray">${esc(s.category)}</span>
          ${(() => { const q = s.platform || "通用"; const cls = q === "dsh" ? "sk-plat-dsh" : q === "workbuddy" ? "sk-plat-wb" : q === "不适用" ? "bad" : "gray";
            return `<span class="chip ${cls}">${esc(q === "dsh" ? "DSH" : q === "workbuddy" ? "WorkBuddy" : q)}</span>`; })()}
          ${s.already ? `<span class="chip teal">已装</span>` : ""}
          ${s.learned ? `<span class="chip teal">已学</span>` : ""}
          ${s.n > 1 ? `<span class="chip gray">${s.n} 条笔记</span>` : ""}
          ${s.verified === false ? `<span class="chip bad">本地待核对</span>` : ""}
          ${rank ? `<span class="sk-rank">#${rank}</span>` : ""}
        </div>
        <div class="sk-why">${esc(s.why || "在多条笔记里反复出现，值得动手")}</div>
        <div class="sk-act">👉 ${esc(s.action || "打开来源笔记，照步骤试一遍")}</div>
        <div class="sk-src">来源：${(s.sources || []).slice(0, 3).map(x => `<a href="#/item/${x.id}" title="本地笔记已校验">${esc(x.title)}</a>`).join(" · ") || "—"}</div>
      </div>
      <div class="sk-btns">
        <button class="btn sm" data-smark="${esc(s.id)}" data-field="installed">${(s.installed || s.already) ? "取消已装" : "标为已装"}</button>
        <button class="btn sm ghost" data-smark="${esc(s.id)}" data-field="ignored">不看这条</button>
      </div>
    </div>
  </div>`;
}

function skDupCard(g, i) {
  return `<div class="sk-card sk-dup">
    <div class="sk-row">
      <span class="sk-cover sk-cover-ph"><b>重</b></span>
      <div class="sk-main">
        <div class="sk-title"><b>${esc(g.kind)}</b><span class="chip gray">${(g.items || []).length} 条${g.total ? " / 共 " + g.total + " 条" : ""}</span></div>
        <div class="sk-why">${esc(g.reason || "内容重复")}${g.kind === "同一技能" ? " · 点开合并着看" : " · 点开逐条看，自己决定留哪条"}</div>
        <div class="sk-src">${(g.items || []).map(x => `<a href="#/item/${x.id}">${esc(x.title)}</a>`).join(" · ")}</div>
      </div>
      <div class="sk-btns"><a class="btn sm" href="#/dups">去查重页</a></div>
    </div>
  </div>`;
}

function skOldCard(o) {
  return `<div class="sk-card sk-old">
    <div class="sk-row">
      ${skCover(o.cover, o.title)}
      <div class="sk-main">
        <div class="sk-title"><b>${esc(o.title)}</b><span class="chip bad">建议删除</span><span class="chip gray">${esc(o.category)}</span></div>
        <div class="sk-why">${esc(o.reason)}</div>
        <div class="sk-src"><a href="#/item/${o.id}">打开笔记确认</a>${o.md_ok ? " · 本地文件在" : " · 本地文件缺失"}</div>
      </div>
      <div class="sk-btns"><button class="btn sm ghost" data-sdel="${o.id}">移入回收站</button></div>
    </div>
  </div>`;
}

async function renderSkills(tab) {
  if (tab) skillsTab = tab;
  let r;
  try { r = await api("/api/skills"); } catch (e) { view.innerHTML = `<div class="card">${esc(e.message)}</div>`; return; }
  SKILLS = r.report || {};
  const pr = r.progress || {};
  if (pr.running && !skillsBusy) { skillsBusy = true; pollSkills(); }
  const d = SKILLS;
  const local = d.local || {};
  const all = d.skills || [];
  const byId = Object.fromEntries(all.map(s => [s.id, s]));
  const topIds = d.top || [];
  const top = topIds.map(id => byId[id]).filter(Boolean);
  const doList = all.filter(s => s.status === "do" && !s.ignored);
  const later = all.filter(s => s.status === "later" && !s.ignored);
  const installed = all.filter(s => s.installed || s.status === "installed");
  const ignored = all.filter(s => s.ignored || s.status === "ignored");
  const dups = d.duplicates || [], olds = d.obsolete || [];

  const tabs = [
    ["do", "可执行", doList.length], ["dup", "重复项", dups.length + (d.clusters || []).length],
    ["old", "落后/建议删除", olds.length], ["installed", "已装", installed.length],
    ["later", "暂缓", later.length], ["ignored", "已忽略", ignored.length],
  ];
  view.innerHTML = `
    <div class="head"><div><h1>技能库</h1>
      <div class="muted">只整理 AI 与学习类笔记，娱乐/美食/健身一律不碰；每条都校验过本地笔记与封面</div></div>
      <span class="spacer"></span>
      <button class="btn primary" id="skReview">${ico("sparkles")}重新审查</button></div>

    <div class="card sk-plat">
      <div class="sk-plat-main"><b>我实际在用的平台</b>
        <div class="muted small">推荐只落到这些平台上；PATH 里探测到但你不用的工具会自动排除</div></div>
      <input id="skPlatInput" class="sk-plat-input" value="${esc((local.active_platforms || ["dsh", "workbuddy"]).join(", "))}" spellcheck="false" />
      <button class="btn primary sm" id="skPlatSave">保存并重审</button>
      <div class="muted small sk-plat-path">PATH 探测到（不作推荐依据）：${(local.installed || []).map(x => esc(x)).join("、") || "无"}</div>
    </div>

    <div class="sk-overview">
      <div class="sk-stat"><b>${doList.length}</b><span>可执行</span></div>
      <div class="sk-stat"><b>${dups.length}<em>+${(d.clusters || []).length}</em></b><span>真重复 + 同技能散落</span></div>
      <div class="sk-stat"><b>${olds.length}</b><span>建议删除</span></div>
      <div class="sk-stat"><b>${installed.length}</b><span>已装</span></div>
      <div class="sk-stat sk-stat-wide"><span>上次审查：${skTime(d.reviewed_at)}</span>
        <span>大脑：${esc(local.model || "未配")} ｜ 实际在用 ${(local.active_platforms || []).length} 个平台 ｜ AI 笔记 ${local.ai_notes || 0} 条</span>
        <span class="muted small" id="skOverviewStep">${pr.running ? "审查中：" + esc(pr.step || "") : (d.filtered_no_file ? "已过滤 " + d.filtered_no_file + " 条本地缺文件的笔记" : "本地文件全部校验通过")}</span></div>
    </div>

    <div class="card" style="margin-bottom:16px"><b>本机全局情况（已脱敏）</b>
      <div class="sk-local">
        <div><span class="muted small">实际在用（推荐依据）</span>
          <div>${(local.active_platforms || []).map(x => `<span class="chip teal">${esc(x)}</span>`).join(" ") || "未设置"}</div>
          <span class="muted small" style="display:block;margin-top:8px">PATH 探测到（不参与推荐）</span>
          <div>${(local.installed || []).map(x => `<span class="chip gray">${esc(x)}</span>`).join(" ") || "无"}</div></div>
        <div><span class="muted small">主要分类</span><div>${Object.entries(local.top_cats || {}).map(([k, v]) => `<span class="chip gray">${esc(k)} ${v}</span>`).join(" ")}</div></div>
        <div><span class="muted small">记忆库偏好（仅本机显示，不上传）</span><div class="muted small sk-prefs">${(local.prefs || []).slice(0, 2).map(x => esc(String(x).slice(0, 38))).join("<br>") || "未读取"}</div></div>
      </div></div>

    <div class="tabs" id="skTabs" style="margin-bottom:14px">
      ${tabs.map(([v, l, n]) => `<button data-t="${v}" class="${skillsTab === v ? "on" : ""}">${l} ${n ? `<b>${n}</b>` : ""}</button>`).join("")}
    </div>

    <div id="skBody"></div>`;

  const body = $("#skBody");
  if (d.empty) {
    body.innerHTML = `<div class="card"><h2>还没审查过</h2><p class="muted">点右上角「重新审查」，大脑会结合本机环境与记忆库，把已拆解的 AI/学习类笔记排成可执行清单。</p></div>`;
  } else if (skillsTab === "do") {
    const groups = [
      ["dsh", "DSH · 多 Agent / 插件 / MCP / 会话"],
      ["workbuddy", "WorkBuddy · 账号池 / 日报 / 自动化"],
      ["通用", "通用 · 两个平台都能用"],
    ];
    const rank = new Map(top.map((s, i) => [s.id, i + 1]));
    body.innerHTML = `<div class="card" style="margin-bottom:14px"><b>优先建议（前 ${top.length} 条，按平台分类）</b>
      <div class="muted small">组内按优先级 P5→P1 排；# 是总榜名次。不在实际平台上的技能已自动移到「暂缓」。</div></div>
      ${groups.map(([q, label]) => {
        const items = top.filter(s => (s.platform || "通用") === q);
        return `<div class="sk-group"><b>${label}</b><span class="muted small">${items.length} 条</span></div>` +
          (items.length ? items.map(s => skCard(s, rank.get(s.id))).join("") : `<div class="card muted small">这一组暂时没有优先建议</div>`);
      }).join("") || `<div class="card">暂时没有可执行的，点「重新审查」再跑一次。</div>`}
      <div class="card" style="margin-top:18px"><b>其余可执行（${Math.max(0, doList.length - top.length)} 条，按优先级排）</b>
        <div class="muted small">这些大脑没逐条点评，但同样能直接动手。</div></div>
      <div class="sk-more">${doList.filter(s => !topIds.includes(s.id)).slice(0, 40)
        .map(s => skCard(s, 0)).join("") || `<div class="card">没有更多了</div>`}</div>`;
  } else if (skillsTab === "dup") {
    const cl = d.clusters || [];
    body.innerHTML = `<div class="card" style="margin-bottom:14px"><b>真重复（标题相同 / 内容几乎一样）</b>
      <div class="muted small">这些是同一件事被存了多次，点开逐条看，自己决定留哪条，不会自动删。</div></div>
      ${dups.slice(0, 40).map(skDupCard).join("") || `<div class="card">没有发现真重复</div>`}
      <div class="card" style="margin:18px 0 14px"><b>同一个技能散落在多条笔记里（${cl.length}）</b>
        <div class="muted small">不算重复，但内容被拆散了，可以照着合并看。</div></div>
      ${cl.slice(0, 30).map(g => skDupCard({ kind: g.skill + "（" + g.total + " 条）", reason: g.reason, items: g.items })).join("") || `<div class="card">没有</div>`}`;
  } else if (skillsTab === "old") {
    body.innerHTML = `<div class="card" style="margin-bottom:14px"><b>落后 / 已被替代，建议删除</b>
      <div class="muted small">只是候选，点「移入回收站」才会动，随时能恢复。</div></div>
      ${olds.map(skOldCard).join("") || `<div class="card">没有发现明显过时的内容</div>`}`;
  } else {
    const list = skillsTab === "installed" ? installed : skillsTab === "later" ? later : ignored;
    body.innerHTML = list.slice(0, 80).map(s => skCard(s, 0)).join("") || `<div class="card">这里是空的</div>`;
  }

  $$("#skTabs button").forEach(b => b.onclick = () => renderSkills(b.dataset.t));
  const pSave = $("#skPlatSave");
  if (pSave) pSave.onclick = async () => {
    const val = ($("#skPlatInput").value || "").split(/[,，\s]+/).filter(Boolean);
    pSave.disabled = true; pSave.textContent = "重审中…";
    try {
      await api("/api/skills/platforms", { platforms: val });
      await api("/api/skills/review", {});
      skillsBusy = false;
      toast("平台已保存，正在按新平台重新审查");
      pollSkills();
    } catch (e) { toast(e.message, 4000); pSave.disabled = false; pSave.textContent = "保存并重审"; }
  };
  $("#skReview").onclick = async () => {
    const b = $("#skReview"); b.disabled = true; b.textContent = "审查中…";
    try { await api("/api/skills/review", {}); skillsBusy = false; pollSkills(); }
    catch (e) { toast(e.message, 4000); b.disabled = false; }
  };

  $$("#skBody [data-smark]").forEach(btn => btn.onclick = async () => {
    const cur = byId[btn.dataset.smark];
    const val = !(cur && cur[btn.dataset.field]);
    await api("/api/skills/mark", { ids: [btn.dataset.smark], field: btn.dataset.field, value: val });
    toast(val ? "已标记" : "已取消"); renderSkills(skillsTab);
  });
  $$("#skBody [data-sdel]").forEach(btn => btn.onclick = async () => {
    if (!confirm("把这条移进回收站？（可恢复）")) return;
    await api(`/api/items/${btn.dataset.sdel}/action`, { action: "delete" });
    toast("已移入回收站"); renderSkills(skillsTab);
  });
}

async function pollSkills() {
  if (skillsBusy) return;
  skillsBusy = true;
  for (let i = 0; i < 120; i++) {
    await new Promise(r => setTimeout(r, 3000));
    let r;
    try { r = await api("/api/skills"); } catch (e) { break; }
    if (!r.progress || !r.progress.running) {
      skillsBusy = false;
      toast("审查完成，清单已更新");
      renderSkills(skillsTab);
      return;
    }
  }
  skillsBusy = false;
}
