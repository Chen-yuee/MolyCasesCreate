from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..data_store import store
from ..data_loader import loader
from ..inserter import assign_positions

router = APIRouter(tags=["insertion"])


class ManualPositionBody(BaseModel):
    target_dia_id: str


@router.post("/api/queries/{qid}/assign")
def auto_assign(qid: str):
    """为 Query 下所有 draft evidence 自动分配插入位置（按 order 排序）"""
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    if not q.evidences:
        raise HTTPException(status_code=400, detail="该 Query 下没有 Evidence")

    # 只处理 draft 状态的，按 order 排序
    to_assign = sorted([e for e in q.evidences if e.status == "draft"], key=lambda e: e.order)
    if not to_assign:
        return {"success": True, "assignments": [], "message": "没有需要分配位置的 evidence"}

    success, assignments, error = assign_positions(q.sample_id, q.protagonist, to_assign)
    if not success:
        raise HTTPException(status_code=422, detail=error)

    # 保存结果
    assign_map = {a["evidence_id"]: a for a in assignments}
    for ev in to_assign:
        if ev.id in assign_map:
            a = assign_map[ev.id]
            ev.target_dia_id = a["target_dia_id"]
            ev.session_key = a["session_key"]
            ev.status = "positioned"
            store.update_evidence(ev)

    return {"success": True, "assignments": assignments}


@router.post("/api/queries/{qid}/preview-assign")
def preview_assign(qid: str):
    """预览自动分配结果，不改变 evidence 状态"""
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    if not q.evidences:
        raise HTTPException(status_code=400, detail="该 Query 下没有 Evidence")

    # 处理所有 evidence，按 order 排序
    to_assign = sorted(q.evidences, key=lambda e: e.order)
    if not to_assign:
        return {"success": True, "assignments": [], "message": "没有 evidence"}

    success, assignments, error = assign_positions(q.sample_id, q.protagonist, to_assign)
    if not success:
        raise HTTPException(status_code=422, detail=error)

    return {"success": True, "assignments": assignments}


@router.put("/api/evidences/{eid}/position")
def manual_position(eid: str, body: ManualPositionBody):
    """手动设置 evidence 的插入位置"""
    ev = store.get_evidence(eid)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    q = store.get_query(ev.query_id)
    msg = loader.get_message_by_dia_id(q.sample_id, body.target_dia_id)
    if not msg:
        raise HTTPException(status_code=400, detail=f"dia_id {body.target_dia_id} 在该样本中不存在")
    ev.target_dia_id = body.target_dia_id
    ev.session_key = msg["session_key"]
    ev.status = "positioned"
    return store.update_evidence(ev)
