"""用 GitHub REST API 提交整个目录（git 走代理握手失败，这里用 HTTP API 绕过）。

读 E:\\AI\\FavStudy-gh 下的源码与文档，一次性做成一个 commit 推到 main。
"""
import base64
import json
import os
import subprocess
import urllib.request
from pathlib import Path

REPO = "baka-king/fav-study"
ROOT = Path(r"E:\AI\FavStudy-gh")
PROXY = "http://127.0.0.1:7890"
API = "https://api.github.com"

TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
if not TOKEN:
    raise SystemExit("拿不到 gh token")

opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))


def call(method, path, body=None):
    url = API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "favstudy-sync",
    })
    with opener.open(req, timeout=60) as r:
        return json.loads(r.read().decode() or "{}")


SKIP_DIRS = {".git", "__pycache__", "data", "python", "backup", "models", "tmp", "node_modules"}
SKIP_SUFFIX = {".pyc", ".log", ".db", ".zip"}

files = {}
for p in ROOT.rglob("*"):
    if p.is_dir():
        continue
    rel = p.relative_to(ROOT).as_posix()
    if any(part in SKIP_DIRS for part in p.parts[len(ROOT.parts):-1]):
        continue
    if p.suffix.lower() in SKIP_SUFFIX:
        continue
    files[rel] = p

print("待提交文件:", len(files))

ref = call("GET", f"/repos/{REPO}/git/ref/heads/master")
head = ref["object"]["sha"]
base_commit = call("GET", f"/repos/{REPO}/git/commits/{head}")
base_tree = base_commit["tree"]["sha"]

tree = []
for rel, p in sorted(files.items()):
    body = p.read_bytes()
    try:
        text = body.decode("utf-8")
        is_text = True
    except UnicodeDecodeError:
        is_text = False
    blob = call("POST", f"/repos/{REPO}/git/blobs", {
        "content": base64.b64encode(body).decode() if not is_text else text,
        "encoding": "base64" if not is_text else "utf-8",
    })
    tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})

new_tree = call("POST", f"/repos/{REPO}/git/trees", {"base_tree": base_tree, "tree": tree})
commit = call("POST", f"/repos/{REPO}/git/commits", {
    "message": "v1.0.6：B站手动解析、显卡加速、三套主题、分类标准与自查",
    "tree": new_tree["sha"],
    "parents": [head],
})
call("PATCH", f"/repos/{REPO}/git/refs/heads/master", {"sha": commit["sha"], "force": False})
print("已推送 commit:", commit["sha"][:10])