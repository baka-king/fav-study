"""分类自查：用关键词给分类做一次体检，找出明显分错的条目。

不调用 AI，纯规则，几秒钟跑完。结果写成 Markdown，方便人看：
  - 每个分类有多少条
  - 明显分错的（标题里有美食词却分到 AI 类等），逐条列出来
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from . import config, db

RULES = [
    ("美食与烹饪", "吃|饭|菜|餐|食谱|烘焙|厨房|零食|咖啡|奶茶|火锅|烤肉|面条|饺子|汤|甜品|烤|煮|炒|蒸|酱|减脂餐"),
    ("健身与健康", "健身|训练|跑步|增肌|减脂|拉伸|深蹲|瑜伽|腹肌|有氧|体态|康复|肌肉"),
    ("摄影与剪辑", "相机|镜头|调色|修图|构图|布光|拍摄|后期|出片|摄影|剪辑|LUT|曝光"),
    ("穿搭与美妆", "穿搭|口红|妆容|护肤|美甲|发型|眼影|底妆|彩妆|护肤|香水|美瞳"),
    ("AI 编程", "代码|编程|函数|框架|报错|部署|docker|git|接口|调试|脚本"),
    ("AI 工具推荐", "插件|工具|客户端|安装包|开源|app|软件|浏览器扩展"),
    ("提示词技巧", "提示词|prompt|咒语|角色扮演|系统提示"),
]

# 这些分类里出现上面的词，属于正常
SAFE_CATS = {"生活与娱乐", "无法分类", "其他", "学习与成长", "商业与创业"}


def _all_items():
    rows = db.conn().execute(
        "SELECT id,title,note_json,category,platform FROM items "
        "WHERE status='done' AND COALESCE(deleted_at,0)=0").fetchall()
    for r in rows:
        d = dict(r)
        d["note_title"] = ""
        nj = d.get("note_json") or ""
        m = re.search(r'"title"\s*:\s*"([^"]{0,80})"', nj)
        if m:
            d["note_title"] = m.group(1)
        yield d


def run(write_file=True) -> dict:
    cats = {}
    suspicious = []
    total = 0
    for it in _all_items():
        total += 1
        cat = it["category"] or "未分类"
        cats[cat] = cats.get(cat, 0) + 1
        text = (it["title"] or "") + " " + (it["note_title"] or "")
        hit = None
        for expect, pat in RULES:
            if re.search(pat, text, re.I):
                hit = expect
                break
        if not hit:
            continue
        if hit == cat or cat in SAFE_CATS or cat == hit:
            continue
        suspicious.append({"id": it["id"], "title": (it["title"] or "")[:40],
                           "category": cat, "expect": hit})

    out = {"total": total, "cats": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
           "suspicious": suspicious[:80], "suspicious_n": len(suspicious)}
    if write_file:
        p = config.DATA / "tmp" / "cat_audit.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# 分类自查（{time.strftime('%F %T')}）", "",
                 f"已完成 {total} 条，疑似分错 {len(suspicious)} 条", "", "## 各分类条数", ""]
        for k, v in out["cats"].items():
            lines.append(f"- {k}：{v}")
        lines += ["", "## 疑似分错的条目（前 80 条）", ""]
        for s in out["suspicious"]:
            lines.append(f"- #{s['id']}　现分类：{s['category']}　更像：{s['expect']}　｜ {s['title']}")
        p.write_text("\n".join(lines), encoding="utf-8")
        out["file"] = str(p)
    return out