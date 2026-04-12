import json
import os
import re
from typing import Optional


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        # 从 web/backend 往上找 config.json
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_data_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # 优先用 remapped 版本
    remapped = os.path.join(base, "data", "CN", "locomo10_CN_remapped.json")
    original = os.path.join(base, "data", "CN", "locomo10_CN.json")
    return remapped if os.path.exists(remapped) else original


def get_store_path() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "queries_store.json")


def classify_evidence(content: str) -> str:
    if any(kw in content for kw in ["公司", "负责人", "经理", "总监", "联系人"]):
        return "contact"
    if re.search(r"\d{2,4}年\d{1,2}月\d{1,2}日", content) or \
       re.search(r"\d{1,2}[点时]\d{0,2}", content):
        return "schedule"
    if any(kw in content for kw in ["待办", "任务", "记得", "提醒"]):
        return "todo"
    return "general"
