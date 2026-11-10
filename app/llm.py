"""AI 提炼：调用 OpenAI 兼容的 /chat/completions 接口，把文字稿变成结构化学习笔记。

只把文字稿发给你选的 AI 服务商；视频、音频、你的个人笔记都不会上传。
"""
import json
import re
import time
import urllib.error
import urllib.request

MAX_CHARS = 6000  # 文字稿太长就截断，控制花费

SYSTEM = """你是一位擅长把短视频内容整理成学习笔记的助手。你会收到一条抖音视频的语音转文字稿，或者一条抖音图文笔记的正文和图片里识别出的文字（都可能有错别字或断行，请按上下文理解），需要提炼成结构化笔记。

用户关注的主题：{focus}

用户的知识库按这些分类整理，category 必须从这里选一个，不要自拟新分类；实在都不合适才填「其他」：
{categories}

关于 relevant（有没有用）：
- 只要内容落在上面这些分类里（尤其是摄影与剪辑、美食与烹饪、健身与健康、穿搭与美妆、学习与成长、AI 相关、商业与创业），就算相关，relevant 填 true。
- 只有纯娱乐消遣才填 false：影视解说、动漫、游戏、搞笑段子、情感八卦、明星动态、纯音乐/跳舞。

请严格只输出一个 JSON 对象，不要输出任何其他文字，格式如下：
{{
  "skip": false,
  "skip_reason": "",
  "relevant": true,
  "title": "一句话说清这条视频讲了什么（20字以内，不要照抄原标题里的话题标签）",
  "category": "必须是上面分类列表里的一个，原样抄，不要自拟",
  "tags": ["3-5个关键词"],
  "difficulty": "入门 / 进阶 / 高级 选一个",
  "summary": "3-5 句话的详细总结",
  "points": ["核心观点或知识点，每条一句话，3-8 条"],
  "steps": ["如果视频教了可以照着做的方法，按顺序写出具体步骤；没有就给空数组"],
  "tools": [{{"name": "视频提到的工具/网站/产品名", "use": "它是干什么用的"}}],
  "concepts": [{{"term": "关键概念", "explain": "用大白话解释"}}],
  "quiz": [{{"q": "根据视频内容出的一道自测题", "a": "答案"}}]
}}

规则：
- **永远不要 skip**：哪怕只是广告、短剧、闲聊、纯音乐，也要照实写出一条笔记（标题、summary、1-3 条 points），
  并在 summary 第一句说明「这条没有可学习的内容」。只有实在没有任何文字可读时，skip 才为 true。
- 分类**必须从下面的分类列表里原样选**：判断的是内容本身是什么（美食就是美食与烹饪，健身就是健身与健康），
  不要按「和 AI 主题是否相关」来选；哪个都不合适就填「无法分类」，不要硬塞。
- 不要编造视频里没有的信息；转写里明显听错的专有名词（比如工具名）可以按常识纠正。
- 全部使用简体中文。quiz 出 1-3 题。"""

USER = """标题：{title}
作者：{author}
{label}：
{transcript}

请提炼成学习笔记。"""


class LLMError(Exception):
    def __init__(self, msg, retry=False):
        super().__init__(msg)
        self.retry = retry


