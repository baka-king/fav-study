"""给收藏自动分类。

两条路：
- 规则分类：只看标题 / 话题标签，不下载视频，500 条也是瞬间完成，完全免费；
- AI 分类：把标题按批（40 条一次）交给模型，套用设置里的分类体系，命不中的再回到规则结果。

分类结果写进 items.category，并在 items.category_src 里记下来源（rule / ai / manual），
这样以后重新分类时可以只覆盖机器分的、不动手动改过的。
"""
import json
import queue
import re
import threading
import time

from . import db, llm

# 生活类分类：抖音收藏里除了 AI，还有一堆做饭、健身、穿搭的干货，
# 只按"AI 分类"分的话它们全都会落到「其他」。
LIFE_CATEGORIES = ["美食与烹饪", "健身与健康", "穿搭与美妆", "摄影与剪辑",
                   "商业与创业", "学习与成长", "生活与娱乐"]

# 分类 → 关键词（小写）。命中话题标签算 3 分，命中标题正文算 2 分。
RULES = [
    ("AI 编程", ["编程", "代码", "开发", "程序员", "codex", "cursor", "claude code", "mcp", "vibecoding",
                 "python", "github", "git", "爬虫", "部署", "服务器", "架构", "api", "前端", "后端",
                 "数据库", "开源项目", "重构", "debug", "终端", "命令行", "ide", "vscode", "skill",
                 "插件市场", "工作台", "自动化脚本"]),
    ("AI 绘画与视频", ["绘画", "生图", "出图", "即梦", "midjourney", "可灵", "sora", "视频生成", "文生图",
                       "aigc", "修图", "设计", "海报", "写真", "换脸", "ai影神图", "comfyui",
                       "stable diffusion", "ai 后期", "ai修图"]),
    ("提示词技巧", ["提示词", "prompt", "咒语", "指令", "话术", "角色扮演", "system prompt"]),
    ("AI 办公效率", ["办公", "excel", "ppt", "word", "表格", "文档", "会议", "待办", "obsidian", "notion",
                     "笔记软件", "自动化", "工作流", "效率工具", "快捷键", "知识库", "整理资料"]),
    ("AI 副业与变现", ["副业", "变现", "赚钱", "接单", "带货", "起号", "流量", "个人ip", "私域", "接广",
                       "商单", "月入", "日入", "数字游民", "一人公司"]),
    ("AI 工具推荐", ["工具", "软件", "app", "插件", "神器", "好用", "推荐", "应用", "小程序", "试用",
                     "上手", "网站", "宝藏", "资源站", "工具清单"]),
    ("大模型与行业资讯", ["大模型", "发布", "融资", "行业", "榜单", "gpt", "gemini", "claude", "deepseek",
                          "agi", "人工智能", "智能体", "agent", "算力", "开源模型", "发布会", "ai",
                          "chatgpt", "openai", "模型", "参数"]),
    ("美食与烹饪", ["美食", "家常菜", "菜谱", "食谱", "做饭", "下厨", "厨房", "烘焙", "探店", "减脂餐",
                    "早餐", "午餐", "晚餐", "火锅", "咖啡", "调料", "蒸饺", "鸡腿", "焖", "炒", "汤",
                    "好吃", "食材", "鱿鱼", "做饭", "私厨", "卤肉", "拌饭", "牛肉", "鸡胸", "排骨",
                    "包菜", "茄子", "外卖", "下饭菜"]),
    ("健身与健康", ["健身", "减脂", "增肌", "体脂", "瘦", "跑步", "游泳", "瑜伽", "训练", "拉伸", "健康",
                    "睡眠", "饮食", "戒糖", "有氧", "力量", "体型", "薄肌", "养生", "驻颜", "腹肌",
                    "皮质醇", "自律餐", "减肥", "中医", "健身餐"]),
    ("穿搭与美妆", ["穿搭", "显瘦", "西装", "化妆", "护肤", "发型", "美妆", "香水", "造型", "通勤",
                    "口红", "粉底", "男装", "女装", "搭配", "ootd", "衬衫", "t恤", "无性别", "潮牌",
                    "变帅", "爆改"]),
    ("摄影与剪辑", ["摄影", "拍照", "布光", "剪辑", "相机", "运镜", "调色", "构图", "后期", "镜头",
                    "口播", "出片", "拍摄", "滤镜", "摄影棚", "白棚", "打光", "灯光", "调色教程",
                    "修图思路", "氛围感"]),
    ("商业与创业", ["创业", "商业", "生意", "电商", "运营", "营销", "品牌", "开店", "管理", "团队",
                    "自媒体", "公司", "客户", "销售", "供应链", "外贸", "财经", "投资", "股票",
                    "基金", "营收", "ipo", "融资", "估值", "老板", "职场", "招聘", "面试"]),
    ("学习与成长", ["学习", "读书", "英语", "考研", "考试", "记忆", "认知", "思维", "复习", "方法论",
                    "自律", "成长", "干货", "历史", "科普", "冷知识", "心理学", "考公", "考编",
                    "书单", "文学", "读完", "知识点", "上课", "课程"]),
    ("生活与娱乐", ["游戏", "电影", "自驾", "旅行", "宠物", "cos", "动漫", "情感", "音乐", "vlog",
                    "同人", "搞笑", "剧情", "好物", "日常", "恋爱", "爱情", "治愈", "内耗", "焦虑",
                    "情绪", "情侣", "女性", "手办", "读书", "好书", "家居", "装修", "独居", "别墅",
                    "酒店", "登山", "雪山", "演唱会", "音乐节", "新番", "解说", "表白", "暗恋"]),
]

