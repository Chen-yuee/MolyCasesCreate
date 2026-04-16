"""
手动分配 evidence 位置脚本。

参考前端 QueryDetailPanel.jsx 中「确认并重新应用位置」按钮的逻辑：
1. 对于已润色的 evidence，先减退再分配位置
2. 对所有 evidence 设置目标位置（target_dia_id）和 session_key
"""

from typing import List, Dict
from .data_store import store
from .data_loader import loader


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
    # 检查 assignments 格式
    for i, assignment in enumerate(assignments):
        if "evidence_id" not in assignment:
            return {"success": False, "error": f"Assignment {i} missing 'evidence_id'"}
        if "target_dia_id" not in assignment:
            return {"success": False, "error": f"Assignment {i} missing 'target_dia_id'"}

    q = store.get_query(query_id)
    if not q:
        return {"success": False, "error": f"Query {query_id} not found"}

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
    for ev in all_evidence:
        target_dia_id = assignment_map.get(ev.id)
        if not target_dia_id:
            continue

        # 检查位置是否发生改变
        position_changed = ev.target_dia_id != target_dia_id

        # 只有位置改变且状态是 polished 时才去除润色
        if position_changed and ev.status == "polished":
            store.unpolish_evidence_from_message(ev, q)
            unpolished_count += 1

    # 2. 分配位置
    processed_count = 0
    for ev in all_evidence:
        target_dia_id = assignment_map.get(ev.id)
        if not target_dia_id:
            # 这里的continue导致前端报错？？？后续得看。什么情况下没有dia_id???
            continue

        msg = loader.get_message_by_dia_id(q.sample_id, target_dia_id)
        if not msg:
            continue

        ev.target_dia_id = target_dia_id
        ev.session_key = msg["session_key"]
        ev.status = "positioned"
        store.update_evidence(ev)
        processed_count += 1

    return {
        "success": True,
        "processed": processed_count,
        "unpolished": unpolished_count,
    }