def _post(url, headers, payload, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _as_cfg(c):
    """兼容传整份设置或已经整理好的模型配置。"""
    if "kind" in c:
        return c
    from .config import llm_cfg
    return llm_cfg(c, "main")


_QUIRKS = {}  # (接口地址, 模型) → 这个模型需要的参数调整，记住后下次直接用


def _apply_quirks(payload, key):
    q = _QUIRKS.get(key, set())
    if "mct" in q and "max_tokens" in payload:
        # 推理模型的输出上限也包含"思考"用的 token，给宽一点
        payload["max_completion_tokens"] = max(payload.pop("max_tokens") * 2, 4000)
    if "no_temp" in q:
        payload.pop("temperature", None)


def chat(cfg, messages, json_mode=True, temperature=0.3, max_tokens=None, timeout=120, retry_429=True):
    """带备用模型的入口：主模型超时/连不上/5xx 时自动切到配置里的备用模型。"""
    cfg = _as_cfg(cfg)
    fb = cfg.get("fallback") if isinstance(cfg, dict) else None
    try:
        return _chat_one(cfg, messages, json_mode=json_mode, temperature=temperature,
                         max_tokens=max_tokens, timeout=timeout, retry_429=retry_429)
    except LLMError as e:
        msg = str(e)
        # 超时 / 连不上 / 5xx / 限速 / 主模型那家没余额 → 都值得试一次备用
        worth = getattr(e, "retry", False) or "余额不足" in msg or "429" in msg or "限速" in msg
        if not fb or not worth:
            raise
        print(f"[AI] 主模型 {cfg.get('model')} 失败（{str(e)[:60]}），改用备用 {fb.get('model')}", flush=True)
        return _chat_one(fb, messages, json_mode=json_mode, temperature=temperature,
                         max_tokens=max_tokens, timeout=timeout, retry_429=retry_429)


def _chat_one(cfg, messages, json_mode=True, temperature=0.3, max_tokens=None, timeout=120, retry_429=True):
    """返回 (文本, 消耗的 token 数)。带重试：网络/5xx 重试 2 次，429/529 限速等 5 秒。

    cfg 可以是整份设置，也可以是 config.llm_cfg() 的结果。
    """
    cfg = _as_cfg(cfg)
    key = (cfg.get("api_key") or "").strip()
    base = (cfg.get("base_url") or "").strip().rstrip("/")
    model = (cfg.get("model") or "").strip()
    if not key:
        raise LLMError("还没填 AI 的 API Key")
    if not base or not model:
        raise LLMError("请在设置里填好接口地址和模型名")

    if cfg.get("kind") == "anthropic":
        # Claude 原生接口：system 单独传；没有 JSON 模式，靠提示词约束 + parse_json 兜底
        if base.endswith("/v1"):
            base = base[:-3]
        url = base + "/v1/messages"
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        msgs = [m for m in messages if m["role"] != "system"]
        payload = {"model": model, "max_tokens": max_tokens or 4096, "messages": msgs, "temperature": temperature}
        if system:
            payload["system"] = system
    else:
        url = base + "/chat/completions"
        headers = {"Authorization": f"Bearer {key}"}
        payload = {"model": model, "messages": messages, "temperature": temperature, "stream": False}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        _apply_quirks(payload, (base, model))

    attempt = 0
    while True:
        attempt += 1
        try:
            data = _post(url, headers, payload, timeout=timeout)
            if cfg.get("kind") == "anthropic":
                text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
                u = data.get("usage") or {}
                used = (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0)
                if data.get("stop_reason") == "max_tokens" and json_mode:
                    raise LLMError("AI 输出太长被截断了，可以在设置里把精读分段字数调小再试")
            else:
                text = data["choices"][0]["message"]["content"] or ""
                used = (data.get("usage") or {}).get("total_tokens", 0)
            return text, used
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "ignore")[:300]
            except Exception:
                pass
            if e.code == 401:
                raise LLMError("API Key 无效（401），请到设置里检查")
            if e.code in (402, 403):
                raise LLMError(f"账户余额不足或没有权限（{e.code}），请到服务商后台检查：{body}")
            if e.code == 404:
                raise LLMError(f"接口地址或模型名不对（404）：{body}")
            low = body.lower()
            qk = (base, model)
            # OpenAI 新一代（推理）模型：max_tokens 改名 max_completion_tokens
            if e.code == 400 and "max_completion_tokens" in low and "max_tokens" in payload:
                _QUIRKS.setdefault(qk, set()).add("mct")
                _apply_quirks(payload, qk)
                continue
            # 有的模型只允许默认 temperature
            if e.code == 400 and "temperature" in low and "temperature" in payload:
                _QUIRKS.setdefault(qk, set()).add("no_temp")
                payload.pop("temperature", None)
                continue
            if e.code == 400 and (payload.get("max_tokens") or 0) > 4096 and "token" in low:
                payload["max_tokens"] = 4096  # 免费模型通常限制单次最多输出 4096 tokens
                continue
            if e.code == 400 and "response_format" in payload:
                payload.pop("response_format")  # 有的模型不支持 JSON 模式，去掉再试
                continue
            if e.code in (429, 529) and attempt <= 3 and retry_429:
                time.sleep(5 * attempt)
                continue
            if e.code >= 500 and attempt <= 2:
                time.sleep(2)
                continue
            if e.code == 429:
                raise LLMError("请求太频繁或免费额度用完了（429）。免费额度一般按天/按月恢复；"
                               "着急的话可以在设置里换成付费模型。", retry=True)
            raise LLMError(f"AI 接口报错（HTTP {e.code}）：{body}", retry=e.code >= 500)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt <= 2:
                time.sleep(2)
                continue
            raise LLMError(f"连不上 AI 接口：{getattr(e, 'reason', e)}", retry=True)
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError(f"AI 接口返回的格式看不懂：{e}")