# 每个分类下面的子分类。规则分类只分到「分类」，子分类交给 AI 判断（它更懂语境）。
SUBS = {
    "AI 编程": ["工具使用", "开发实战", "开源项目", "Agent 智能体", "部署运维"],
    "AI 绘画与视频": ["AI 绘画", "AI 视频", "AI 修图", "视频生成"],
    "提示词技巧": ["提示词模板", "使用技巧"],
    "AI 办公效率": ["办公软件", "自动化", "文档整理"],
    "AI 副业与变现": ["副业项目", "变现方法", "流量运营"],
    "AI 工具推荐": ["效率工具", "创作工具", "学习工具"],
    "大模型与行业资讯": ["模型发布", "行业动态", "产品更新", "评测对比"],
    "美食与烹饪": ["家常菜", "减脂餐", "健身餐", "烘焙甜品", "探店", "饮品咖啡"],
    "健身与健康": ["减脂", "力量训练", "有氧运动", "健康养生"],
    "穿搭与美妆": ["男装穿搭", "女装穿搭", "美妆护肤", "发型造型"],
    "摄影与剪辑": ["摄影拍摄", "布光", "调色修图", "视频剪辑", "影视制作"],
    "商业与创业": ["创业经验", "电商运营", "营销流量", "职场"],
    "学习与成长": ["学习方法", "认知思维", "考试考证", "阅读读书", "英语语言"],
    "生活与娱乐": ["Vlog 日常", "游戏", "影视解说", "动漫二次元", "情感生活", "户外旅行"],
    "AI 学习方法": ["用 AI 学习", "备考方法"],
    "其他": ["其他"],
}

# 太宽泛的词：单独命中不算数，避免「工具」「学习」把一切吞掉
WEAK = {"ai", "工具", "软件", "应用", "推荐", "学习", "健康", "游戏", "电影", "音乐", "美食",
        "项目", "整理", "干货", "日常", "训练", "搭配", "设计", "发布", "行业"}

_TAG = re.compile(r"#([^#\s]{1,24})")


