from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from ..data_store import store
from ..data_loader import loader
from ..inserter import assign_positions
from .. import manual_inserter
from ..logger import get_logger

logger = get_logger("api.insertion")

router = APIRouter(tags=["insertion"])


class ManualPositionBody(BaseModel):
    target_dia_id: str


class ManualAssignBody(BaseModel):
    assignments: List[dict]  # [{"evidence_id": str, "target_dia_id": str}, ...]

# 这个api有问题
# @router.post("/api/queries/{qid}/assign")
# def auto_assign(qid: str):
    # 这个函数有问题，先注释掉
    # """为 Query 下所有 draft evidence 自动分配插入位置（按 order 排序）"""
    # q = store.get_query(qid)
    # if not q:
    #     raise HTTPException(status_code=404, detail="Query not found")
    # if not q.evidences:
    #     raise HTTPException(status_code=400, detail="该 Query 下没有 Evidence")

    # # 从 evidence IDs 获取实际的 Evidence 对象，按 order 排序
    # evidences = [store.get_evidence(eid) for eid in q.evidences]
    # evidences = [e for e in evidences if e is not None]
    # ordered_evidences = sorted(evidences, key=lambda e: e.queries[0].order if e.queries else 0)
    # draft_evidences = [e for e in ordered_evidences if e.status == "draft"]
    # if not draft_evidences:
    #     return {"success": True, "assignments": [], "message": "没有需要分配位置的 draft evidence"}

    # success, assignments, error = assign_positions(q.sample_id, q.protagonist, ordered_evidences)
    # if not success:
    #     raise HTTPException(status_code=422, detail=error)

    # # 只更新 draft evidence 的分配结果，fixed evidence 保持不变
    # assign_map = {a["evidence_id"]: a for a in assignments}
    # for ev in draft_evidences:
    #     if ev.id in assign_map:
    #         a = assign_map[ev.id]
    #         ev.target_dia_id = a["target_dia_id"]
    #         ev.session_key = a["session_key"]
    #         ev.status = "positioned"
    #         store.update_evidence(ev)

    # return {"success": True, "assignments": assignments}

# 这个api有问题，先注释掉
# @router.post("/api/queries/{qid}/preview-assign")
# def preview_assign(qid: str):
    # """预览自动分配结果，不改变 evidence 状态"""
    # q = store.get_query(qid)
    # if not q:
    #     raise HTTPException(status_code=404, detail="Query not found")
    # if not q.evidences:
    #     raise HTTPException(status_code=400, detail="该 Query 下没有 Evidence")

    # # 从 evidence IDs 获取对象，按 order 排序
    # evidences = [store.get_evidence(eid) for eid in q.evidences]
    # evidences = [e for e in evidences if e is not None]
    # ordered_evidences = sorted(evidences, key=lambda e: e.queries[0].order if e.queries else 0)
    # if not ordered_evidences:
    #     return {"success": True, "assignments": [], "message": "没有 evidence"}

    # success, assignments, error = assign_positions(q.sample_id, q.protagonist, ordered_evidences)
    # if not success:
    #     raise HTTPException(status_code=422, detail=error)

    # return {"success": True, "assignments": assignments}

# 这个api有问题，先注释掉
# @router.put("/api/evidences/{eid}/position")
# def manual_position(eid: str, body: ManualPositionBody):
    # """手动设置 evidence 的插入位置"""
    # ev = store.get_evidence(eid)
    # if not ev:
    #     raise HTTPException(status_code=404, detail="Evidence not found")

    # # 从 evidence.queries 获取关联的 query
    # if not ev.queries:
    #     raise HTTPException(status_code=400, detail="该 evidence 未关联任何 query")
    # q = store.get_query(ev.queries[0].id)
    # if not q:
    #     raise HTTPException(status_code=404, detail="关联的 Query 不存在")

    # msg = loader.get_message_by_dia_id(q.sample_id, body.target_dia_id)
    # if not msg:
    #     raise HTTPException(status_code=400, detail=f"dia_id {body.target_dia_id} 在该样本中不存在")

    # ev.target_dia_id = body.target_dia_id
    # ev.session_key = msg["session_key"]
    # ev.status = "positioned"
    # return store.update_evidence(ev)


@router.post("/api/queries/{qid}/manual-assign")
def manual_assign(qid: str, body: ManualAssignBody):
    """
    手动分配 evidence 位置。
    已润色的 evidence 会先减退再分配位置。
    """
    logger.info(f"收到手动分配请求 - qid: {qid}, assignments: {len(body.assignments)}")
    result = manual_inserter.apply_manual_positions(qid, body.assignments)
    if not result.get("success"):
        logger.error(f"手动分配失败 - qid: {qid}, error: {result.get('error')}")
        raise HTTPException(status_code=400, detail=result.get("error"))
    logger.info(f"手动分配成功 - qid: {qid}, result: {result}")
    return result