def parse_json(text: str) -> dict:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except Exception:
        a, b = t.find("{"), t.rfind("}")
        if a >= 0 and b > a:
            return json.loads(t[a:b + 1])
        raise


def _str_list(v):
    if isinstance(v, str):
        v = [v]
    return [str(x).strip() for x in (v or []) if str(x).strip()]


def _obj_list(v, keys):
    out = []
    for x in v or []:
        if isinstance(x, dict):
            d = {k: str(x.get(k, "")).strip() for k in keys}
            if d[keys[0]]:
                out.append(d)
        elif isinstance(x, str) and x.strip():
            out.append({keys[0]: x.strip(), keys[1]: ""})
    return out


CATEGORY_GUIDE = {
    "AI 编程": "写代码、框架库用法、部署调试、Git、接口对接、开源项目实现；不收「只介绍工具怎么装」",
    "AI 工具推荐": "介绍具体 AI 工具/插件/客户端/网站：是什么、怎么装、有什么效果；不收「讲原理实现」",
    "提示词技巧": "提示词写法、角色设定、模板、系统提示词调教；不收「展示 AI 作品」",
    "AI 办公效率": "用 AI 处理文档表格 PPT 邮件、自动化流程、时间管理；不收「纯编程实现」",
    "AI 副业与变现": "用 AI 赚钱的具体方法：接单、带货、做号、报价、获客；不收「只喊口号」",
    "AI 绘画与视频": "绘画/视频生成工具与提示词、AIGC 作品与创作流程、AI 剪辑；不收「真人拍摄后期」",
    "大模型与行业资讯": "模型发布与对比、评测、公司动态、行业趋势、榜单；不收「怎么用某个工具」",
    "AI 学习方法": "怎么学会用 AI 的路径、课程体系、学习法；不收「通用考试学习」",
    "摄影与剪辑": "拍摄构图布光、修图调色、剪辑、器材；不收「AI 生成图像」",
    "美食与烹饪": "菜谱做法、食材处理、探店、厨具、减脂餐做法；不收「只拍吃播不教做法」",
    "健身与健康": "训练动作与计划、减脂增肌、康复体态、睡眠健康；不收「只记录打卡」",
    "穿搭与美妆": "穿搭、妆容、护肤、发型、彩妆测评；不收「cosplay 装扮展示」",
    "学习与成长": "通用学习方法、考试考证、职场成长、思维方式、英语学习；不收「AI 工具学习」",
    "商业与创业": "生意运营、商业模式、团队管理、行业观察、非 AI 的赚钱路径；不收「用 AI 变现」",
    "生活与娱乐": "日常记录、影视动漫游戏、搞笑、旅游、宠物、cosplay 展示；不收「有明确方法论的内容」",
    "无法分类": "确实不属于以上任何一类，或标题/内容抓取失败、没有可判断信息",
}


