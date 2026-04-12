"""
一次性迁移脚本：为 evidence_items 添加 query_text 和 evidence_content
"""
import json
import os
from datetime import datetime
from config import get_store_path


def migrate():
    store_path = get_store_path()
    if not os.path.exists(store_path):
        print(f"数据文件不存在: {store_path}")
        return

    # 读取现有数据
    with open(store_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    polished_messages = data.get("polished_messages", [])

    # 构建 query 和 evidence 的查找字典
    query_map = {q["id"]: q for q in queries}
    evidence_map = {}
    for q in queries:
        for ev in q.get("evidences", []):
            evidence_map[ev["id"]] = ev

    # 更新 polished_messages
    updated_count = 0
    for msg in polished_messages:
        for item in msg.get("evidence_items", []):
            query_id = item.get("query_id")
            evidence_id = item.get("evidence_id")

            # 添加 query_text
            if query_id in query_map:
                item["query_text"] = query_map[query_id].get("query_text", "")
            else:
                item["query_text"] = ""

            # 添加 evidence_content
            if evidence_id in evidence_map:
                item["evidence_content"] = evidence_map[evidence_id].get("content", "")
            else:
                item["evidence_content"] = ""

            updated_count += 1

    # 备份原文件（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{store_path}.backup_{timestamp}"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已备份原数据到: {backup_path}")

    # 保存新数据
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"迁移完成！")
    print(f"- 更新了 {len(polished_messages)} 个 PolishedMessages")
    print(f"- 更新了 {updated_count} 个 evidence_items")


if __name__ == "__main__":
    migrate()
