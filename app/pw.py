"""整个后台线程共用一个 Playwright 实例。

Playwright 的同步 API 不允许在同一个线程里起两个实例，否则会报
「It looks like you are using Playwright Sync API inside the asyncio loop」。
抖音和小红书两个浏览器的代码都要通过这里拿实例。
"""
from __future__ import annotations

import threading

from playwright.sync_api import sync_playwright

_lock = threading.Lock()
_pw = None


def get():
    global _pw
    with _lock:
        if _pw is None:
            _pw = sync_playwright().start()
        return _pw


def shutdown():
    global _pw
    with _lock:
        if _pw is not None:
            try:
                _pw.stop()
            except Exception:
                pass
            _pw = None
