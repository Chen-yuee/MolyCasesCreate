"""
数据迁移脚本：将旧的 PolishedMessage 结构迁移到新的支持多 query 的结构
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
    old_polished_messages = data.get("polished_messages", [])

    # 按 (sample_id, dia_id) 重新组织 PolishedMessage
    new_polished_messages = {}

    for old_msg in old_polished_messages:
        sample_id = old_msg.get("sample_id")
        dia_id = old_msg.get("dia_id")
        key = f"{sample_id}:{dia_id}"

        if key not in new_polished_messages:
            # 创建新的 PolishedMessage
            new_polished_messages[key] = {
                "sample_id": sample_id,
                "dia_id": dia_id,
                "session_key": old_msg.get("session_key", ""),
                "original_text": old_msg.get("original_text", ""),
                "final_polished_text": old_msg.get("final_polished_text", ""),
                "evidence_items": [],
                "updated_at": old_msg.get("updated_at", datetime.now().isoformat())
            }

        # 添加 evidence_items
        query_id = old_msg.get("query_id")
        for ev_id in old_msg.get("evidence_ids", []):
            new_polished_messages[key]["evidence_items"].append({
                "query_id": query_id,
                "evidence_id": ev_id
            })

    # 保存迁移后的数据
    data["polished_messages"] = list(new_polished_messages.values())

    # 备份原文件
    backup_path = store_path + ".backup"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已备份原数据到: {backup_path}")

    # 保存新数据
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"迁移完成！")
    print(f"- 处理了 {len(queries)} 个 queries")
    print(f"- 创建了 {len(new_polished_messages)} 个 PolishedMessages")


if __name__ == "__main__":
    migrate()
