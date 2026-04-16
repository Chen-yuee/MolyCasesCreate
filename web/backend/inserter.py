from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from .data_loader import loader
from .models import Evidence, EvidenceConstraint


# ── dia_id → 扁平化索引 lookup ─────────────────────────────────────────────

def _build_dia_index_map(sample_idx: int) -> Dict[str, int]:
    """构建 dia_id → 扁平化索引 的映射（按 session→turn 顺序）"""
    msgs = loader.get_all_messages(sample_idx)
    return {msg["dia_id"]: i for i, msg in enumerate(msgs)}


def _msg_to_index(msg: dict, idx_map: Dict[str, int]) -> int:
    """从 lookup table 获取扁平化索引"""
    return idx_map[msg["dia_id"]]


def _get_turns_between(idx_map: Dict[str, int], dia_id1: str, dia_id2: str) -> int:
    """用 lookup table 计算 turns 距离"""
    return abs(idx_map[dia_id1] - idx_map[dia_id2]) - 1


# ── EvidenceSlot ────────────────────────────────────────────────────────────

@dataclass
class EvidenceSlot:
    evidence_id: str
    status: str                      # "fixed" | "draft"
    target_dia_id: Optional[str]
    session_key: Optional[str]
    msg_index: Optional[int]           # 扁平化顺序号（从 lookup table 获取）
    speaker: str
    order: int
    explicit_constraints: List[EvidenceConstraint]
    implicit_constraints: List[dict] = field(default_factory=list)


# ── 隐式约束推导 ─────────────────────────────────────────────────────────────

def _derive_implicit_constraints(evidences: List[Evidence]) -> Dict[str, List[dict]]:
    """
    从显式约束推导出隐式约束。
    隐式约束包括：
    1. 顺序约束：每个 evidence 必须在前面的之后
    2. Session 约束传递：如果 A 和 C 在同一 session，B 在中间，则 B 也应该在同一 session
    3. 距离约束传递：如果 A 和 C 有距离约束，中间的 evidence 也受影响
    """
    implicit = {}

    # 1. 基于列表顺序的隐式约束：每个 evidence 必须在前面的之后
    for i, ev in enumerate(evidences):
        implicit[ev.id] = []
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

            if constraint.same_session:
                for j in range(start_idx + 1, end_idx):
                    implicit[evidences[j].id].append({
                        "type": "same_session",
                        "target_id": target_id
                    })

            if constraint.max_turns is not None:
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


# ── 约束检查 ────────────────────────────────────────────────────────────────

def _fmt_constraint_msg(slot: EvidenceSlot, c: EvidenceConstraint,
                          ctype: str, detail: str) -> str:
    return (
        f"Evidence「{slot.evidence_id}」（order={slot.order}）的约束「{ctype}」不满足：{detail}"
    )


def _msg_satisfies_all_constraints(
    slot: EvidenceSlot,
    msg: dict,
    slot_map: Dict[str, EvidenceSlot],
    assigned: Dict[str, str],
    idx_map: Dict[str, int],
    sample_idx: int,
) -> Tuple[bool, Optional[str]]:
    """
    检查 msg 是否满足 slot 的所有约束。
    返回 (True, None) 或 (False, error_message)
    """
    # 显式约束
    for c in slot.explicit_constraints:
        target_slot = slot_map.get(c.target_evidence_id)
        if target_slot is None:
            continue

        if target_slot.status == "fixed":
            t_dia = target_slot.target_dia_id
            t_sess = target_slot.session_key
        elif target_slot.evidence_id in assigned:
            t_dia = assigned[target_slot.evidence_id]
            t_sess = loader.get_message_by_dia_id(sample_idx, t_dia)["session_key"]
        else:
            continue

        if c.same_session is not None:
            if c.same_session and msg["session_key"] != t_sess:
                return False, _fmt_constraint_msg(slot, c, "same_session", "必须与目标在同一 session")
            if not c.same_session and msg["session_key"] == t_sess:
                return False, _fmt_constraint_msg(slot, c, "same_session", "必须与目标在不同 session")

        turns = _get_turns_between(idx_map, msg["dia_id"], t_dia)
        if turns >= 0:
            if c.min_turns is not None and turns < c.min_turns:
                return False, _fmt_constraint_msg(
                    slot, c, "min_turns", f"至少间隔 {c.min_turns} turns，实际 {turns}")
            if c.max_turns is not None and turns > c.max_turns:
                return False, _fmt_constraint_msg(
                    slot, c, "max_turns", f"至多间隔 {c.max_turns} turns，实际 {turns}")

    # 隐式约束
    for ic in slot.implicit_constraints:
        target_slot = slot_map.get(ic["target_id"])
        if target_slot is None:
            continue

        if target_slot.status == "fixed":
            t_dia = target_slot.target_dia_id
            t_sess = target_slot.session_key
        elif target_slot.evidence_id in assigned:
            t_dia = assigned[target_slot.evidence_id]
            t_sess = loader.get_message_by_dia_id(sample_idx, t_dia)["session_key"]
        else:
            continue

        if ic["type"] == "same_session":
            if msg["session_key"] != t_sess:
                return False, (
                    f"Evidence「{slot.evidence_id}」隐式约束：必须与「{ic['target_id']}」同 session"
                )
        elif ic["type"] == "max_distance":
            turns = _get_turns_between(idx_map, msg["dia_id"], t_dia)
            if turns >= 0 and turns > ic["max_turns"]:
                return False, (
                    f"Evidence「{slot.evidence_id}」隐式约束：与「{ic['target_id']}」间隔 {turns} turns，"
                    f"超过上限 {ic['max_turns']}"
                )

    return True, None


