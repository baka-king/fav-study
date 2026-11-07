"""把一条学习笔记变成一段可以直接粘到 DSH（DeepSeek Harness）里执行的指令。

不需要 AI：完全按笔记里已有的内容拼出来，所以每生成一次都一样，也不会花钱。
"""


def _dur(sec):
    try:
        sec = int(sec or 0)
    except Exception:
        return ""
    if not sec:
        return ""
    m, s = divmod(sec, 60)
    if m >= 60:
        return f"{m // 60} 小时 {m % 60} 分"
    return f"{m} 分 {s} 秒"


def build(item):
    n = item.get("note") or {}
    title = n.get("title") or item.get("title") or "未命名"
    author = item.get("author") or ""
    dur = _dur(item.get("duration"))
    cat = item.get("category") or n.get("category") or ""
    diff = n.get("difficulty") or ""
    url = item.get("url") or ""

    meta = " · ".join(x for x in (author, dur, cat, diff) if x)
    parts = [
        "# 任务：把这条视频里的东西落地",
        "",
        "我用「收藏学习台」整理了一条抖音收藏，下面是笔记。请你（DSH）按笔记内容**直接动手做**，"
        "不要只给建议、不要只列大纲。",
        "",
        "## 这条视频是什么",
        f"标题：{title}",
    ]
    if meta:
        parts.append(f"来源：{meta}")
    if url:
        parts.append(f"链接：{url}")

    summary = (n.get("summary") or "").strip()
    if summary:
        parts += ["", "## 一句话总结", summary]

    points = [p for p in (n.get("points") or []) if str(p).strip()]
    if points:
        parts += ["", "## 核心观点", *[f"- {p}" for p in points]]

    steps = [s for s in (n.get("steps") or []) if str(s).strip()]
    if steps:
        parts += ["", "## 照着做（视频里给的步骤）", *[f"{i}. {s}" for i, s in enumerate(steps, 1)]]

    tools = [t for t in (n.get("tools") or []) if isinstance(t, dict) and t.get("name")]
    if tools:
        parts += ["", "## 提到的工具 / 产品"]
        parts += [f"- {t.get('name')}：{t.get('use', '')}" for t in tools]

    concepts = [c for c in (n.get("concepts") or []) if isinstance(c, dict) and c.get("term")]
    if concepts:
        parts += ["", "## 关键概念"]
        parts += [f"- {c.get('term')}：{c.get('explain', '')}" for c in concepts]

    if item.get("my_note"):
        parts += ["", "## 我自己的笔记", str(item["my_note"]).strip()]

    parts += [
        "",
        "## 我要你做的事",
        "1. 先判断：这条内容能在我这台电脑上变成什么——一个能跑的工具 / 脚本、一份配置、一个最小 demo，"
        "或者一套可执行的操作步骤，四选一，用一句话说明你的判断；",
        "2. 然后直接做：要装依赖就装、要改文件就改、要跑命令就跑，每完成一步告诉我你改了什么、为什么这么改；",
        "3. 做完给我一段「怎么用」的说明，两三句就够；",
        "4. 需要我做决定、或者你卡住了，直接问我，不要自己猜着往下走。",
        "",
        "如果这条内容主要是观点、资讯或方法论，没有能直接落地的操作，就把它整理成一份**可执行清单**："
        "写清楚接下来我要做的 3-5 件事，每件都具体到能马上动手。",
    ]
    return "\n".join(parts).strip() + "\n"
