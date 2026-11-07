"""把被误判成「主题无关」的收藏重新审查一遍，够格的放回学习库。

之前「关注主题」只写了 AI，导致摄影后期、美食、健身这些干货也被判成无关，
还因为 AI 自拟分类，全都堆进了「其他」。审查分两步：
1) 先按标题/摘要做规则分类，有把握的直接恢复（不花钱）；
2) 剩下的交给 AI 判断一下属于哪个分类（没配 Key 就跳过）。
"""
from . import classify, db, llm, notes

KEEP_OUT = {"生活与娱乐", "其他"}   # 这两类保持「无关」，等你手动收
MIN_SCORE = 12                      # 规则命中分太低的不乱恢复

# 旧数据里的子分类是 AI 自拟的（"摄影后期调色"、"其他（美食教程）"…），
# 按关键词收敛回分类表里的正经子分类
SUB_HINT = {
    "摄影与剪辑": [("调色", "调色修图"), ("修图", "调色修图"), ("后期", "调色修图"), ("降噪", "调色修图"),
                ("布光", "布光"), ("打光", "布光"), ("灯光", "布光"), ("灯位", "布光"),
                ("剪辑", "视频剪辑"), ("转场", "视频剪辑"), ("影视", "影视制作"), ("分镜", "影视制作"),
                ("拍摄", "摄影拍摄"), ("摄影", "摄影拍摄"), ("构图", "摄影拍摄"), ("器材", "摄影拍摄"),
                ("镜头", "摄影拍摄"), ("审美", "摄影拍摄"), ("相机", "摄影拍摄")],
    "学习与成长": [("英语", "英语语言"), ("日语", "英语语言"), ("外语", "英语语言"), ("语言", "英语语言"),
                ("考试", "考试考证"), ("考证", "考试考证"), ("考研", "考试考证"),
                ("读书", "阅读读书"), ("阅读", "阅读读书"), ("书", "阅读读书"),
                ("方法", "学习方法"), ("学习", "学习方法"), ("效率", "学习方法"),
                ("认知", "认知思维"), ("思维", "认知思维"), ("成长", "认知思维"), ("心理", "认知思维")],
    "商业与创业": [("电商", "电商运营"), ("淘宝", "电商运营"), ("店铺", "电商运营"),
                ("小红书", "营销流量"), ("抖音", "营销流量"), ("流量", "营销流量"), ("营销", "营销流量"),
                ("销售", "职场"), ("职场", "职场"), ("面试", "职场"), ("简历", "职场"),
                ("创业", "创业经验"), ("副业", "创业经验"), ("赚钱", "创业经验")],
    "健身与健康": [("减脂", "减脂"), ("减肥", "减脂"), ("瘦", "减脂"), ("体脂", "减脂"),
                ("增肌", "力量训练"), ("力量", "力量训练"), ("训练", "力量训练"),
                ("跑步", "有氧运动"), ("有氧", "有氧运动"), ("运动", "有氧运动"),
                ("健康", "健康养生"), ("养生", "健康养生"), ("睡眠", "健康养生"), ("饮食", "健康养生")],
    "美食与烹饪": [("减脂餐", "减脂餐"), ("健身餐", "健身餐"), ("烘焙", "烘焙甜品"), ("甜点", "烘焙甜品"),
                ("探店", "探店"), ("咖啡", "饮品咖啡"), ("饮品", "饮品咖啡"),
                ("菜谱", "家常菜"), ("做菜", "家常菜"), ("美食", "家常菜"), ("食", "家常菜")],
    "穿搭与美妆": [("男装", "男装穿搭"), ("女装", "女装穿搭"), ("穿搭", "男装穿搭"), ("衣服", "男装穿搭"),
                ("护肤", "美妆护肤"), ("美妆", "美妆护肤"), ("妆", "美妆护肤"), ("变美", "美妆护肤"),
                ("发型", "发型造型"), ("头发", "发型造型")],
}


def _guess_sub(category, text):
    """按关键词把乱七八糟的子分类收敛到分类表里的那个。"""
    subs = classify.SUBS.get(category) or []
    text = (text or "").lower()
    for kw, sub in SUB_HINT.get(category, []):
        if kw in text and sub in subs:
            return sub
    return ""


def normalize_subs(log=None, dry=False):
    """把所有分类下的「野」子分类收敛到正经名单，没把握的置空（显示为未细分）。"""
    rows = db.conn().execute(
        "SELECT id,title,category,subcategory FROM items "
        "WHERE COALESCE(deleted_at,0)=0 AND category IS NOT NULL AND subcategory IS NOT NULL "
        "AND subcategory<>''").fetchall()
    fixed, cleared = 0, 0
    for r in rows:
        cat, sub = r["category"], r["subcategory"]
        if cat not in classify.SUBS or sub in (classify.SUBS.get(cat) or []):
            continue
        new = _guess_sub(cat, f"{r['title'] or ''} {sub}")
        if dry:
            fixed += bool(new)
            cleared += not new
            continue
        db.update(r["id"], subcategory=new or None)
        fixed += bool(new)
        cleared += not new
    if log and (fixed or cleared):
        log(f"子分类整理：收敛 {fixed} 条，清空没把握的 {cleared} 条")
    return {"fixed": fixed, "cleared": cleared}