# ── Phase 1 前置验证 ─────────────────────────────────────────────────────────

def _pre_validate_fixed_order(ev_slots: List[EvidenceSlot]) -> Optional[str]:
    """检查 fixed evidence 的顺序是否矛盾"""
    prev_fixed: Optional[EvidenceSlot] = None
    for slot in ev_slots:
        if slot.status == "fixed":
            if prev_fixed is not None and slot.msg_index <= prev_fixed.msg_index:
                return (
                    f"已定位的 evidence「{slot.evidence_id}」（order={slot.order}，"
                    f"dia_id={slot.target_dia_id}）出现在「{prev_fixed.evidence_id}」（order={prev_fixed.order}）之后，"
                    f"但位置不满足顺序约束（前者 dia_id={prev_fixed.target_dia_id}）。"
                    f"请手动调整已有 evidence 的位置。"
                )
            prev_fixed = slot
    return None


def _check_single_constraint(
    slot: EvidenceSlot, target: EvidenceSlot, c: EvidenceConstraint,
    idx_map: Dict[str, int],
) -> Optional[str]:
    """检查单个约束，slot 和 target 均已固定"""
    t_dia = target.target_dia_id
    t_sess = target.session_key
    s_dia = slot.target_dia_id
    if s_dia is None:
        return None

    if c.same_session is not None:
        if c.same_session and slot.session_key != t_sess:
            return _fmt_constraint_msg(slot, c, "same_session", "必须与目标在同一 session")
        if not c.same_session and slot.session_key == t_sess:
            return _fmt_constraint_msg(slot, c, "same_session", "必须与目标在不同 session")

    turns = _get_turns_between(idx_map, s_dia, t_dia)
    if turns >= 0:
        if c.min_turns is not None and turns < c.min_turns:
            return _fmt_constraint_msg(
                slot, c, "min_turns", f"至少间隔 {c.min_turns} turns，实际 {turns}")
        if c.max_turns is not None and turns > c.max_turns:
            return _fmt_constraint_msg(
                slot, c, "max_turns", f"至多间隔 {c.max_turns} turns，实际 {turns}")

    return None


def _pre_validate_fixed_constraints(
    ev_slots: List[EvidenceSlot], idx_map: Dict[str, int],
) -> Optional[str]:
    """检查 fixed evidence 之间是否有约束冲突"""
    slot_map = {s.evidence_id: s for s in ev_slots}
    for slot in ev_slots:
        if slot.status != "fixed":
            continue
        for c in slot.explicit_constraints:
            target = slot_map.get(c.target_evidence_id)
            if target is None or target.status != "fixed":
                continue
            err = _check_single_constraint(slot, target, c, idx_map)
            if err:
                return err
    return None


# ── 候选域构建 ──────────────────────────────────────────────────────────────

