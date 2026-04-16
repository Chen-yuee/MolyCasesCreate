#!/usr/bin/env python3
"""
数据修复脚本：重建 Query.evidences 字段

问题：数据结构重构后，Query 对象缺少 evidences 字段（应为 evidence ID 列表）
解决：从 Evidence.queries 字段反向重建 Query.evidences 字段

使用方法：
    python scripts/fix_query_evidences_field.py
"""

import json
import shutil
from datetime import datetime
from pathlib import Path


def fix_query_evidences():
    # 数据文件路径
    data_file = Path(__file__).parent.parent / "web/backend/data/queries_store.json"

    if not data_file.exists():
        print(f"错误：数据文件不存在 {data_file}")
        return False

    # 备份原始文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = data_file.with_suffix(f".backup.{timestamp}.json")
    shutil.copy2(data_file, backup_file)
    print(f"✓ 已备份原始文件到: {backup_file}")

    # 读取数据
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    evidences = data.get("evidences", [])

    print(f"\n数据统计:")
    print(f"  - Queries: {len(queries)}")
    print(f"  - Evidences: {len(evidences)}")

    # 为每个 query 初始化空的 evidences 列表
    for query in queries:
        query["evidences"] = []

    # 从 evidence.queries 反向重建 query.evidences
    fixed_count = 0
    for evidence in evidences:
        eid = evidence["id"]
        query_refs = evidence.get("queries", [])

        for query_ref in query_refs:
            qid = query_ref["id"]

            # 找到对应的 query
            for query in queries:
                if query["id"] == qid:
                    # 添加 evidence ID（避免重复）
                    if eid not in query["evidences"]:
                        query["evidences"].append(eid)
                        fixed_count += 1
                    break

    print(f"\n修复结果:")
    print(f"  - 添加了 {fixed_count} 个 evidence 引用")

    # 显示每个 query 的 evidences 数量
    for query in queries:
        qid = query["id"]
        ev_count = len(query["evidences"])
        print(f"  - Query {qid[:8]}... : {ev_count} evidences")

    # 写回文件
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 数据已修复并保存到: {data_file}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Query.evidences 字段修复脚本")
    print("=" * 60)

    success = fix_query_evidences()

    if success:
        print("\n✓ 修复完成！")
    else:
        print("\n✗ 修复失败")
        exit(1)
