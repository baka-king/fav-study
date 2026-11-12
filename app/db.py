import collections
import re
"""SQLite 条目库。每条视频一行，记录处理状态、文字稿、AI 笔记和学习进度。"""
import json
import sqlite3
import threading
import time

from .config import DB_PATH

# 状态：
#   queued       等待处理
#   fetching     读取视频信息
#   downloading  下载中
#   transcribing 转文字中
#   extracting   AI 提炼中
#   done         完成，可以学习
#   need_key     已转成文字，但没配 AI Key，等配好后再提炼
#   irrelevant   和关注主题无关（自动收起，不算失败）
#   skipped      广告 / 图文 / 纯音乐 / 无对白，自动跳过
#   failed       失败，可以重试
ACTIVE = ("fetching", "downloading", "transcribing", "extracting", "retry_wait")

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL DEFAULT 'link',      -- link / favorite / local
  aweme_id TEXT UNIQUE,
  url TEXT,
  local_path TEXT,
  title TEXT,
  author TEXT,
  duration REAL,
  cover TEXT,
  status TEXT NOT NULL DEFAULT 'queued',
  reason TEXT,
  attempts INTEGER NOT NULL DEFAULT 0,
  transcript TEXT,
  note_json TEXT,
  category TEXT,
  md_path TEXT,
  learned INTEGER NOT NULL DEFAULT 0,
  starred INTEGER NOT NULL DEFAULT 0,
  my_note TEXT NOT NULL DEFAULT '',
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  learned_at REAL
);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_live ON items(deleted_at, status);
CREATE INDEX IF NOT EXISTS idx_items_platform ON items(platform);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_items_aweme ON items(aweme_id);
CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at);
-- 共识观点：每个分类一份，AI 从这个分类的多条笔记里找出互相印证 / 有分歧的观点
CREATE TABLE IF NOT EXISTS insights (
  category TEXT PRIMARY KEY,
  data_json TEXT NOT NULL,
  item_ids TEXT NOT NULL,     -- 整理时用到的笔记 id（逗号分隔），用来判断有没有新笔记
  model TEXT,
  md_path TEXT,
  created_at REAL NOT NULL
);
"""

_local = threading.local()
_write_lock = threading.Lock()


def conn():
    c = getattr(_local, "conn", None)
    if c is None:
        c = sqlite3.connect(DB_PATH, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        _local.conn = c
    return c


EXTRA_COLUMNS = {
    "segments_json": "TEXT",   # 带时间戳的文字稿分段
    "deep_json": "TEXT",       # 精读结果
    "chat_json": "TEXT",       # 精读里的答题点评、问老师记录
    "media_type": "TEXT",      # video / note（图文）
    "images_json": "TEXT",     # 图文的图片（相对于笔记目录的路径列表）
    "category_src": "TEXT",    # 分类来源：rule（关键词）/ ai（模型）/ manual（手改）
    "subcategory": "TEXT",     # 子分类（AI 判断，比如「健身与健康」下面的「减脂」「健身餐」）
    "auto_skip": "INTEGER",    # 1=按分类自动跳过；2=用户手动要求处理（不再自动跳过）
    "deleted_at": "REAL",      # 扔进回收站的时间；NULL = 正常
    "published_at": "REAL",    # 作品发布时间（抖音 create_time）
    "collected_at": "REAL",    # 收藏时间（抖音收藏列表里带的话就存，没带就是空）
    "platform": "TEXT",
    "play_url": "TEXT",
    "play_url_ts": "REAL",        # douyin / xhs（小红书）；空 = 抖音老数据
    "bili_desc": "TEXT",        # B 站视频简介（没字幕时给 AI 的补充材料）
    "queue_prio": "REAL",         # 插队：数值越大越先处理（手动添加/点插队时置为当前时间）
    "done_at": "REAL",            # 处理完成的时间（用来按先后顺序看刚做完的）
}

# 时长筛选：≤1 分钟 / 1-5 分钟 / 5-15 分钟 / 15 分钟以上
DUR_RANGES = {"s": (0, 60), "m": (60, 300), "l": (300, 900), "xl": (900, None)}


def init():
    with _write_lock:
        conn().executescript(SCHEMA)
        have = {r["name"] for r in conn().execute("PRAGMA table_info(items)")}
        for col, typ in EXTRA_COLUMNS.items():
            if col not in have:  # 老版本的数据库自动升级
                conn().execute(f"ALTER TABLE items ADD COLUMN {col} {typ}")
        # 程序上次被强制关掉时，卡在中间状态的条目放回队列
        conn().execute(
            f"UPDATE items SET status='queued' WHERE status IN ({','.join('?' * len(ACTIVE))})", ACTIVE)
        conn().commit()
        # WAL 会一直长（实测 4 MB 日志 / 512 KB 主库），启动时收一下，读写也快些
        try:
            conn().execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass


JSON_FIELDS = {"note": "note_json", "segments": "segments_json", "deep": "deep_json", "chat": "chat_json",
               "images": "images_json"}


def _row(r):
    if r is None:
        return None
    d = dict(r)
    for name, col in JSON_FIELDS.items():
        if col in d:
            d[name] = json.loads(d.pop(col) or "null")
    return d


def add(source, *, aweme_id=None, url=None, local_path=None, title=None, author=None,
        duration=None, cover=None, published_at=None, collected_at=None, platform=None,
        jump=False):
    """新增一条；同一个视频（aweme_id 相同）不会重复添加。返回 (id, 是否新增)。"""
    now = time.time()
    with _write_lock:
        c = conn()
        if aweme_id:
            r = c.execute("SELECT id, deleted_at FROM items WHERE aweme_id=?", (aweme_id,)).fetchone()
            if r:
                if r["deleted_at"]:
                    c.execute("UPDATE items SET deleted_at=NULL WHERE id=?", (r["id"],))
                    c.commit()
                return r["id"], False
        if local_path:
            r = c.execute("SELECT id, deleted_at FROM items WHERE local_path=?", (local_path,)).fetchone()
            if r:
                if r["deleted_at"]:
                    c.execute("UPDATE items SET deleted_at=NULL WHERE id=?", (r["id"],))
                    c.commit()
                return r["id"], False
        # 手动添加的（粘贴链接 / 本地文件 / 手动导入）自动插队：用户刚发进来的要先处理；
        # 自动同步收藏夹进来的不插队，否则一次同步会把整条队列顶翻
        prio = now if jump else None
        cur = c.execute(
            "INSERT INTO items(source,aweme_id,url,local_path,title,author,duration,cover,status,"
            "published_at,collected_at,created_at,updated_at,platform,queue_prio)"
            " VALUES(?,?,?,?,?,?,?,?,'queued',?,?,?,?,?,?)",
            (source, aweme_id, url, local_path, title, author, duration, cover,
             published_at, collected_at, now, now, platform or "douyin", prio))
        c.commit()
        return cur.lastrowid, True


def update(item_id, **fields):
    if not fields:
        return
    for name, col in JSON_FIELDS.items():
        if name in fields:
            v = fields.pop(name)
            fields[col] = json.dumps(v, ensure_ascii=False) if v is not None else None
    if fields.get("status") == "done" and not fields.get("done_at"):
        fields.setdefault("done_at", time.time())
    fields["updated_at"] = time.time()
    keys = list(fields)
    with _write_lock:
        conn().execute(f"UPDATE items SET {','.join(k + '=?' for k in keys)} WHERE id=?",
                       [fields[k] for k in keys] + [item_id])
        conn().commit()


def get(item_id):
    return _row(conn().execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone())


def trash(item_id):
    """删到回收站（还能恢复）。"""
    now = time.time()
    with _write_lock:
        conn().execute("UPDATE items SET deleted_at=?, updated_at=? WHERE id=?", (now, now, item_id))
        conn().commit()


def restore(item_id):
    now = time.time()
    with _write_lock:
        conn().execute("UPDATE items SET deleted_at=NULL, updated_at=? WHERE id=?", (now, item_id))
        conn().commit()


def trash_items(limit=5000):
    rows = conn().execute(
        "SELECT id,title,author,cover,status,duration,media_type,deleted_at,category "
        "FROM items WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def trash_count():
    return conn().execute("SELECT COUNT(*) FROM items WHERE deleted_at IS NOT NULL").fetchone()[0]


def empty_trash():
    with _write_lock:
        cur = conn().execute("DELETE FROM items WHERE deleted_at IS NOT NULL")
        conn().commit()
        return cur.rowcount


def delete(item_id):
    with _write_lock:
        conn().execute("DELETE FROM items WHERE id=?", (item_id,))
        conn().commit()


# 处理优先级：AI / 技能 / 学习 先做，美食健身等等往后排
PRIORITY_SQL = (
    "CASE "
    " WHEN category LIKE 'AI%' OR category IN ('大模型与行业资讯','提示词技巧') THEN 0 "
    " WHEN category IN ('学习与成长') THEN 1 "
    " WHEN category IN ('摄影与剪辑','商业与创业','穿搭与美妆') THEN 2 "
    " WHEN category IN ('美食与烹饪','健身与健康') THEN 3 "
    " ELSE 4 END, "
)

# 这些分类不拆解（生活记录、纯娱乐）
SKIP_CATS = ("生活与娱乐",)


def jump(item_id):
    """手动插队：把这条排到队首。"""
    with _write_lock:
        conn().execute("UPDATE items SET queue_prio=?, updated_at=? WHERE id=?",
                       (time.time(), time.time(), item_id))
        conn().commit()


def today_summary():
    """今天拆了多少条、进了哪些分类（给「今日汇总」卡片用）。"""
    import datetime
    t0 = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    c = conn()
    added = c.execute("SELECT COUNT(*) FROM items WHERE created_at>=? AND COALESCE(deleted_at,0)=0",
                      (t0,)).fetchone()[0]
    done = c.execute("SELECT COUNT(*) FROM items WHERE status='done' AND COALESCE(done_at,0)>=?",
                     (t0,)).fetchone()[0]
    skipped = c.execute("SELECT COUNT(*) FROM items WHERE status IN ('skipped','irrelevant')"
                        " AND updated_at>=? AND COALESCE(deleted_at,0)=0", (t0,)).fetchone()[0]
    rows = c.execute("SELECT category, COUNT(*) n FROM items WHERE status='done' AND COALESCE(done_at,0)>=?"
                     " GROUP BY category ORDER BY n DESC LIMIT 6", (t0,)).fetchall()
    return {"added": added, "done": done, "skipped": skipped,
            "cats": [{"cat": r["category"] or "未分类", "n": r["n"]} for r in rows]}


def count_remote_covers():
    """还有多少条封面挂在远端（图床签名过期后会拉不到）。"""
    return conn().execute(
        "SELECT COUNT(*) FROM items WHERE cover LIKE 'http%' AND COALESCE(deleted_at,0)=0").fetchone()[0]


def next_queued():
    from . import config
    s = config.load()
    sql = ("SELECT * FROM items WHERE status='queued' AND COALESCE(deleted_at,0)=0 ")
    # 小红书被临时关掉时，队列里跳过它的条目，别的平台照常跑
    if not s.get("xhs_enabled", True):
        sql += "AND COALESCE(platform,'')<>'xhs' "
    sql += f"ORDER BY COALESCE(queue_prio,0) DESC, {PRIORITY_SQL} id LIMIT 1"
    return _row(conn().execute(sql).fetchone())


def skip_by_category(cats=SKIP_CATS, reason="生活/娱乐类内容，不拆解"):
    """把不需要拆解的分类直接标成已跳过；用户手动点过「还是处理这条」的不会再跳。"""
    if not cats:
        return 0
    with _write_lock:
        q = ",".join("?" * len(cats))
        cur = conn().execute(
            f"UPDATE items SET status='skipped', reason=?, auto_skip=1, updated_at=? "
            f"WHERE status='queued' AND COALESCE(deleted_at,0)=0 AND COALESCE(auto_skip,0)=0 AND category IN ({q})",
            (reason, time.time(), *cats))
        conn().commit()
        return cur.rowcount


def list_items(status=None, category=None, sub=None, q=None, learned=None, starred=None,
               dur=None, sort="new", limit=1000, stage=None, platform=None, since=None,
               scope=None):
    # 列表页只要摘要，不要把整份 note_json 都塞进响应里（笔记多了会到好几 MB）
    sql = ("SELECT id,source,aweme_id,url,title,author,duration,cover,status,reason,category,"
           "category_src,subcategory,learned,starred,created_at,updated_at,published_at,collected_at,media_type,platform,url,"
           "(deep_json IS NOT NULL) AS has_deep,"
           "json_extract(note_json,'$.summary') AS summary,"
           "json_extract(note_json,'$.title') AS note_title,"
           "queue_prio,done_at,"
           "json_extract(note_json,'$.difficulty') AS difficulty FROM items "
           "WHERE COALESCE(deleted_at,0)=0")   # 回收站里的不进任何列表
    args = []
    if status and status != "all":
        statuses = status.split(",")
        sql += f" AND status IN ({','.join('?' * len(statuses))})"
        args += statuses
    if platform:
        if platform == "douyin":   # 老数据 platform 是空的
            sql += " AND COALESCE(NULLIF(platform,''),'douyin')='douyin'"
        else:
            sql += " AND platform=?"
            args.append(platform)
    if stage == "done":     # 已拆解：出了笔记的
        sql += " AND status='done'"
    elif stage == "todo":   # 未拆解：还在排队 / 跳过 / 失败的
        sql += " AND status<>'done'"
    if category:
        sql += " AND category=?"
        args.append(category)
    if sub:
        sql += " AND subcategory=?"
        args.append(sub)
    if learned is not None:
        sql += " AND learned=?"
        args.append(1 if learned else 0)
    if starred:
        sql += " AND starred=1"
    if dur in DUR_RANGES:
        lo, hi = DUR_RANGES[dur]
        sql += " AND duration > ?"
        args.append(max(lo, 0))
        if hi is not None:
            sql += " AND duration <= ?"
            args.append(hi)
    if since:
        # 按「什么时候进到库里」筛：抖音收藏列表不带收藏时间，入库时间就是最接近的
        sql += " AND COALESCE(NULLIF(collected_at,0), created_at) >= ?"
        args.append(float(since))
    if q:
        like = f"%{q}%"
        if scope == "title":
            sql += " AND title LIKE ?"
            args.append(like)
        elif scope == "author":
            sql += " AND author LIKE ?"
            args.append(like)
        elif scope == "body":
            sql += " AND (note_json LIKE ? OR transcript LIKE ? OR my_note LIKE ?)"
            args += [like] * 3
        else:
            sql += (" AND (title LIKE ? OR author LIKE ? OR note_json LIKE ? OR transcript LIKE ?"
                    " OR my_note LIKE ?)")
            args += [like] * 5
    # 时间排序：优先用收藏时间，其次发布时间，最后入库时间
    tkey = "COALESCE(NULLIF(collected_at,0), published_at, created_at)"
    added = "COALESCE(NULLIF(collected_at,0), created_at)"   # 什么时候收藏/入库的
    sql += {"long": " ORDER BY duration DESC, id DESC",
            "short": " ORDER BY duration ASC, id DESC",
            "time_desc": f" ORDER BY {tkey} DESC, id DESC",
            "time_asc": f" ORDER BY {tkey} ASC, id ASC",
            "new": f" ORDER BY {added} DESC, id DESC",   # 最新收藏：按进库时间
            # 处理中的排最前，其余按插队值 → 原优先级 → id
            "queue": f" ORDER BY CASE WHEN status='queued' THEN 1 ELSE 0 END, COALESCE(queue_prio,0) DESC, {PRIORITY_SQL} id ASC",
            "done": " ORDER BY COALESCE(done_at, updated_at) DESC, id DESC",
            "done_asc": " ORDER BY COALESCE(done_at, updated_at) ASC, id ASC"}.get(sort, " ORDER BY id DESC")
    sql += " LIMIT ?"
    args.append(limit)
    out = []
    for r in conn().execute(sql, args).fetchall():
        d = dict(r)
        d["summary"] = d.get("summary") or ""
        d["note_title"] = d.get("note_title") or ""
        d["difficulty"] = d.get("difficulty") or ""
        out.append(d)
    return out


def _plat_sql(platform):
    """平台过滤片段（老数据 platform 为空，按抖音算）。"""
    if not platform:
        return "", []
    if platform == "douyin":
        return " AND COALESCE(NULLIF(platform,''),'douyin')='douyin'", []
    return " AND platform=?", [platform]


def items_by_aweme(aweme_ids):
    """缓存文件 → 对应条目（标题、封面）。"""
    ids = [str(x) for x in (aweme_ids or []) if x]
    if not ids:
        return {}
    out = {}
    for i in range(0, len(ids), 400):
        chunk = ids[i:i + 400]
        q = ",".join("?" * len(chunk))
        for r in conn().execute(
                f"SELECT id, aweme_id, title, cover, platform, duration FROM items WHERE aweme_id IN ({q})",
                chunk):
            out[str(r["aweme_id"])] = dict(r)
    return out


def items_with_video(limit=5000):
    """所有能缓存视频的条目（用于「把全部视频都缓存到本地」）。"""
    rows = conn().execute(
        "SELECT id, aweme_id, title, platform, media_type FROM items "
        "WHERE COALESCE(deleted_at,0)=0 AND COALESCE(aweme_id,'')<>'' "
        "AND COALESCE(media_type,'')<>'note' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def items_for_classify(only_missing=True, limit=5000, platform=None):
    """分类用：只要标题这些轻量字段。"""
    plat, args = _plat_sql(platform)
    sql = ("SELECT id,title,author,media_type,duration,category,subcategory FROM items "
           "WHERE COALESCE(deleted_at,0)=0" + plat)
    if only_missing:
        sql += " AND (category IS NULL OR category='')"
    sql += " ORDER BY id LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn().execute(sql, args).fetchall()]


def items_to_refine(limit=5000, platform=None):
    """分得不准的：还没分类的，或者被规则归到「其他」的。给 AI 再分一次用。"""
    plat, args = _plat_sql(platform)
    args.append(limit)
    rows = conn().execute(
        "SELECT id,title,author,media_type,duration,category,subcategory FROM items "
        "WHERE COALESCE(deleted_at,0)=0 AND (category IS NULL OR category='' OR category='其他')" + plat +
        " ORDER BY id LIMIT ?", args).fetchall()
    return [dict(r) for r in rows]


def items_without_sub(limit=5000, platform=None):
    """已经有分类、但还没子分类的条目：只补子分类，省流量。"""
    plat, args = _plat_sql(platform)
    args.append(limit)
    rows = conn().execute(
        "SELECT id,title,author,media_type,duration,category,subcategory FROM items "
        "WHERE COALESCE(deleted_at,0)=0 AND category IS NOT NULL AND category<>'' "
        "AND (subcategory IS NULL OR subcategory='')" + plat +
        " ORDER BY id LIMIT ?", args).fetchall()
    return [dict(r) for r in rows]


def items_for_reclassify(limit=5000, platform=None):
    """全部重分：已经由笔记（AI 读完整文字稿）分好的那些不动。"""
    plat, args = _plat_sql(platform)
    args.append(limit)
    rows = conn().execute(
        "SELECT id,title,author,media_type,duration,category,subcategory FROM items "
        "WHERE COALESCE(deleted_at,0)=0 AND (category IS NULL OR category='' OR COALESCE(category_src,'') IN ('rule','ai'))" + plat +
        " ORDER BY id LIMIT ?", args).fetchall()
    return [dict(r) for r in rows]


def set_categories(mapping, src="rule"):
    """批量写分类：mapping 是 {id: 分类} 或 {id: (分类, 子分类)}，一次事务写完。"""
    if not mapping:
        return 0
    now = time.time()
    rows = []
    for i, val in mapping.items():
        if isinstance(val, (tuple, list)):
            cat, sub = (val + ("",))[:2] if len(val) < 2 else val[:2]
        else:
            cat, sub = val, ""
        rows.append((str(cat or "其他")[:40], str(sub or "")[:30], src, now, int(i)))
    with _write_lock:
        conn().executemany(
            "UPDATE items SET category=?, subcategory=?, category_src=?, updated_at=? WHERE id=?", rows)
        conn().commit()
    return len(rows)


def done_items():
    """学习库里的全部笔记（含 JSON 字段），图谱、共识观点和周报用。"""
    return [_row(r) for r in conn().execute(
        "SELECT id,title,author,category,learned,learned_at,starred,created_at,md_path,media_type,"
        "note_json,deep_json,chat_json FROM items WHERE status='done' AND COALESCE(deleted_at,0)=0 ORDER BY id")]


def get_insight(category):
    r = conn().execute("SELECT * FROM insights WHERE category=?", (category,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["data"] = json.loads(d.pop("data_json"))
    d["item_ids"] = [int(x) for x in d["item_ids"].split(",") if x]
    return d


def list_insights():
    return [get_insight(r["category"]) for r in conn().execute("SELECT category FROM insights ORDER BY created_at DESC")]


def save_insight(category, data, item_ids, model, md_path):
    with _write_lock:
        conn().execute(
            "INSERT OR REPLACE INTO insights(category,data_json,item_ids,model,md_path,created_at) VALUES(?,?,?,?,?,?)",
            (category, json.dumps(data, ensure_ascii=False), ",".join(map(str, item_ids)), model, md_path, time.time()))
        conn().commit()


def _norm_title(t):
    """查重用的标题归一化：去掉话题标签、标点、空格，取前 40 个字。"""
    import re
    t = str(t or "")
    t = re.sub(r"#[^#\s]+", " ", t)
    t = re.sub(r"\W+", "", t)
    return t.lower()[:40]


def _bigrams(s):
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _jac(a, b):
    A, B = _bigrams(a), _bigrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def _doc_tokens(text):
    """把一段中文切成「二元组 + 英文词」，用来算内容相似度。"""
    import collections
    import re
    text = (text or "").lower()
    text = re.sub("#[^#" + chr(92) + "s]+", " ", text)
    text = re.sub("https?://" + chr(92) + "S+", " ", text)
    toks = []
    for run in re.findall("[" + chr(0x4E00) + "-" + chr(0x9FFF) + "]+", text):
        if len(run) == 1:
            toks.append(run)
        else:
            toks += [run[i:i + 2] for i in range(len(run) - 1)]
    toks += re.findall("[a-z][a-z0-9+_.-]{1,}", text)
    return collections.Counter(toks)


def _note_text(it):
    n = it.get("note") or {}
    parts = [it.get("title") or "", n.get("title") or "", n.get("summary") or ""]
    parts += [str(x) for x in (n.get("points") or [])[:8]]
    parts += [str(c.get("term", "")) + " " + str(c.get("explain", ""))
              for c in (n.get("concepts") or [])[:6]]
    return chr(10).join(parts)


_sim_cache = {"key": None, "val": None}


def _pairwise_cosine(docs):
    """tf-idf + 余弦，返回 {(id_a, id_b): 相似度}（只算有共同词的组合）。"""
    import math
    df = {}
    for c in docs.values():
        for t in c:
            df[t] = df.get(t, 0) + 1
    n = len(docs)
    vecs = {}
    for i, c in docs.items():
        v = {t: (1 + math.log(k)) * math.log(1 + n / df[t]) for t, k in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs[i] = (v, norm)
    post = {}
    for i, (v, _n) in vecs.items():
        for t in v:
            post.setdefault(t, []).append(i)
    dot = {}
    for t, lst in post.items():
        if len(lst) < 2 or len(lst) > n * 0.6:   # 太常见的词没有区分度
            continue
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                i, j = lst[a], lst[b]
                dot[(i, j)] = dot.get((i, j), 0.0) + vecs[i][0][t] * vecs[j][0][t]
    return {k: v / (vecs[k[0]][1] * vecs[k[1]][1]) for k, v in dot.items()}


DUP_TEXT = 0.5     # 文字稿这么像：几乎就是同一条视频
DUP_NOTE = 0.55    # 笔记（拆解）这么像：判断为重复
NEAR = 0.35        # 达到这个相似度的连成一组，标成「内容相近」


_BOILER = re.compile(r"没有可学习的实质内容|没有可提取|无法提取|没有可识别|没有可获取|无实际内容|"
                     r"没有可学习的|仅剩片尾|没有可提取的具体")


def similar_content_groups(limit=80, platform=None):
    """按「拆解出来的内容」找相似条目。

    主要看文字稿（同一条视频被不同账号搬运时，文字稿几乎一样），
    笔记的总结/观点也算一份（0.85 权重）。返回的每组带 tier：
    dup=几乎重复，near=内容相近，都得你自己确认才删。
    """
    plat = ""
    args = []
    if platform:
        if platform == "douyin":
            plat = " AND COALESCE(NULLIF(platform,''),'douyin')='douyin'"
        else:
            plat = " AND platform=?"
            args.append(platform)
    rows = conn().execute(
        "SELECT id,title,aweme_id,author,duration,cover,category,subcategory,"
        "collected_at,created_at,updated_at,transcript,note_json FROM items "
        "WHERE COALESCE(deleted_at,0)=0 AND status='done' AND note_json IS NOT NULL" + plat +
        " ORDER BY id", args).fetchall()
    items, text_docs, note_docs = [], {}, {}
    for r in rows:
        d = dict(r)
        raw = d.pop("note_json", None)
        try:
            d["note"] = json.loads(raw or "{}")
        except Exception:
            d["note"] = {}
        d["n_points"] = len(d["note"].get("points") or [])
        d["summary"] = d["note"].get("summary") or ""
        d["note_title"] = d["note"].get("title") or ""
        items.append(d)
        # 套话（"没有可学习的实质内容/无法提取"）不是内容，参与相似度会把一堆无关视频连成一片
        boiler = bool(_BOILER.search(d["summary"] + " " + " ".join(
            str(x) for x in (d["note"].get("points") or [])[:4])))
        d["boiler"] = boiler
        text_docs[d["id"]] = collections.Counter() if boiler else _doc_tokens((d.get("transcript") or "")[:2500])
        note_docs[d["id"]] = collections.Counter() if boiler else _doc_tokens(_note_text(d))
    if len(items) < 2:
        return []
    key = (len(items), max((it.get("updated_at") or 0) for it in items))
    with _write_lock:
        if _sim_cache["key"] == key:
            return _sim_cache["val"]

    by_text = _pairwise_cosine(text_docs)
    by_note = _pairwise_cosine(note_docs)
    pair = {}
    for k, v in by_note.items():
        pair[k] = v * 0.85
    for k, v in by_text.items():
        pair[k] = max(pair.get(k, 0.0), v)

    parent = {it["id"]: it["id"] for it in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for (i, j), s in pair.items():
        if s >= NEAR:
            union(i, j)

    by_title = {}
    for it in items:  # 标题一模一样的，不管内容长短都算一组
        k = _norm_title(it["title"])
        if len(k) >= 6:
            by_title.setdefault(k, []).append(it["id"])
    for ids in by_title.values():
        for x in ids[1:]:
            union(ids[0], x)

    groups = {}
    for it in items:
        groups.setdefault(find(it["id"]), []).append(it)

    def brief(it):
        return {"id": it["id"], "title": it["title"], "note_title": it["note_title"],
                "summary": it["summary"], "author": it["author"], "duration": it["duration"],
                "cover": it["cover"], "category": it["category"], "subcategory": it["subcategory"],
                "collected_at": it["collected_at"], "created_at": it["created_at"],
                "n_points": it["n_points"], "aweme_id": it["aweme_id"]}

    out = []
    for lst in groups.values():
        if len(lst) < 2:
            continue
        best, dup = 0.0, False
        for i, a in enumerate(lst):
            for b in lst[i + 1:]:
                k = (a["id"], b["id"])
                s = pair.get(k, 0.0)
                best = max(best, s)
                if by_text.get(k, 0.0) >= DUP_TEXT or by_note.get(k, 0.0) >= DUP_NOTE:
                    dup = True
        lst.sort(key=lambda x: (-(len(x["summary"]) + x["n_points"] * 120), x["id"]))
        out.append({"key": lst[0]["id"], "score": round(min(0.99, best), 2),
                    "tier": "dup" if dup else "near",
                    "items": [brief(it) for it in lst]})
    out.sort(key=lambda g: (0 if g["tier"] == "dup" else 1, -len(g["items"]), -g["score"]))
    out = out[:limit]
    with _write_lock:
        _sim_cache["key"], _sim_cache["val"] = key, out
    return out


def duplicate_groups(min_len=6, limit=200):
    """找重复：

    1) 标题去掉话题标签/标点后完全一样；
    2) 同一个作者、标题前 16 个字一样；
    3) 同一个作者、时长几乎一样（差 1.5 秒内）而且标题相似（二元组 Jaccard ≥ 0.55）。
    """
    rows = conn().execute(
        "SELECT id,title,author,status,duration,created_at,cover,url,category,subcategory "
        "FROM items WHERE COALESCE(deleted_at,0)=0 ORDER BY id").fetchall()
    items = [dict(r) for r in rows]
    parent = {r["id"]: r["id"] for r in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_norm, by_author = {}, {}
    for r in items:
        k = _norm_title(r["title"])
        if len(k) >= min_len:
            by_norm.setdefault(k, []).append(r)
        if (r.get("author") or "").strip():
            by_author.setdefault(r["author"].strip(), []).append(r)

    for lst in by_norm.values():
        for x in lst[1:]:
            union(lst[0]["id"], x["id"])

    for lst in by_author.values():
        if len(lst) < 2:
            continue
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                x, y = lst[i], lst[j]
                nx, ny = _norm_title(x["title"]), _norm_title(y["title"])
                if not nx or not ny:
                    continue
                same_prefix = len(nx[:16]) >= 8 and nx[:16] == ny[:16]
                dx, dy = x.get("duration") or 0, y.get("duration") or 0
                dur_close = dx > 0 and dy > 0 and abs(dx - dy) <= 1.5
                if same_prefix or (dur_close and _jac(nx, ny) >= 0.55):
                    union(x["id"], y["id"])

    groups = {}
    for r in items:
        groups.setdefault(find(r["id"]), []).append(r)
    out = [{"key": k, "items": v} for k, v in groups.items() if len(v) > 1]
    out.sort(key=lambda g: (-len(g["items"]), g["items"][0]["id"]))
    return out[:limit]


_dups_n_cache = {"t": 0.0, "n": 0}
_dups_busy = {"on": False}


def dups_count(min_gap=600.0):
    """侧边栏徽标用：能清掉多少条重复。

    计算要读所有笔记算相似度，慢（几百毫秒到几秒），**绝不能卡在 /api/state 里**，
    所以放后台线程算，接口只返回上次算好的值。
    """
    now = time.time()
    if now - _dups_n_cache["t"] >= min_gap and not _dups_busy["on"]:
        def _work():
            _dups_busy["on"] = True
            try:
                n = sum(len(g["items"]) - 1 for g in similar_content_groups())
            except Exception:
                n = _dups_n_cache["n"]
            _dups_n_cache["t"], _dups_n_cache["n"] = time.time(), n
            _dups_busy["on"] = False

        import threading
        threading.Thread(target=_work, daemon=True, name="dups-count").start()
    return _dups_n_cache["n"]


def stats():
    c = conn()
    by_status = {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM items WHERE COALESCE(deleted_at,0)=0 GROUP BY status")}
    # 学习库左侧的分类：只算已经整理成笔记的（保持原来的含义）
    cats = [dict(r) for r in c.execute(
        "SELECT category, COUNT(*) n, SUM(learned) learned FROM items WHERE status='done' AND COALESCE(deleted_at,0)=0 "
        "GROUP BY category ORDER BY n DESC")]
    # 收藏库用的分类：所有条目都算，另外带上其中有多少条已经变成笔记
    all_cats = [dict(r) for r in c.execute(
        "SELECT category, COUNT(*) n, COALESCE(SUM(status='done'),0) done FROM items "
        "WHERE category IS NOT NULL AND category<>'' AND COALESCE(deleted_at,0)=0 GROUP BY category ORDER BY n DESC")]
    sub_rows = [dict(r) for r in c.execute(
        "SELECT category, COALESCE(NULLIF(subcategory,''),'未细分') sub, COUNT(*) n FROM items "
        "WHERE category IS NOT NULL AND category<>'' AND COALESCE(deleted_at,0)=0 GROUP BY category, sub ORDER BY n DESC")]
    by_cat = {}
    for r in sub_rows:
        by_cat.setdefault(r["category"], []).append({"sub": r["sub"], "n": r["n"]})
    for cat in all_cats:
        cat["subs"] = by_cat.get(cat["category"], [])
    learned = c.execute("SELECT COUNT(*) FROM items WHERE status='done' AND learned=1 AND COALESCE(deleted_at,0)=0").fetchone()[0]
    starred = c.execute("SELECT COUNT(*) FROM items WHERE status='done' AND starred=1 AND COALESCE(deleted_at,0)=0").fetchone()[0]
    dur = c.execute(
        "SELECT COUNT(*) n, COALESCE(SUM(duration),0) total, COALESCE(AVG(NULLIF(duration,0)),0) avg,"
        " COALESCE(SUM(CASE WHEN duration>0 AND duration<=60 THEN 1 ELSE 0 END),0) s,"
        " COALESCE(SUM(CASE WHEN duration>60 AND duration<=300 THEN 1 ELSE 0 END),0) m,"
        " COALESCE(SUM(CASE WHEN duration>300 AND duration<=900 THEN 1 ELSE 0 END),0) l,"
        " COALESCE(SUM(CASE WHEN duration>900 THEN 1 ELSE 0 END),0) xl FROM items WHERE COALESCE(deleted_at,0)=0").fetchone()
    classified = c.execute(
        "SELECT COUNT(*) FROM items WHERE category IS NOT NULL AND category<>'' AND COALESCE(deleted_at,0)=0").fetchone()[0]
    # 按平台分开统计（抖音 / 小红书）：收藏库要分开展示
    by_platform = {}
    for r in c.execute("SELECT COALESCE(NULLIF(platform,''),'douyin') p, COUNT(*) n FROM items "
                       "WHERE COALESCE(deleted_at,0)=0 GROUP BY p"):
        by_platform[r["p"]] = r["n"]
    plat_cats = {}
    rows = c.execute(
        "SELECT COALESCE(NULLIF(platform,''),'douyin') p, category, COUNT(*) n, "
        "COALESCE(SUM(status='done'),0) done FROM items "
        "WHERE COALESCE(deleted_at,0)=0 AND category IS NOT NULL AND category<>'' "
        "GROUP BY p, category ORDER BY n DESC").fetchall()
    for r in rows:
        plat_cats.setdefault(r["p"], []).append({"category": r["category"], "n": r["n"], "done": r["done"]})
    plat_stats = {}
    for r in c.execute(
            "SELECT COALESCE(NULLIF(platform,''),'douyin') p, COUNT(*) n, "
            "COALESCE(SUM(status='done'),0) done, COALESCE(SUM(duration),0) total, "
            "COALESCE(AVG(NULLIF(duration,0)),0) avg, "
            "COALESCE(SUM(category IS NOT NULL AND category<>''),0) classified "
            "FROM items WHERE COALESCE(deleted_at,0)=0 GROUP BY p").fetchall():
        plat_stats[r["p"]] = {"total": r["n"], "done": r["done"], "dur_total": r["total"],
                              "dur_avg": r["avg"], "classified": r["classified"]}
    total = sum(by_status.values())
    return {"by_status": by_status, "categories": cats, "all_categories": all_cats,
            "by_platform": by_platform, "platform_categories": plat_cats,
            "platform_stats": plat_stats,
            "learned": learned, "starred": starred, "total": total,
            "duration": {"total": dur["total"], "avg": dur["avg"], "n": dur["n"],
                         "buckets": {"s": dur["s"], "m": dur["m"], "l": dur["l"], "xl": dur["xl"]}},
            "classify": {"classified": classified, "unclassified": max(0, total - classified)}}


def requeue_failed():
    """把失败的条目全部重新排队（浏览器问题修好后用得上）。"""
    c = conn()
    n = c.execute("UPDATE items SET status='queued', attempts=0, reason=NULL "
                  "WHERE status='failed' AND COALESCE(deleted_at,0)=0").rowcount
    c.commit()
    return n