def _build_domain(
    slot: EvidenceSlot,
    ev_slots: List[EvidenceSlot],
    slot_map: Dict[str, EvidenceSlot],
    sample_idx: int,
    protagonist: str,
    assigned: Dict[str, str],
    last_assigned_index: int,
    idx_map: Dict[str, int],
) -> List[dict]:
    """
    为 draft slot 计算所有满足约束的候选消息。
    按 msg_index 升序返回（确定性）。
    """
    speaker = slot.speaker or protagonist
    all_msgs = loader.get_all_messages(sample_idx)
    candidates = [m for m in all_msgs if m["speaker"] == speaker]

    used = set()
    for sid, s in slot_map.items():
        if s.status == "fixed" and s.target_dia_id:
            used.add(s.target_dia_id)
    for eid, dia in assigned.items():
        used.add(dia)

    valid = []
    for msg in candidates:
        if msg["dia_id"] in used:
            continue
        msg_idx = _msg_to_index(msg, idx_map)
        if msg_idx <= last_assigned_index:
            continue
        ok, _ = _msg_satisfies_all_constraints(
            slot, msg, slot_map, assigned, idx_map, sample_idx)
        if ok:
            valid.append(msg)

    valid.sort(key=lambda m: _msg_to_index(m, idx_map))
    return valid


def _select_next_slot(
    draft_slots: List[EvidenceSlot],
    ev_slots: List[EvidenceSlot],
    slot_map: Dict[str, EvidenceSlot],
    sample_idx: int,
    protagonist: str,
    assigned: Dict[str, str],
    last_assigned_index: int,
    idx_map: Dict[str, int],
) -> Tuple[Optional[EvidenceSlot], List[dict]]:
    """
    MRV 启发式：选候选域最小的 draft slot。
    返回 (slot, domain)
    """
    best_slot = None
    best_domain: List[dict] = []
    best_size = float("inf")

    for slot in draft_slots:
        if slot.evidence_id in assigned:
            continue
        domain = _build_domain(
            slot, ev_slots, slot_map, sample_idx, protagonist,
            assigned, last_assigned_index, idx_map)
        if len(domain) < best_size:
            best_size = len(domain)
            best_slot = slot
            best_domain = domain
            if best_size == 0:
                break

    return best_slot, best_domain


# ── 回溯搜索 ────────────────────────────────────────────────────────────────

def _backtrack(
    ev_slots: List[EvidenceSlot],
    draft_slots: List[EvidenceSlot],
    slot_map: Dict[str, EvidenceSlot],
    sample_idx: int,
    protagonist: str,
    assigned: Dict[str, str],
    last_assigned_index: int,
    idx_map: Dict[str, int],
) -> Tuple[bool, Optional[Dict[str, str]], Optional[str]]:
    """
    回溯搜索。返回 (solved, assignment_dict, error)
    assignment_dict: {evidence_id: dia_id}
    """
    if len(assigned) == len(draft_slots):
        return True, assigned, None

    slot, domain = _select_next_slot(
        draft_slots, ev_slots, slot_map, sample_idx, protagonist,
        assigned, last_assigned_index, idx_map)

    if slot is None:
        return True, assigned, None

    if not domain:
        return False, None, (
            f"Evidence「{slot.evidence_id}」（order={slot.order}）没有可用的候选位置，"
            f"请检查约束设置。"
        )

    for msg in domain:
        new_assigned = dict(assigned)
        new_assigned[slot.evidence_id] = msg["dia_id"]
        new_last_index = max(last_assigned_index, _msg_to_index(msg, idx_map))

        dead_end = False
        for other_slot in draft_slots:
            if other_slot.evidence_id in new_assigned:
                continue
            other_domain = _build_domain(
                other_slot, ev_slots, slot_map, sample_idx, protagonist,
                new_assigned, new_last_index, idx_map)
            if not other_domain:
                dead_end = True
                break

        if dead_end:
            continue

        solved, result, err = _backtrack(
            ev_slots, draft_slots, slot_map, sample_idx, protagonist,
            new_assigned, new_last_index, idx_map)
        if solved:
            return True, result, None

    return False, None, (
        f"Evidence「{slot.evidence_id}」（order={slot.order}）的所有候选位置均导致后续无解。"
    )


# ── 约束最终验证 ────────────────────────────────────────────────────────────