def _restore(item_id, cat):
    """把一条「主题无关」放回学习库：改分类、生成 MD、状态改成 done。"""
    it = db.get(item_id)
    if not it:
        return False
    n = it.get("note") or {}
    n["category"] = cat
    n["relevant"] = True
    it["note"] = n
    it["category"] = cat
    sub = _guess_sub(cat, f"{it.get('title') or ''} {it.get('subcategory') or ''}") or None
    it["subcategory"] = sub
    try:
        path = notes.write(it)
    except Exception:
        path = it.get("md_path")
    db.update(it["id"], status="done", note=n, category=cat, subcategory=sub,
              reason=None, md_path=path)
    return True


def _irrelevant_ids():
    return [r["id"] for r in db.conn().execute(
        "SELECT id FROM items WHERE status='irrelevant' AND COALESCE(deleted_at,0)=0 ORDER BY id").fetchall()]


def recheck(dry=False, log=None):
    """规则审查（不花钱）。"""
    moved, stayed, by_cat = 0, 0, {}
    for item_id in _irrelevant_ids():
        it = db.get(item_id)
        if not it:
            continue
        n = it.get("note") or {}
        text = " ".join([it.get("title") or "", n.get("title") or "", (n.get("summary") or "")[:120],
                         it.get("subcategory") or ""])
        cat, score = classify.guess(text)
        if cat in KEEP_OUT or score < MIN_SCORE:
            stayed += 1
            continue
        if dry:
            moved += 1
            by_cat[cat] = by_cat.get(cat, 0) + 1
            continue
        if _restore(item_id, cat):
            moved += 1
            by_cat[cat] = by_cat.get(cat, 0) + 1
            if log and moved % 20 == 0:
                log(f"重新审查：已放回 {moved} 条")
    if log and moved:
        log("按规则放回：" + "，".join(f"{k} {v} 条" for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1])))
    return {"moved": moved, "stayed": stayed, "by_cat": by_cat}


AI_SYSTEM = """你在帮用户整理抖音收藏的学习库。用户想学的方向是：{focus}

下面是若干条目（标题 + 笔记摘要）。请逐条判断它属于哪个分类。
分类只能从这些里选：{cats}
不要填「其他」；真的判断不出来就填 null。影视解说、动漫、游戏、情感八卦、明星动态、搞笑段子也填 null。

参考：跑步/健身/减脂/睡眠/作息 → 健身与健康；做菜/食谱/探店 → 美食与烹饪；
PS/修图/调色/布光/拍摄/转场/相机 → 摄影与剪辑；日语/英语/学习方法/认知成长 → 学习与成长；
穿搭/护肤/化妆/发型 → 穿搭与美妆；副业/电商/销售/创业 → 商业与创业；AI 工具/模型/提示词 → 对应的 AI 分类。

只输出 JSON：{{"items":[{{"id":1,"category":"摄影与剪辑"}},{{"id":2,"category":null}}]}}"""


def ai_recheck(settings, log=None, batch=20):
    """剩下的交给 AI 判一次分类（只发标题和摘要，很便宜）。"""
    cats = list(dict.fromkeys([c for c in (settings.get("categories") or []) if c]
                              + list(classify.SUBS)))
    cats = [c for c in cats if c and c != "其他"]
    ids = _irrelevant_ids()
    if not ids or not (settings.get("api_key") or "").strip():
        return {"moved": 0, "by_cat": {}, "skipped": len(ids)}
    moved, by_cat = 0, {}
    for i in range(0, len(ids), batch):
        chunk = ids[i:i + batch]
        lines = []
        for item_id in chunk:
            it = db.get(item_id)
            if not it:
                continue
            n = it.get("note") or {}
            lines.append(f"id={item_id} 标题：{str(it.get('title') or '')[:80]}"
                         f" | 笔记：{str(n.get('title') or '')[:60]}"
                         f" | 摘要：{str(n.get('summary') or '').replace(chr(10), ' ')[:100]}")
        if not lines:
            continue
        msgs = [{"role": "system", "content": AI_SYSTEM.format(
                    focus=settings.get("focus_topic") or "干货", cats="、".join(cats))},
                {"role": "user", "content": "\n".join(lines)}]
        try:
            text, _used = llm.chat(settings, msgs)
            data = llm.parse_json(text) or {}
        except Exception as e:
            if log:
                log(f"AI 复审这一批失败：{str(e)[:80]}")
            continue
        for row in (data.get("items") or []):
            try:
                item_id = int(row.get("id"))
            except Exception:
                continue
            cat = (row.get("category") or "").strip()
            if cat not in cats or cat in KEEP_OUT:
                continue
            if _restore(item_id, cat):
                moved += 1
                by_cat[cat] = by_cat.get(cat, 0) + 1
    if log and moved:
        log("AI 复审放回：" + "，".join(f"{k} {v} 条" for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1])))
    return {"moved": moved, "by_cat": by_cat, "skipped": 0}


def recheck_all(settings, log=None, dry=False):
    a = recheck(dry=dry, log=log)
    b = {"moved": 0, "by_cat": {}, "skipped": a["stayed"]}
    if not dry and a["stayed"]:
        b = ai_recheck(settings, log=log)
    if not dry and (a["moved"] or b["moved"]):
        normalize_subs(log)
    by_cat = dict(a["by_cat"])
    for k, v in (b.get("by_cat") or {}).items():
        by_cat[k] = by_cat.get(k, 0) + v
    return {"moved": a["moved"] + b["moved"], "stayed": a["stayed"] - b["moved"],
            "by_cat": by_cat, "rule": a["moved"], "ai": b["moved"]}
