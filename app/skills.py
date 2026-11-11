"""技能库：把已拆解的 AI / 学习类笔记，变成一份「能执行」的清单。

- 只碰 AI 与学习类，娱乐类一律不动
- 每条技能都校验本地笔记文件与封面，绝不让预览图和内容对不上
- 大脑审查 = 本机已配的模型 + 本地全局情况（不上传健康/财务/案件等隐私）
- 结果落盘 data/skills.json，页面随时可读，不反复烧额度
"""
from __future__ import annotations

import json
import difflib
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

from . import config, db, llm

FILE = config.DATA / "skills.json"
PFILE = config.DATA / "skills_platforms.json"
DEFAULT_PLATFORMS = ["dsh", "workbuddy"]
PLATFORM_LABELS = {"dsh": "DSH", "workbuddy": "WorkBuddy", "通用": "通用", "不适用": "不适用"}
CATS = ("AI 编程", "AI 工具推荐", "提示词技巧", "AI 办公效率", "AI 副业与变现",
        "AI 绘画与视频", "大模型与行业资讯", "AI 学习方法", "学习与成长")

# 只在「标题 / 工具名」里找，避免正文里一句"这也被淘汰了"就误判
OLD_WORDS = ("已停服", "停止服务", "已下线", "停止维护", "已弃用", "不再维护", "别再装",
             "已封", "不能用了", "已失效", "已过期", "GPT-4", "Claude 2", "Claude 2.1",
             "文心一言 3", "New Bing", "Bard", "AutoGPT", "2023年版", "2023 版")

PROBES = {
    "Codex": ["codex"], "Claude Code": ["claude"], "Node.js": ["node"],
    "Git": ["git"], "Python": ["python"], "yt-dlp": ["yt-dlp"], "ffmpeg": ["ffmpeg"],
    "VS Code": ["code"], "Docker": ["docker"], "Obsidian": ["obsidian"],
}
NL = chr(10)


def get_platforms():
    """用户「实际在用」的平台；PATH 里探测到不算。"""
    try:
        v = [str(x).strip().lower() for x in
             (json.loads(PFILE.read_text(encoding="utf-8")).get("platforms") or []) if str(x).strip()]
        return v or list(DEFAULT_PLATFORMS)
    except Exception:
        return list(DEFAULT_PLATFORMS)


