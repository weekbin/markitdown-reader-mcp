# -*- coding: utf-8 -*-
"""
回调通知模块
"""

from __future__ import annotations

import json
import logging
import urllib.request

_log = logging.getLogger("markitdown")


def _post_callback(callback_url: str, event: str, data: dict):
    """向 callback_url POST 事件通知，失败时记录日志但不阻塞主流程"""
    if not callback_url:
        return
    try:
        payload = json.dumps({"event": event, "data": data}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            callback_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            _log.debug(f"  _post_callback: event={event} status={resp.status}")
    except Exception as e:
        _log.debug(f"  _post_callback: event={event} failed={e}")