def classify_category(text: str, cats) -> str:
    """把一段内容归进给定分类；只有真的一类都不沾边才「无法分类」。"""
    from . import config
    cats = [c for c in (cats or []) if c] or ["无法分类"]
    if not (text or "").strip():
        return None
    guide = "\n".join(f"- {c}：{CATEGORY_GUIDE.get(c, '见分类名')}" for c in cats)
    sys_p = ("你是内容分类器。先看内容讲的是什么，再从下面的分类里选出**最贴近的一个**：\n" + guide +
             "\n\n规则：\n"
             "1. 按内容本身所属的领域选（美食就美食、健身就健身、AI 工具就 AI 工具推荐）；\n"
             "2. **尽量别用「无法分类」**：只要有一类沾边就选它，拿不准就选最接近的；\n"
             "3. 分类名必须从上面原样抄，不许自拟。\n"
             '只输出一个 JSON：{"category":"分类名"}')
    cfg = config.llm_cfg(config.load(), "main")
    raw, _ = chat(cfg, [{"role": "system", "content": sys_p},
                        {"role": "user", "content": text[:900]}],
                  json_mode=True, temperature=0, max_tokens=900, timeout=60, retry_429=False)
    if not (raw or "").strip():
        return None                       # 请求失败/为空：保持原分类，别乱动
    try:
        d = parse_json(raw)
    except Exception:
        return None
    cat = str((d or {}).get("category") or "").strip()
    if not cat:
        return None
    return cat if cat in cats else "无法分类"


def normalize(d: dict) -> dict:
    """统一字段格式，校验不过就抛错。"""
    if d.get("skip") is True:
        return {"skip": True, "skip_reason": str(d.get("skip_reason") or "没有实质内容")}
    note = {
        "skip": False,
        "relevant": d.get("relevant") is not False,
        "title": str(d.get("title") or "").strip(),
        "category": str(d.get("category") or "其他").strip() or "其他",
        "tags": _str_list(d.get("tags"))[:6],
        "difficulty": str(d.get("difficulty") or "").strip(),
        "summary": str(d.get("summary") or "").strip(),
        "points": _str_list(d.get("points")),
        "steps": _str_list(d.get("steps")),
        "tools": _obj_list(d.get("tools"), ["name", "use"]),
        "concepts": _obj_list(d.get("concepts"), ["term", "explain"]),
        "quiz": _obj_list(d.get("quiz"), ["q", "a"]),
    }
    if not note["points"]:
        raise LLMError("AI 返回的核心观点为空")
    if not note["title"]:
        note["title"] = note["points"][0][:30]
    return note


def extract(settings, title, author, transcript, kind="video"):
    """返回 (笔记 dict, token 数)。"""
    _cats = [c for c in (settings.get("categories") or []) if c]
    cats = chr(10).join(f"- {c}：{CATEGORY_GUIDE.get(c, '见分类名')}" for c in _cats)
    messages = [
        {"role": "system", "content": SYSTEM.format(focus=settings.get("focus_topic") or "不限", categories=cats)},
        {"role": "user", "content": USER.format(
            title=title or "（无）", author=author or "（未知）",
            label="图文笔记的正文和图片文字（【图N】是第 N 张图里识别出的文字）" if kind == "note" else "语音转文字稿",
            transcript=(transcript or "")[:MAX_CHARS])},
    ]
    text, used = chat(settings, messages)
    try:
        d = parse_json(text)
    except Exception:
        raise LLMError("AI 返回的不是有效的 JSON：" + (text or "")[:200])
    note = normalize(d)
    if not note.get("skip"):
        # AI 有时把「AI 编程」写成「AI编程」，同一个分类就被拆成两个；对上设置里的分类名
        same = {re.sub(r"\s+", "", c): c for c in settings.get("categories") or []}
        note["category"] = same.get(re.sub(r"\s+", "", note["category"]), note["category"])
    return note, used


