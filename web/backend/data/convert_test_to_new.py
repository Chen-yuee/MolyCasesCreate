#!/usr/bin/env python3
"""
数据转换脚本: 将 test 格式转换为 new 格式
- 提取嵌套的 evidences 到顶层数组
- 删除 evidence 中的 query_id, type, order 字段
- queries 中的 evidences 改为 ID 数组
- 简化 polished_messages 的 evidence_items
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(description="转换 test 格式到 new 格式")
parser.add_argument("input", help="输入文件路径")
parser.add_argument("-o", "--output", help="输出文件路径(默认覆盖输入)")
args = parser.parse_args()

input_path = Path(args.input)
output_path = Path(args.output) if args.output else input_path


def convert():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = input_path.with_name(f"{input_path.stem}.backup_{timestamp}{input_path.suffix}")
    shutil.copy2(input_path, backup_path)
    print(f"备份已保存到: {backup_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_evidences = []

    for query in data.get("queries", []):
        evidences = query.get("evidences", [])
        evidence_ids = []

        for ev in evidences:
            ev.pop("query_id", None)
            ev.pop("type", None)
            ev.pop("order", None)
            ev["queries"] = [{"id": query["id"]}]

            all_evidences.append(ev)
            evidence_ids.append(ev["id"])

        query["evidences"] = evidence_ids

    print(f"共提取 {len(all_evidences)} 条 evidence")

    for msg in data.get("polished_messages", []):
        for item in msg.get("evidence_items", []):
            item.pop("query", None)

    new_data = {
        "queries": data["queries"],
        "evidences": all_evidences,
        "polished_messages": data.get("polished_messages", []),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    print(f"转换完成，写入 {output_path}")


if __name__ == "__main__":
    convert()