def _validate_constraints(
    evidences: List[Evidence],
    assignments: Dict[str, dict],
    idx_map: Dict[str, int],
) -> Tuple[bool, Optional[str]]:
    """验证所有约束是否满足（防御性最终检查）"""
    for ev in evidences:
        if ev.id not in assignments:
            continue
        my = assignments[ev.id]
        my_dia_id = my["target_dia_id"]
        my_session = my["session_key"]

        for c in ev.constraints:
            target_id = c.target_evidence_id
            if target_id not in assignments:
                continue
            target = assignments[target_id]
            target_dia_id = target["target_dia_id"]
            target_session = target["session_key"]

            if c.same_session is not None:
                if c.same_session and my_session != target_session:
                    return False, (
                        f"Evidence「{ev.id}」要求与「{target_id}」同 session，但分配结果不满足"
                    )
                if not c.same_session and my_session == target_session:
                    return False, (
                        f"Evidence「{ev.id}」要求与「{target_id}」不同 session，但分配结果满足"
                    )

            turns = _get_turns_between(idx_map, my_dia_id, target_dia_id)
            if turns < 0:
                continue
            if c.min_turns is not None and turns < c.min_turns:
                return False, (
                    f"Evidence「{ev.id}」要求与「{target_id}」至少间隔 {c.min_turns} turns，"
                    f"实际 {turns}"
                )
            if c.max_turns is not None and turns > c.max_turns:
                return False, (
                    f"Evidence「{ev.id}」要求与「{target_id}」至多间隔 {c.max_turns} turns，"
                    f"实际 {turns}"
                )

    return True, None


# ── 主函数 ─────────────────────────────────────────────────────────────────

def assign_positions(
    sample_idx: int,
    protagonist: str,
    evidences: List[Evidence],
) -> Tuple[bool, Optional[List[dict]], Optional[str]]:
    """
    完备 CSP 分配算法。
    输入的 evidences 已按 order 排序，其中可能混合 fixed（已有位置）和 draft evidence。
    返回 (success, assignments, error)
    """
    if not evidences:
        return True, [], None

    # ── 构建 lookup table（一次性）────────────────────────────────────────────
    idx_map = _build_dia_index_map(sample_idx)

    # ── 构建 EvidenceSlot 列表 ──────────────────────────────────────────────
    ev_slots: List[EvidenceSlot] = []
    for ev in evidences:
        order = ev.queries[0].order if ev.queries else 0
        speaker = ev.speaker or protagonist
        status = "fixed" if ev.status in ("positioned", "polished") else "draft"

        msg_index = None
        session_key = None
        target_dia_id = ev.target_dia_id

        if status == "fixed" and ev.target_dia_id:
            msg_index = idx_map.get(ev.target_dia_id)
            msg = loader.get_message_by_dia_id(sample_idx, ev.target_dia_id)
            session_key = msg["session_key"] if msg else None

        ev_slots.append(EvidenceSlot(
            evidence_id=ev.id,
            status=status,
            target_dia_id=target_dia_id,
            session_key=session_key,
            msg_index=msg_index,
            speaker=speaker,
            order=order,
            explicit_constraints=ev.constraints,
        ))

    # ── 推导隐式约束 ─────────────────────────────────────────────────────────
    implicit_map = _derive_implicit_constraints(evidences)
    for slot in ev_slots:
        slot.implicit_constraints = implicit_map.get(slot.evidence_id, [])

    slot_map = {s.evidence_id: s for s in ev_slots}

    # ── Phase 1: 前置验证 ───────────────────────────────────────────────────
    err = _pre_validate_fixed_order(ev_slots)
    if err:
        return False, None, err

    err = _pre_validate_fixed_constraints(ev_slots, idx_map)
    if err:
        return False, None, err

    # ── Phase 2: 回溯搜索 ────────────────────────────────────────────────────
    draft_slots = [s for s in ev_slots if s.status == "draft"]

    fixed_indices = [s.msg_index for s in ev_slots if s.status == "fixed" and s.msg_index is not None]
    initial_last_index = max(fixed_indices) if fixed_indices else -1

    solved, assignment, err = _backtrack(
        ev_slots=ev_slots,
        draft_slots=draft_slots,
        slot_map=slot_map,
        sample_idx=sample_idx,
        protagonist=protagonist,
        assigned={},
        last_assigned_index=initial_last_index,
        idx_map=idx_map,
    )

    if not solved:
        return False, None, err

    # ── 构建结果 ─────────────────────────────────────────────────────────────
    result = []
    for slot in ev_slots:
        if slot.status == "fixed":
            dia_id = slot.target_dia_id
        else:
            dia_id = assignment[slot.evidence_id]

        msg = loader.get_message_by_dia_id(sample_idx, dia_id)
        result.append({
            "evidence_id": slot.evidence_id,
            "target_dia_id": dia_id,
            "session_key": msg["session_key"],
            "original_text": msg["text"],
        })

    # ── 防御性最终验证 ───────────────────────────────────────────────────────
    valid, error = _validate_constraints(
        evidences,
        {r["evidence_id"]: r for r in result},
        idx_map,
    )
    if not valid:
        return False, None, error

    return True, result, None
