#!/usr/bin/env python3
"""
数据整理脚本: 将原始 queries_store.json 整理为规范格式.
- 提取 evidence 到与 queries, polished_messages 同级
- 删除 evidence 中的 type 字段
- 给 evidence 添加 queries 字段(替换 query_id)
- 从 polished_messages 的 evidence_items 中删除 query 字段
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

import argparse

parser = argparse.ArgumentParser(description="整理 queries_store.json 数据格式")
parser.add_argument("input", help="输入文件路径")
parser.add_argument("-o", "--output", help="输出文件路径(默认覆盖输入)")
args = parser.parse_args()

input_path = Path(args.input)
output_path = Path(args.output) if args.output else input_path


def migrate():
    # 备份
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = input_path.with_name(f"{input_path.stem}.backup_{timestamp}{input_path.suffix}")
    shutil.copy2(input_path, backup_path)
    print(f"备份已保存到: {backup_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. 提取 evidence 到顶层，并记录每个 evidence 在其 query 中的顺序
    all_evidences = []
    for query in data.get("queries", []):
        evidences = query.pop("evidences", [])
        for idx, ev in enumerate(evidences):
            ev["queries"] = [{"id": query["id"], "order": idx}]
            all_evidences.append(ev)
    print(f"共提取 {len(all_evidences)} 条 evidence")

    # 2. 删除每个 evidence 的 type 和 query_id 字段
    for ev in all_evidences:
        ev.pop("type", None)
        ev.pop("query_id", None)

    # 4. 处理 polished_messages: 删除 evidence_items 中的 query 字段
    for msg in data.get("polished_messages", []):
        for item in msg.get("evidence_items", []):
            item.pop("query", None)

    # 构建新结构
    new_data = {
        "queries": data["queries"],
        "evidences": all_evidences,
        "polished_messages": data.get("polished_messages", []),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    print(f"整理完成，写入 {output_path}")


if __name__ == "__main__":
    migrate()