CHAT_HINT = ("gpt", "o1", "o3", "o4", "chatgpt", "claude", "deepseek", "qwen", "glm", "moonshot", "kimi",
             "yi-", "llama", "mistral", "gemini", "doubao", "ernie", "hunyuan", "minimax", "abab", "step")
SKIP_HINT = ("embed", "whisper", "tts", "dall-e", "image", "audio", "realtime", "moderation", "transcribe",
             "search", "rerank", "vision-preview", "babbage", "davinci", "sora", "speech")


def list_models(cfg):
    """向服务商要可用模型列表，返回模型 ID 列表（尽量只留聊天模型）。"""
    cfg = _as_cfg(cfg)
    key = (cfg.get("api_key") or "").strip()
    base = (cfg.get("base_url") or "").strip().rstrip("/")
    if not key or not base:
        raise LLMError("先填好接口地址和 API Key")
    if cfg.get("kind") == "anthropic":
        if base.endswith("/v1"):
            base = base[:-3]
        url, headers = base + "/v1/models?limit=100", {"x-api-key": key, "anthropic-version": "2023-06-01"}
    else:
        url, headers = base + "/models", {"Authorization": f"Bearer {key}"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LLMError(f"这个服务商不支持读取模型列表（HTTP {e.code}），请手动填写模型名")
    except Exception as e:
        raise LLMError(f"读取模型列表失败：{e}")
    ids = [str(m.get("id")) for m in (data.get("data") or data.get("models") or []) if isinstance(m, dict) and m.get("id")]
    chat_ids = [i for i in ids if not any(h in i.lower() for h in SKIP_HINT)]
    pref = [i for i in chat_ids if any(h in i.lower() for h in CHAT_HINT)]
    out = pref or chat_ids or ids
    return sorted(set(out), key=lambda x: (x.count("-") > 4, x))


def test(cfg, retry_429=True):
    text, _ = chat(cfg, [{"role": "user", "content": "请只回复两个字：你好"}], json_mode=False, temperature=0,
                   max_tokens=300, retry_429=retry_429)
    return text.strip()[:50] or "（连接正常）"


def free_setup(plan, api_key, log=lambda m: None):
    """免费方案一键配置：读模型列表 → 挑免费模型 → 逐个测试，返回 (能用的模型, 试过的列表)。"""
    from .config import FREE_PLANS
    p = FREE_PLANS[plan]
    cfg = {"provider": p["provider"], "base_url": p["base_url"], "api_key": api_key.strip(), "kind": "openai"}
    listed = []
    try:
        listed = [m.split("/", 1)[1] if m.startswith("models/") else m for m in list_models(cfg)]
    except LLMError:
        pass
    cands = [m for m in p["models"] if not listed or m in listed]
    if listed and p.get("pick"):
        extra = [m for m in listed if all(k in m.lower() for k in p["pick"])
                 and not any(a in m.lower() for a in p["avoid"]) and m not in cands]
        extra.sort(reverse=True)  # 版本号大的通常更新
        cands += extra
    if not cands:
        cands = list(p["models"])
    tried = []
    for m in cands[:5]:
        cfg["model"] = m
        try:
            test(cfg, retry_429=False)
            return m, tried
        except LLMError as e:
            msg = str(e)
            tried.append(f"{m}：{msg[:80]}")
            if "401" in msg or "无效" in msg:
                raise LLMError("这个 Key 无效，请检查有没有复制完整（前后不要有空格）")
            if "429" in msg:
                raise LLMError("Key 是有效的，但现在请求太频繁或免费额度用完了（429）。过一会儿再点一键配置试试。")
    raise LLMError("没有找到能用的免费模型：" + "；".join(tried[:3]))
