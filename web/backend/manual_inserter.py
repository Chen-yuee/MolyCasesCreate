"""
手动分配 evidence 位置脚本。

参考前端 QueryDetailPanel.jsx 中「确认并重新应用位置」按钮的逻辑：
1. 对于已润色的 evidence，先减退再分配位置
2. 对所有 evidence 设置目标位置（target_dia_id）和 session_key
"""

from typing import List, Dict
from .data_store import store
from .data_loader import loader
from .logger import get_logger

logger = get_logger("manual_inserter")


def apply_manual_positions(
    query_id: str,
    assignments: List[Dict[str, str]],
) -> Dict:
    """
    手动分配 evidence 位置。

    Args:
        query_id: 目标 query ID
        assignments: 每项含 evidence_id 和 target_dia_id
            例: [{"evidence_id": "ev1", "target_dia_id": "dia_001"}, ...]

    Returns:
        {"success": bool, "processed": int, "unpolished": int, "error": Optional[str]}
    """
    logger.info(f"开始手动分配位置 - query_id: {query_id}, assignments 数量: {len(assignments)}")

    # 检查 assignments 格式
    for i, assignment in enumerate(assignments):
        if "evidence_id" not in assignment:
            logger.error(f"Assignment {i} 缺少 'evidence_id'")
            return {"success": False, "error": f"Assignment {i} missing 'evidence_id'"}
        if "target_dia_id" not in assignment:
            logger.error(f"Assignment {i} 缺少 'target_dia_id'")
            return {"success": False, "error": f"Assignment {i} missing 'target_dia_id'"}

    q = store.get_query(query_id)
    if not q:
        logger.error(f"Query {query_id} 未找到")
        return {"success": False, "error": f"Query {query_id} not found"}

    logger.info(f"Query 找到 - sample_id: {q.sample_id}, evidences 数量: {len(q.evidences)}")

    # 构建 evidence_id -> assignment 映射
    assignment_map = {a["evidence_id"]: a["target_dia_id"] for a in assignments}

    # 按 query.evidences 列表顺序获取所有 evidence
    all_evidence = []
    for eid in q.evidences:
        ev = store.get_evidence(eid)
        if ev:
            all_evidence.append(ev)

    unpolished_count = 0

    # 1. 只对位置发生改变的 polished evidence 去除润色
    logger.debug("开始检查需要去除润色的 evidence")
    for ev in all_evidence:
        target_dia_id = assignment_map.get(ev.id)
        if not target_dia_id:
            continue

        # 检查位置是否发生改变
        position_changed = ev.target_dia_id != target_dia_id

        # 只有位置改变且状态是 polished 时才去除润色
        if position_changed and ev.status == "polished":
            logger.info(f"去除润色 - evidence_id: {ev.id}, 旧位置: {ev.target_dia_id}, 新位置: {target_dia_id}")
            store.unpolish_evidence_from_message(ev, q)
            unpolished_count += 1

    logger.info(f"去除润色完成 - 共 {unpolished_count} 个 evidence")

    # 2. 分配位置
    logger.debug("开始分配位置")
    processed_count = 0
    for ev in all_evidence:
        target_dia_id = assignment_map.get(ev.id)
        if not target_dia_id:
            logger.warning(f"Evidence {ev.id} 没有 target_dia_id，跳过")
            continue

        msg = loader.get_message_by_dia_id(q.sample_id, target_dia_id)
        if not msg:
            logger.warning(f"找不到 dia_id: {target_dia_id} (sample_id: {q.sample_id})")
            continue

        ev.target_dia_id = target_dia_id
        ev.session_key = msg["session_key"]
        ev.status = "positioned"
        store.update_evidence(ev)
        logger.debug(f"已分配位置 - evidence_id: {ev.id}, target_dia_id: {target_dia_id}")
        processed_count += 1

    logger.info(f"分配位置完成 - 处理: {processed_count}, 去除润色: {unpolished_count}")

    return {
        "success": True,
        "processed": processed_count,
        "unpolished": unpolished_count,
    }
