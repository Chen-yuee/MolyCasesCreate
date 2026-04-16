from typing import List, Optional, Dict, Tuple
from .data_loader import loader
from .models import Evidence


def _derive_implicit_constraints(evidences: List[Evidence]) -> Dict[str, List[dict]]:
    """
    从显式约束推导出隐式约束。

    隐式约束包括：
    1. 顺序约束：每个 evidence 必须在前面的之后
    2. Session 约束传递：如果 A 和 C 在同一 session，B 在中间，则 B 也应该在同一 session
    3. 距离约束传递：如果 A 和 C 有距离约束，中间的 evidence 也受影响

    返回：{evidence_id: [{"type": "after", "target_id": ...}, ...]}
    """
    implicit = {}

    # 1. 基于列表顺序的隐式约束：每个 evidence 必须在前面的之后
    for i, ev in enumerate(evidences):
        implicit[ev.id] = []
        # 必须在所有前面的 evidence 之后
        for j in range(i):
            implicit[ev.id].append({
                "type": "after",
                "target_id": evidences[j].id
            })

    # 2. 基于显式约束推导
    for i, ev in enumerate(evidences):
        for constraint in ev.constraints:
            target_id = constraint.target_evidence_id
            target_idx = next((j for j, e in enumerate(evidences) if e.id == target_id), None)
            if target_idx is None:
                continue

            start_idx = min(i, target_idx)
            end_idx = max(i, target_idx)

            # 2.1 Same session 约束传递
            if constraint.same_session:
                # 所有在它们之间的 evidence 也应该在同一 session
                for j in range(start_idx + 1, end_idx):
                    implicit[evidences[j].id].append({
                        "type": "same_session",
                        "target_id": target_id
                    })

            # 2.2 距离约束传递
            if constraint.max_turns is not None:
                # 中间的每个 evidence 与两端的距离都应该 < max_turns
                for j in range(start_idx + 1, end_idx):
                    implicit[evidences[j].id].append({
                        "type": "max_distance",
                        "target_id": evidences[start_idx].id,
                        "max_turns": constraint.max_turns
                    })
                    implicit[evidences[j].id].append({
                        "type": "max_distance",
                        "target_id": evidences[end_idx].id,
                        "max_turns": constraint.max_turns
                    })

    return implicit


def _session_num(session_key: str) -> int:
    try:
        return int(session_key.split("_")[1])
    except (IndexError, ValueError):
        return 0


def _get_message_index(sample_idx: int, dia_id: str) -> int:
    """获取消息在对话中的位置索引"""
    all_msgs = loader.get_all_messages(sample_idx)
    idx = next((i for i, m in enumerate(all_msgs) if m["dia_id"] == dia_id), None)
    return idx if idx is not None else -1


def _get_turns_between(sample_idx: int, dia_id1: str, dia_id2: str) -> int:
    """计算两个 dia_id 之间隔了多少条消息（turns）"""
    all_msgs = loader.get_all_messages(sample_idx)
    idx1 = next((i for i, m in enumerate(all_msgs) if m["dia_id"] == dia_id1), None)
    idx2 = next((i for i, m in enumerate(all_msgs) if m["dia_id"] == dia_id2), None)
    if idx1 is None or idx2 is None:
        return -1
    return abs(idx2 - idx1) - 1  # 中间隔了多少条


def _validate_constraints(
    sample_idx: int,
    evidences: List[Evidence],
    assignments: Dict[str, dict]
) -> Tuple[bool, Optional[str]]:
    """验证所有约束是否满足"""
    for ev in evidences:
        if ev.id not in assignments:
            continue
        my_assignment = assignments[ev.id]
        my_dia_id = my_assignment["target_dia_id"]
        my_session = my_assignment["session_key"]

        for constraint in ev.constraints:
            target_id = constraint.target_evidence_id
            if target_id not in assignments:
                continue
            target_assignment = assignments[target_id]
            target_dia_id = target_assignment["target_dia_id"]
            target_session = target_assignment["session_key"]

            # 检查 same_session 约束
            if constraint.same_session is not None:
                if constraint.same_session and my_session != target_session:
                    return False, f"Evidence「{ev.content[:20]}...」要求与另一个 evidence 在同一 session，但分配结果不满足"
                if not constraint.same_session and my_session == target_session:
                    return False, f"Evidence「{ev.content[:20]}...」要求与另一个 evidence 不在同一 session，但分配结果不满足"

            # 检查 turns 约束
            turns = _get_turns_between(sample_idx, my_dia_id, target_dia_id)
            if turns < 0:
                continue
            if constraint.min_turns is not None and turns < constraint.min_turns:
                return False, f"Evidence「{ev.content[:20]}...」要求与另一个 evidence 至少间隔 {constraint.min_turns} turns，但实际只有 {turns} turns"
            if constraint.max_turns is not None and turns > constraint.max_turns:
                return False, f"Evidence「{ev.content[:20]}...」要求与另一个 evidence 最多间隔 {constraint.max_turns} turns，但实际有 {turns} turns"

    return True, None