def _hits(text, kw):
    if not text or not kw:
        return 0
    if kw.isascii():
        return len(re.findall(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", text))
    return text.count(kw)


def guess(title, author=""):
    """纯规则的分类，返回 (分类, 分数)。分数为 0 表示没把握。"""
    text = (title or "").lower()
    tags = " ".join(_TAG.findall(text))
    body = _TAG.sub(" ", text)
    best, best_score = "其他", 0
    for name, kws in RULES:
        score = 0
        for kw in kws:
            w = 1 if kw in WEAK else 2
            score += 3 * w * _hits(tags, kw) + 2 * w * _hits(body, kw)
        if score > best_score:
            best, best_score = name, score
    if best_score < 4:  # 至少要有一次像样的命中，否则老实归到「其他」
        return "其他", best_score
    return best, best_score


def normalize_note_category(cat):
    """笔记里 AI 自拟的分类：不认识的归到「其他」，把原名留作子分类，侧边栏就不会冒出一堆怪分类。"""
    cat = (cat or "").strip() or "其他"
    known = set(SUBS) | {"其他"}
    try:
        from . import config
        known |= {c for c in (config.load().get("categories") or []) if c}
    except Exception:
        pass
    if cat in known:
        return cat, ""
    return "其他", cat[:30]


def items_for_scope(scope="missing", platform=None):
    """missing=只分没分类的；others=只重分「其他」；all=全部重分（跳过笔记已分好的）。"""
    if scope == "others":
        return db.items_to_refine(platform=platform)
    if scope == "all":
        return db.items_for_reclassify(platform=platform)
    if scope == "unsub":
        return db.items_without_sub(platform=platform)
    return db.items_for_classify(only_missing=True, platform=platform)


def rule_classify(items=None, scope="missing", platform=None):
    """给条目按规则分一遍，返回 {id: 分类}。"""
    items = items if items is not None else items_for_scope(scope, platform=platform)
    first, score = {}, {}
    for it in items:
        cat, s = guess(it.get("title"), it.get("author"))
        first[it["id"]] = cat
        score[it["id"]] = s

    # 同一个作者发的内容通常是一个方向：作者有 3 条以上、某一类占六成，
    # 就把这个作者那些「本来没把握」的条目跟着改过去（影视飓风、穿搭店之类的很准）。
    import collections
    by_author = collections.defaultdict(list)
    for it in items:
        a = (it.get("author") or "").strip()
        if a:
            by_author[a].append(it["id"])
    out = dict(first)
    for author, ids in by_author.items():
        if len(ids) < 3:
            continue
        counts = collections.Counter(first[i] for i in ids if first[i] != "其他")
        if not counts:
            continue
        top, n = counts.most_common(1)[0]
        if n / len(ids) >= 0.6:
            for i in ids:
                if score.get(i, 0) < 10:  # 只动没把握的，别把明确命中改掉
                    out[i] = top
    return out


def allowed_categories(settings):
    """AI 可以选的分类：设置里用户自己定的 + 生活类 + 其他。"""
    cats = [c for c in (settings.get("categories") or []) if c]
    for c in LIFE_CATEGORIES + ["其他"]:
        if c not in cats:
            cats.append(c)
    return cats


AI_SYSTEM = """你是一个给短视频收藏归类的助手。用户把抖音收藏里的内容攒成了学习库，
需要你把它们分到合适的分类 + 子分类里。

只能从下面这套两级分类里选，不要自创：
{taxonomy}

规则：
- 只看标题、话题标签（#后面那些）和作者判断，宁愿归到「其他」也不要瞎猜；
- 标题里带 #美食 #健身 #穿搭 #摄影 这类话题标签时，标签比正文更可信；
- 同一个作者基本是同一个方向，可以据此判断；
- 一条内容只给一个分类和一个子分类，子分类必须属于你选的那个分类；
- 严格只输出一个 JSON 对象，键是编号，值是「分类/子分类」，例如 {{"12": "AI 编程/工具使用"}}，不要输出别的文字。"""


def _norm(x):
    return re.sub(r"[\s·\-—_/]+", "", str(x or "")).lower()


def _match_sub(category, sub):
    """AI 写的子分类和我们的名单对不齐时，宽松匹配一下。"""
    subs = SUBS.get(category) or []
    if not sub:
        return ""
    n = _norm(sub)
    for s0 in subs:
        if _norm(s0) == n:
            return s0
    for s0 in subs:
        if n and (n in _norm(s0) or _norm(s0) in n):
            return s0
    return ""


def _ask_batch(settings, system, chunk, cats):
    """问一批，返回 {id: (分类, 子分类)}。"""
    def line(it):
        t = (it.get("title") or "（无标题）").replace("\n", " ")[:90]
        a = (it.get("author") or "").strip()
        return f"[{it['id']}] {t}（作者：{a}）" if a else f"[{it['id']}] {t}"

    msgs = [system, {"role": "user", "content": "给下面这些内容分类：\n" + "\n".join(line(it) for it in chunk)}]
    text, _ = llm.chat(settings, msgs, json_mode=True, temperature=0, max_tokens=4000, timeout=120)
    data = llm.parse_json(text) if text else {}
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        data = data["result"]
    got = {}
    for k, v in (data or {}).items():
        try:
            item_id = int(str(k).strip("[]# "))
        except ValueError:
            continue
        if isinstance(v, dict):
            c = str(v.get("category") or v.get("分类") or "").strip()
            sub = str(v.get("subcategory") or v.get("sub") or v.get("子分类") or "").strip()
        else:
            raw = str(v).strip().replace("｜", "|")
            for sep in ("/", "|", "·", ">"):
                if sep in raw:
                    c, sub = [x.strip() for x in raw.split(sep, 1)]
                    break
            else:
                c, sub = raw, ""
        if c in cats:
            got[item_id] = (c, _match_sub(c, sub))
    return got


def ai_classify(settings, items, log=lambda m: None, batch=25, on_progress=None):
    """用 AI 按批分类，返回 {id: (分类, 子分类)}；失败的批次返回空，由调用方回落到规则。"""
    cats = allowed_categories(settings)
    out = {}
    total = len(items)
    tax = "\n".join(f"- {c}：" + " / ".join(SUBS.get(c) or ["其他"]) for c in cats)
    system = {"role": "system", "content": AI_SYSTEM.format(taxonomy=tax)}
    for start in range(0, total, batch):
        chunk = items[start:start + batch]
        got = {}
        for attempt in (1, 2):
            try:
                got = _ask_batch(settings, system, chunk, cats)
                if got:
                    break
                log(f"⚠ AI 这一批没返回结果（第 {attempt} 次），重试")
            except Exception as e:
                log(f"⚠ AI 分类这一批失败了（{str(e)[:80]}）")
                got = {}
        if not got:
            log("⚠ 这一批改用关键词规则兜底")
        out.update(got)
        if on_progress:
            on_progress(min(start + batch, total), total)
    return out


class Runner:
    """AI 分类在单独线程里跑：不占用下载/转文字的队列，也不会被同步卡住。"""

    def __init__(self):
        self.q = queue.Queue()
        self.state = {"busy": False, "mode": "", "scope": "", "done": 0, "total": 0, "stage": "",
                      "error": "", "finished_at": 0}
        self.thread = threading.Thread(target=self._run, daemon=True, name="classify")
        self.thread.start()

    def submit(self, mode="ai", scope="missing", platform=None):
        self.q.put((mode, scope, platform))

    def snapshot(self):
        return dict(self.state)

    def _run(self):
        while True:
            mode, scope, platform = self.q.get()
            try:
                self._do(mode, scope, platform)
            except Exception as e:
                self.state.update(busy=False, error=str(e)[:200], finished_at=time.time())

    def _do(self, mode, scope, platform=None):
        items = items_for_scope(scope, platform=platform)
        total = len(items)
        if not total:
            self.state.update(busy=False, mode=mode, scope=scope, done=0, total=0,
                              stage="没有需要分类的条目", error="", finished_at=time.time())
            return
        self.state.update(busy=True, mode=mode, scope=scope, done=0, total=total,
                          stage="准备中", error="")
        mapping = {}
        if mode == "ai":
            from . import config
            settings = config.load()

            def prog(done, tot):
                self.state.update(done=done, total=tot, stage="AI 判断中")

            mapping = ai_classify(settings, items, log=lambda m: None, on_progress=prog)
        rule_map = rule_classify(items)
        for it in items:  # AI 没给结果的，用规则兜底（子分类留空）
            if it["id"] not in mapping:
                mapping[it["id"]] = (rule_map[it["id"]], "")
        db.set_categories(mapping, src="ai" if mode == "ai" else "rule")
        self.state.update(busy=False, done=total, total=total, stage=f"分类完成：{total} 条",
                          error="", finished_at=time.time())