def set_platforms(value):
    out = []
    for x in (value or []):
        x = str(x).strip().lower()
        if x and x not in out and re.fullmatch(r"[\w一-鿿.+-]{1,24}", x):
            out.append(x)
    PFILE.parent.mkdir(parents=True, exist_ok=True)
    PFILE.write_text(json.dumps({"platforms": out or list(DEFAULT_PLATFORMS)},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    return get_platforms()


# 平台归类：dsh / workbuddy / 通用 / 不适用
P_DSH = ("dsh", "harness", "deepseek harness", "子 agent", "多 agent", "多子", "子会话",
         "agent 编排", "插件", "skill", "mcp", "cli ", "命令行", "破甲", "模型路由", "多会话")
P_WB = ("workbuddy", "账号池", "网关", "日报", "积分", "外派", "面板", "dashboard",
        "定时任务", "自动刷", "批量账号", "转发", "多账号")
P_OUT = ("codex", "claude code", "claude", "cursor", "windsurf", "vscode", "vs code",
         "jetbrains", "cline", "roo code", "aider")


def platform_of(name, text=""):
    t = (str(name or "") + " " + str(text or "")).lower()
    if any(k in t for k in P_OUT):
        return "不适用"
    d = any(k in t for k in P_DSH)
    w = any(k in t for k in P_WB)
    if d and w:
        return "通用"
    if d:
        return "dsh"
    if w:
        return "workbuddy"
    return "通用"


def _lib() -> Path:
    return config.library_dir()


def _local_ok(p) -> bool:
    try:
        return bool(p) and Path(p).is_file()
    except Exception:
        return False


def _cover_for(it):
    """只返回确实存在、且属于这条的本地封面；没有就 None（绝不拿远端图凑）。"""
    cov = (it.get("cover") or "").strip()
    if not cov.startswith("/files/"):
        return None
    f = _lib() / cov[len("/files/"):]
    if not f.is_file() or f.stat().st_size < 512:
        return None
    aid = str(it.get("aweme_id") or "")
    if aid and aid not in str(f):
        return None
    return cov


def _focus_ai(text):
    t = str(text or "").strip()
    for cut in ("以及摄影与剪辑", "美食与烹饪", "健身与健康", "穿搭与美妆"):
        if cut in t:
            t = t.split(cut)[0]
            break
    return (t.rstrip("，,、 ").strip() + "。娱乐、美食、健身、穿搭不在本技能库范围")[:160]


def _local_state():
    """本地全局情况：只取与技术偏好有关的，绝不把健康/财务/案件带出去。"""
    import shutil
    installed = [name for name, cmds in PROBES.items() if any(shutil.which(c) for c in cmds)]
    s = config.load()
    st = db.stats()
    by_cat = {c["category"]: c["n"] for c in (st.get("categories") or [])
              if isinstance(c, dict) and c.get("category")}
    prefs = []
    rule = Path(r"E:\AI\个人大脑\notes\00_规则.md")
    if rule.is_file():
        for line in rule.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip().lstrip("#-> ").strip()
            if not (8 < len(line) < 120):
                continue
            if re.search(r"优先级|先交付|工具|AI|学习|效率|模型|决策|结论", line) and not re.search(
                    r"负债|药|体检|取保|现金|股金|房|体重|睡眠|失业|疾病|案件", line):
                prefs.append(line)
    handover = Path(r"E:\AI\个人大脑_交接.md")
    if handover.is_file():
        m = re.search(r"已装：([^\n]{5,160})", handover.read_text(encoding="utf-8", errors="ignore"))
        if m:
            prefs.append("已装软件：" + m.group(1).strip())
    return {
        "installed": installed,  # PATH 探测结果，仅展示，不作为推荐依据
        "active_platforms": get_platforms(),
        "model": (s.get("model") or "").strip(),
        "provider": (s.get("provider") or "").strip(),
        # focus 只保留与 AI/学习有关的部分：健身、美食、穿搭不进提示词
        "focus": _focus_ai((s.get("focus_topic") or "")),
        "prefs": prefs[:8],
        "ai_notes": sum(n for c, n in by_cat.items() if c in CATS),
        "done": st.get("by_status", {}).get("done", 0),
        "top_cats": dict(Counter({c: n for c, n in by_cat.items() if c in CATS}).most_common(6)),
    }


def _rows():
    """已拆解、且在 AI / 学习分类里的条目（娱乐类完全不进）。"""
    q = ",".join("?" * len(CATS))
    rs = db.conn().execute(
        "SELECT id,title,author,category,learned,starred,md_path,cover,url,platform,"
        "aweme_id,created_at,published_at,note_json FROM items "
        "WHERE status='done' AND COALESCE(deleted_at,0)=0 AND category IN (" + q + ")",
        CATS).fetchall()
    out = []
    for r in rs:
        d = dict(r)
        d["md_ok"] = _local_ok(d.get("md_path"))
        d["cover"] = _cover_for(d) if d["md_ok"] else None
        try:
            d["note"] = json.loads(d.get("note_json") or "{}")
        except Exception:
            d["note"] = {}
        out.append(d)
    return out


def _norm(name):
    s = re.sub(r"[（(].*?[)）]", "", str(name or ""))
    s = re.sub(r"\s+", " ", s).strip().lower()
    s = re.sub(r"[^\w\u4e00-\u9fff.+-]", "", s)
    return s[:48]


def _tools_of(it):
    out = []
    for t in (it["note"].get("tools") or [])[:8]:
        if isinstance(t, dict):
            n = (t.get("name") or "").strip()
            use = (t.get("use") or "").strip()
        else:
            n, use = str(t).strip(), ""
        if n and len(n) < 60:
            out.append({"name": n, "use": use[:120]})
    return out


def collect():
    """把笔记聚合成技能条目（按工具/主题归一）。"""
    rows = [r for r in _rows() if r["md_ok"]]
    buckets = defaultdict(list)
    for it in rows:
        tools = _tools_of(it)
        if not tools:
            key = _norm(it["note"].get("title") or it["title"])[:40] or ("n%d" % it["id"])
            buckets["topic:" + key].append((it, None))
        for t in tools:
            k = _norm(t["name"])
            if k:
                buckets["tool:" + k].append((it, t))
    skills = []
    for key, pairs in buckets.items():
        src, seen = [], set()
        for it, t in pairs:
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            src.append({"id": it["id"], "title": (it["note"].get("title") or it["title"] or "")[:60],
                        "category": it["category"], "learned": bool(it["learned"]),
                        "cover": it["cover"], "md_ok": it["md_ok"], "url": it["url"] or ""})
        first_it, first_t = pairs[0]
        name = (first_t or {}).get("name") or first_it["note"].get("title") or first_it["title"]
        cat = Counter(x[0]["category"] for x in pairs).most_common(1)[0][0]
        steps, points = [], []
        for it, _ in pairs[:3]:
            steps += [str(x)[:120] for x in (it["note"].get("steps") or [])[:2]]
            points += [str(x)[:120] for x in (it["note"].get("points") or [])[:2]]
        skills.append({
            "id": key, "name": str(name)[:60], "category": cat,
            "verified": all(x["md_ok"] for x in src) and all(
                (not x["cover"]) or x["cover"].startswith("/files/") for x in src),
            "kind": "tool" if key.startswith("tool:") else "topic",
            "use": (first_t or {}).get("use", ""), "steps": steps[:5], "points": points[:5],
            "sources": src, "n": len(src),
            "learned": any(x[0]["learned"] for x in pairs),
            "date": max((x[0].get("published_at") or x[0].get("created_at") or 0) for x in pairs),
        })
    for s in skills:
        s["platform"] = platform_of(s["name"], s.get("use") or "")
        s["generic"] = (len(_norm(s["name"])) < 3 or _norm(s["name"]) in {
            "ai", "aigc", "工具", "教程", "方法", "抖音", "微信", "小红书", "网站", "软件", "模型", "平台"})
    skills.sort(key=lambda s: (-int(s["learned"]), -s["n"], -s["date"]))
    return skills


def _grams(text, n=3):
    t = re.sub(r"[\s\W_]+", "", str(text or "").lower())
    if len(t) < n:
        return set()
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _dup_groups():
    """自动选重复项：只认「标题归一后相同」或「正文三元组重合度 ≥ 0.62」的真重复。

    不再用之前那套把「排骨做法」和「AI 开源项目」判成一样的相似度。
    """
    rows = [r for r in _rows() if r["md_ok"]]
    allowed = set(CATS)
    groups, used = [], set()

    # ① 标题归一后完全相同
    by_title = defaultdict(list)
    for it in rows:
        t = re.sub(r"#\S+|【[^】]*】|[\s\W_]+", "", (it["note"].get("title") or it["title"] or "")).lower()
        if len(t) >= 6:
            by_title[t].append(it)
    for t, items in by_title.items():
        if len(items) >= 2:
            groups.append({"kind": "标题完全相同", "reason": "归一化标题一致",
                           "items": [{"id": x["id"], "title": (x["note"].get("title") or x["title"] or "")[:60],
                                      "category": x["category"], "cover": x["cover"]} for x in items]})
            used |= {x["id"] for x in items}

    # ①.5 标题高度近似（改一两个字就算同一条）
    free = [r for r in rows if r["id"] not in used]
    for i in range(len(free)):
        for j in range(i + 1, len(free)):
            a, b = free[i], free[j]
            if a["id"] in used or b["id"] in used:
                continue
            ta = (a["note"].get("title") or a["title"] or "")
            tb = (b["note"].get("title") or b["title"] or "")
            if len(ta) < 6 or abs(len(ta) - len(tb)) > 12:
                continue
            if difflib.SequenceMatcher(None, ta, tb).ratio() >= 0.80:
                groups.append({"kind": "标题只差几个字",
                               "items": [{"id": a["id"], "title": ta[:60], "category": a["category"], "cover": a["cover"]},
                                         {"id": b["id"], "title": tb[:60], "category": b["category"], "cover": b["cover"]}]})
                used |= {a["id"], b["id"]}

    # ② 正文三元组重合度（只比 120 字以上的正文）
    grams, meta = {}, {}
    for it in rows:
        if it["id"] in used:
            continue
        text = " ".join([it["note"].get("summary") or ""] + [str(x) for x in (it["note"].get("points") or [])[:6]])
        if len(text) < 120:
            continue
        grams[it["id"]] = _grams(text)
        meta[it["id"]] = it
    ids = list(grams)
    seen = set()
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if a in seen or b in seen:
                continue
            if _jaccard(grams[a], grams[b]) >= 0.45:
                ia, ib = meta[a], meta[b]
                groups.append({"kind": "内容几乎一样", "reason": "正文重合度很高，基本是同一条被重复收藏",
                               "items": [{"id": ia["id"], "title": (ia["note"].get("title") or ia["title"] or "")[:60],
                                          "category": ia["category"], "cover": ia["cover"]},
                                         {"id": ib["id"], "title": (ib["note"].get("title") or ib["title"] or "")[:60],
                                          "category": ib["category"], "cover": ib["cover"]}]})
                seen |= {a, b}
    return groups[:40]


def clusters():
    """同一个技能散落在多条笔记里 —— 单独一类，用来合并着看，不算内容重复。"""
    out = []
    for s in collect():
        if s["n"] >= 2:
            out.append({"kind": "同一技能", "skill": s["name"], "reason": "出现在 %d 条笔记里" % s["n"],
                        "items": [{"id": x["id"], "title": x["title"], "category": x["category"],
                                   "cover": x["cover"]} for x in s["sources"][:8]],
                        "skill_id": s["id"], "total": s["n"]})
    out.sort(key=lambda g: -g["total"])
    return out[:30]


def _old_candidates(rows):
    out = []
    now = time.time()
    for it in rows:
        head = (it["title"] or "") + " " + (it["note"].get("title") or "")
        tools = " ".join(t.get("name", "") for t in _tools_of(it))
        hits = [w for w in OLD_WORDS if w.lower() in (head + " " + tools).lower()]
        age_days = (now - (it.get("published_at") or it.get("created_at") or now)) / 86400
        # 行业快讯满一年、或标题里出现明显的旧版本/停服信号，才算建议删除候选
        news = it["category"] == "大模型与行业资讯"
        if hits or (news and age_days > 120):
            reason = ("标题/工具名里有旧版本或停服信号：" + "、".join(hits[:3])) if hits                 else "120 天前的模型/行业快讯，结论多半已被新版覆盖"
            out.append({"id": it["id"], "title": (it["note"].get("title") or it["title"] or "")[:60],
                        "category": it["category"], "reason": reason, "cover": it["cover"],
                        "md_ok": it["md_ok"]})
    return out[:60]


def _ask(cfg, prompt, log, json_mode=True):
    try:
        text, _ = llm.chat(cfg, [{"role": "user", "content": prompt}],
                           json_mode=json_mode, temperature=0,
                           max_tokens=3000 if json_mode else 6000, timeout=180)
        return llm.parse_json(text)
    except Exception as e:
        if json_mode:
            return _ask(cfg, prompt, log, json_mode=False)
        log("大脑这一批没返回 JSON：" + str(e)[:80])
        return {}


def _brain(skills, local, log=print):
    """分批让大脑审查（一次太多会被思考型模型吃掉输出）。"""
    cfg = config.llm_cfg(config.load(), "main")
    ctx = ("你是用户的本地技能审查大脑。他从收藏里拆出 AI / 学习类技能，结合他本机的全局情况，"
           "挑出最值得现在动手的。" + NL +
           "规则：只评 AI / 学习相关；已装过的工具降权并说明；明显过时/被替代/停服的标 obsolete=true；" +
           "每条给 priority(1-5，5最高)、why(一句话，结合他的情况)、action(具体下一步)。" + NL +
           "边界：action 只能是 AI 工具/编程/提示词/学习类动作；不要建议健身、健康、饮食、睡眠、穿搭、摄影器材；" +
           "不要引用任何健康或财务数据。" + NL +
           "平台说明：dsh = 多 Agent / 插件 / MCP / 子会话 / 模型路由的工作台；" +
           "workbuddy = 账号池网关、日报、外派任务、定时任务与面板的自动化工作台。" + NL +
           "平台：本机【实际在用】的平台只有 active_platforms 里的那些；installed 只是 PATH 探测结果，" +
           "不算你在用。禁止建议安装/配置 Codex、Claude Code、Cursor、VS Code 等其它工具。" +
           "每条给 platform（只能是 dsh / workbuddy / 通用 / 不适用 之一）；" +
           "不适用当前平台的技能 priority=1 并在 why 里写明原因；action 必须能在当前平台上落地。" + NL +
           '只输出 JSON：{"items":[{"id":"...","priority":5,"why":"...","action":"...","platform":"dsh","obsolete":false}]}' + NL + NL +
           "【本机全局情况】" + json.dumps(local, ensure_ascii=False)[:1200] + NL + NL)
    out = {}
    batch_size = 14
    rank = {"dsh": 0, "workbuddy": 0, "通用": 1, "不适用": 3}
    cand = [s for s in skills if s.get("platform") != "不适用" and not s.get("generic")]
    cand.sort(key=lambda s: (rank.get(s.get("platform"), 2), -s["n"], -int(s["learned"])))
    top = cand[:70]
    for i in range(0, len(top), batch_size):
        batch = top[i:i + batch_size]
        digest = [{"id": s["id"], "name": s["name"], "cat": s["category"], "n": s["n"],
                   "use": (s["use"] or "")[:70], "points": s["points"][:2],
                   "learned": s["learned"]} for s in batch]
        d = _ask(cfg, ctx + "【技能清单】" + json.dumps(digest, ensure_ascii=False)[:4500], log)
        for x in (d.get("items") or []):
            if x.get("id"):
                out[str(x["id"])] = x
        log("大脑审查 %d/%d" % (i + len(batch), len(top)))
    return out


def _pick_top(do, active, k=24):
    """总榜：先按优先级，再给每个实际平台保底 2 条，避免某个平台分组是空的。"""
    picked = []
    for p in active:
        for s in [x for x in do if x.get("platform") == p][:2]:
            if s not in picked:
                picked.append(s)
    for s in do:
        if len(picked) >= k:
            break
        if s not in picked:
            picked.append(s)
    picked.sort(key=lambda x: (-int(x.get("priority") or 0), -int(x.get("learned") or 0), -int(x.get("n") or 0)))
    return [x["id"] for x in picked[:k]]


def review(log=print):
    """审查一次并落盘。每次都重新读本机全局情况。"""
    local = _local_state()
    skills = collect()
    brain = _brain(skills, local, log=log)
    active = set(local.get("active_platforms") or DEFAULT_PLATFORMS)
    # 只有「实际在用」的平台算已装；PATH 里的 codex/claude 不算
    installed = set(active)
    for s in skills:
        v = brain.get(s["id"]) or {}
        plat = str(v.get("platform") or "").strip()
        if plat not in PLATFORM_LABELS:
            plat = platform_of(s["name"], s.get("use") or "")
        s["platform"] = plat
        s["platform_src"] = "brain" if str(v.get("platform") or "").strip() in PLATFORM_LABELS else "local"
        s["why"] = str(v.get("why") or "")[:160]
        s["action"] = str(v.get("action") or "")[:160]
        s["obsolete"] = bool(v.get("obsolete"))
        s["already"] = bool(installed & {s["name"].lower(), _norm(s["name"])})
        try:
            pr = int(v.get("priority") or 0)
        except Exception:
            pr = 0
        s["priority"] = max(1, min(5, pr)) if pr else 0
        neg = str(v.get("action") or "") + " " + str(v.get("why") or "")
        s["skip"] = bool(re.search(r"跳过|不部署|不必|没增量|为零|偏离|先不|不建议|不要单独|没有边际收益", neg))
        if s["skip"]:
            s["priority"] = 1
        # 不在实际平台上的，或建议里偷偷让人装 Codex/Claude Code 的，一律归暂缓
        if s["platform"] == "不适用" or re.search(
                r"codex|claude code|cursor|vs ?code|windsurf", neg, re.I):
            s["priority"] = 1
            s["skip"] = True
            if not s["why"]:
                s["why"] = "依赖其它平台的工具，本机实际在用 " + "、".join(sorted(active)) + "，先不做"
        if not s["priority"]:
            s["priority"] = 1 if s["platform"] == "不适用" else                 min(5, 2 + min(2, s["n"] // 3) + int(s["learned"]) - int(s["already"]))
            if not s["why"]:
                s["why"] = "在 %d 条笔记里出现" % s["n"] + ("，且你已学过" if s["learned"] else "")
            if not s["action"]:
                s["action"] = "打开来源笔记，照步骤试一遍"
    # 状态：可执行的、已装的、暂缓的、用户忽略的
    for s in skills:
        if s.get("ignored"):
            s["status"] = "ignored"
        elif s.get("obsolete"):
            s["status"] = "obsolete"
        elif s.get("installed") or s.get("already"):
            s["status"] = "installed"
        elif s.get("skip"):
            s["status"] = "later"
        else:
            s["status"] = "do"
    do = sorted([s for s in skills if s["status"] == "do" and s.get("platform") != "不适用"
                 and not s.get("generic")],
                key=lambda x: (-x["priority"], -int(x["learned"]), -x["n"]))
    data = {
        "reviewed_at": time.time(), "local": local,
        "top": _pick_top(do, local.get("active_platforms") or DEFAULT_PLATFORMS),
        "skills": skills, "duplicates": _dup_groups(), "clusters": clusters(),
        "obsolete": _old_candidates(_rows()),
        "filtered_no_file": sum(1 for r in _rows() if not r["md_ok"]),
        "scope": list(CATS),
    }
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    log("技能库审查完成：%d 个技能，%d 组重复，%d 条过时候选" %
        (len(skills), len(data["duplicates"]), len(data["obsolete"])))
    return data


_PROGRESS = {"running": False, "step": "", "started": 0}


def refresh_local():
    """只重算本地那几块（重复/同技能/过时/本机环境），不动大脑给过的结论。"""
    if not FILE.is_file():
        return review()
    d = json.loads(FILE.read_text(encoding="utf-8"))
    d["local"] = _local_state()
    d["duplicates"] = _dup_groups()
    d["clusters"] = clusters()
    d["obsolete"] = _old_candidates(_rows())
    # 旧缓存补齐平台字段：不在实际在用平台上的立即移出可执行清单
    active = set(d["local"].get("active_platforms") or DEFAULT_PLATFORMS)
    for s in d.get("skills") or []:
        if not s.get("platform_src") == "brain":
            s["platform"] = platform_of(s["name"], s.get("use") or "")
        s["generic"] = (len(_norm(s["name"])) < 3 or _norm(s["name"]) in {
            "ai", "aigc", "工具", "教程", "方法", "抖音", "微信", "小红书", "网站", "软件", "模型", "平台"})
        if s["platform"] == "不适用" or re.search(
                r"codex|claude code|cursor|vs ?code|windsurf",
                (s.get("action") or "") + " " + (s.get("why") or ""), re.I):
            s["priority"] = 1
            s["skip"] = True
            s["status"] = "later"
            if not s.get("why"):
                s["why"] = "依赖其它平台的工具，本机实际在用 " + "、".join(sorted(active)) + "，先不做"
        elif s.get("status") == "later" and not s.get("skip") and not s.get("ignored"):
            s["status"] = "do"
    desc = sorted([s for s in d["skills"] if s.get("status") == "do" and s.get("platform") != "不适用"
                   and not s.get("generic")],
                  key=lambda x: (-int(x.get("priority") or 0), -int(x.get("learned") or 0), -int(x.get("n") or 0)))
    d["top"] = _pick_top(desc, d["local"].get("active_platforms") or DEFAULT_PLATFORMS)
    d["reviewed_at_local"] = time.time()
    for s in d.get("skills") or []:
        if s.get("obsolete") and s["id"] not in {o["id"] for o in d["obsolete"]}:
            s["obsolete"] = False
    FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def progress():
    return dict(_PROGRESS)


def review_async():
    """后台跑一次审查，页面轮询 progress()。"""
    import threading
    if _PROGRESS["running"]:
        return False

    def job():
        _PROGRESS.update(running=True, step="正在读取本机环境与记忆库", started=time.time())
        try:
            review(log=lambda m: _PROGRESS.update(step=str(m)[:80]))
        except Exception as e:
            _PROGRESS["step"] = "审查失败：" + str(e)[:70]
        finally:
            _PROGRESS["running"] = False
    threading.Thread(target=job, daemon=True, name="skills-review").start()
    return True


def report():
    if not FILE.is_file():
        return {"empty": True, "reviewed_at": 0}
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"empty": True, "reviewed_at": 0}
    # 兼容旧缓存：读取时补齐状态与优先清单，不用重跑大脑
    skills = d.get("skills") or []
    if skills and (not d.get("top") or "status" not in skills[0]):
        for s in skills:
            if s.get("ignored"):
                s["status"] = "ignored"
            elif s.get("obsolete"):
                s["status"] = "obsolete"
            elif s.get("installed") or s.get("already"):
                s["status"] = "installed"
            elif s.get("skip"):
                s["status"] = "later"
            else:
                s["status"] = "do"
        do = sorted([s for s in skills if s["status"] == "do"],
                    key=lambda x: (-int(x.get("priority") or 0), -int(x.get("learned") or 0), -int(x.get("n") or 0)))
        d["top"] = [x["id"] for x in do[:24]]
        try:
            FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass
    d.setdefault("duplicates", [])
    d.setdefault("clusters", [])
    d.setdefault("obsolete", [])
    d.setdefault("local", {})
    d.setdefault("top", [])
    return d


def mark(ids, field, value=True):
    """标记已装 / 忽略，不动娱乐类。"""
    d = report()
    if d.get("empty"):
        return 0
    ids = {str(x) for x in ids}
    n = 0
    for s in d.get("skills", []):
        if s["id"] in ids:
            s[field] = bool(value)
            n += 1
    FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return n