def assign_positions(
    sample_idx: int,
    protagonist: str,
    evidences: List[Evidence],
) -> Tuple[bool, Optional[List[dict]], Optional[str]]:
    """
    为一组 evidence 分配插入位置，支持约束验证。
    evidences 已按 order 排序。
    返回 (success, assignments, error_message)
    """
    import random

    # 按 speaker 分组候选消息
    all_msgs = loader.get_all_messages(sample_idx)
    protagonist_msgs = [m for m in all_msgs if m["speaker"] == protagonist and len(m["text"]) >= 10]
    other_speaker = None
    for m in all_msgs:
        if m["speaker"] != protagonist:
            other_speaker = m["speaker"]
            break
    other_msgs = [m for m in all_msgs if m["speaker"] == other_speaker and len(m["text"]) >= 10] if other_speaker else []

    assignments: Dict[str, dict] = {}
    used_dia_ids = set()
    last_assigned_index = -1

    # 推导完备约束
    implicit = _derive_implicit_constraints(evidences)
    ev_id_to_obj = {ev.id: ev for ev in evidences}

    # 按 order 顺序分配
    for ev in evidences:
        speaker = ev.speaker or protagonist
        candidates = protagonist_msgs if speaker == protagonist else other_msgs
        # 只选择位置在上一个 evidence 之后的消息
        available = [
            m for m in candidates
            if m["dia_id"] not in used_dia_ids
            and _get_message_index(sample_idx, m["dia_id"]) > last_assigned_index
        ]

        if not available:
            return False, None, f"说话人「{speaker}」在剩余位置中没有可用消息（需保证顺序）"

        # 用显式约束 + 隐式约束筛选候选
        filtered = []
        for msg in available:
            valid = True

            # 检查显式约束
            for constraint in ev.constraints:
                target_id = constraint.target_evidence_id
                if target_id not in assignments:
                    continue
                target_a = assignments[target_id]
                t_dia = target_a["target_dia_id"]
                t_sess = target_a["session_key"]

                if constraint.same_session is not None:
                    if constraint.same_session and msg["session_key"] != t_sess:
                        valid = False; break
                    if not constraint.same_session and msg["session_key"] == t_sess:
                        valid = False; break

                turns = _get_turns_between(sample_idx, msg["dia_id"], t_dia)
                if turns >= 0:
                    if constraint.min_turns is not None and turns < constraint.min_turns:
                        valid = False; break
                    if constraint.max_turns is not None and turns > constraint.max_turns:
                        valid = False; break

            if not valid:
                continue

            # 检查隐式约束
            for ic in implicit.get(ev.id, []):
                if ic["target_id"] not in assignments:
                    continue
                target_a = assignments[ic["target_id"]]
                t_dia = target_a["target_dia_id"]
                t_sess = target_a["session_key"]

                if ic["type"] == "same_session":
                    if msg["session_key"] != t_sess:
                        valid = False; break
                elif ic["type"] == "max_distance":
                    turns = _get_turns_between(sample_idx, msg["dia_id"], t_dia)
                    if turns >= 0 and turns > ic["max_turns"]:
                        valid = False; break
                # "after" 类型已在 last_assigned_index 层面保证

            if valid:
                filtered.append(msg)

        # 有满足约束的候选就用，否则放宽到只保证顺序
        chosen = random.choice(filtered if filtered else available)
        chosen_index = _get_message_index(sample_idx, chosen["dia_id"])
        used_dia_ids.add(chosen["dia_id"])
        last_assigned_index = chosen_index
        assignments[ev.id] = {
            "evidence_id": ev.id,
            "target_dia_id": chosen["dia_id"],
            "session_key": chosen["session_key"],
            "original_text": chosen["text"],
        }

    # 最后验证所有约束（可能有些约束在分配时无法检查）
    valid, error = _validate_constraints(sample_idx, evidences, assignments)
    if not valid:
        # 如果验证失败，尝试重新分配（最多100次）
        for attempt in range(100):
            assignments = {}
            used_dia_ids = set()
            last_assigned_index = -1
            success = True
            for ev in evidences:
                speaker = ev.speaker or protagonist
                candidates = protagonist_msgs if speaker == protagonist else other_msgs
                available = [
                    m for m in candidates
                    if m["dia_id"] not in used_dia_ids
                    and _get_message_index(sample_idx, m["dia_id"]) > last_assigned_index
                ]
                if not available:
                    success = False
                    break
                chosen = random.choice(available)
                chosen_index = _get_message_index(sample_idx, chosen["dia_id"])
                used_dia_ids.add(chosen["dia_id"])
                last_assigned_index = chosen_index
                assignments[ev.id] = {
                    "evidence_id": ev.id,
                    "target_dia_id": chosen["dia_id"],
                    "session_key": chosen["session_key"],
                    "original_text": chosen["text"],
                }
            if not success:
                continue
            valid, error = _validate_constraints(sample_idx, evidences, assignments)
            if valid:
                break

        if not valid:
            return False, None, error

    return True, list(assignments.values()), None
