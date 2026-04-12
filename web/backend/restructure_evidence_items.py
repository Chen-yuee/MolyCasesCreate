"""
一次性迁移脚本：重构 evidence_items 结构
从 {"query_id": str, "query_text": str, "evidence_id": str, "evidence_content": str}
改为 {"query": {"id": str, "text": str}, "evidence": {"id": str, "content": str}}
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

    polished_messages = data.get("polished_messages", [])

    # 重构 evidence_items
    updated_count = 0
    for msg in polished_messages:
        new_items = []
        for item in msg.get("evidence_items", []):
            new_item = {
                "query": {
                    "id": item.get("query_id", ""),
                    "text": item.get("query_text", "")
                },
                "evidence": {
                    "id": item.get("evidence_id", ""),
                    "content": item.get("evidence_content", "")
                }
            }
            new_items.append(new_item)
            updated_count += 1
        msg["evidence_items"] = new_items

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
    print(f"- 重构了 {updated_count} 个 evidence_items")


if __name__ == "__main__":
    migrate()
