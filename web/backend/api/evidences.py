import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from ..data_store import store
from ..models import Evidence, EvidenceCreate, EvidenceUpdate, EvidenceQueryRef

router = APIRouter(tags=["evidences"])


@router.get("/api/queries/{qid}/evidences")
def list_evidences(qid: str):
    """返回该 query 关联的所有 evidence 对象（按 order 排序）。"""
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    # q.evidences 是 ID 列表，需要从 _evidences 中取出对象并按 order 排序
    evidences = [store.get_evidence(eid) for eid in q.evidences]
    return sorted([e for e in evidences if e is not None], key=lambda e: e.queries[0].order if e.queries else 0)


@router.post("/api/queries/{qid}/evidences")
def create_evidence(qid: str, body: EvidenceCreate):
    """创建新的 evidence 并关联到指定 query。"""
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")

    # 自动分配 order（取当前最大值 + 1）
    # 最大 order 从已有 evidence 的 queries[0].order 取得
    max_order = max(
        (store.get_evidence(eid).queries[0].order for eid in q.evidences if store.get_evidence(eid) and store.get_evidence(eid).queries),
        default=-1
    )
    order_val = body.order if body.order is not None else max_order + 1
    ev = Evidence(
        id=str(uuid.uuid4()),
        content=body.content,
        speaker=body.speaker,
        constraints=body.constraints or [],
        status="draft",
        created_at=datetime.now().isoformat(),
    )
    ev.queries = [EvidenceQueryRef(id=qid, order=order_val)]
    return store.add_evidence(qid, ev)


@router.put("/api/evidences/{eid}")
def update_evidence(eid: str, body: EvidenceUpdate):
    """更新 evidence 内容。"""
    ev = store.get_evidence(eid)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if body.content is not None:
        ev.content = body.content
    if body.speaker is not None:
        ev.speaker = body.speaker
    if body.order is not None:
        # 更新 queries 中的 order（通常 evidence 只属于一个 query）
        for ref in ev.queries:
            ref.order = body.order
    if body.constraints is not None:
        ev.constraints = body.constraints
    return store.update_evidence(ev)


@router.delete("/api/evidences/{eid}")
def delete_evidence(eid: str):
    """删除 evidence（会同步清理关联的 query 和 polished_message）。"""
    if not store.delete_evidence(eid):
        raise HTTPException(status_code=404, detail="Evidence not found")
    return {"ok": True}


@router.post("/api/evidences/{eid}/unpolish")
def unpolish_evidence(eid: str):
    """撤销指定 evidence 的润色，从 PolishedMessage 中移除并重新去润色。"""
    from ..llm_client import llm_client

    ev = store.get_evidence(eid)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not ev.target_dia_id:
        raise HTTPException(status_code=400, detail="该 evidence 没有分配位置")

    # 从 evidence.queries 获取关联的 query
    if not ev.queries:
        raise HTTPException(status_code=400, detail="该 evidence 未关联任何 query")
    q = store.get_query(ev.queries[0].id)
    if not q:
        raise HTTPException(status_code=404, detail="关联的 Query 不存在")

    # 获取该消息的 PolishedMessage
    polished_msg = store.get_polished_message(q.sample_id, ev.target_dia_id)
    if not polished_msg:
        raise HTTPException(status_code=400, detail="该消息没有润色结果")

    # 移除该 evidence 的关联
    polished_msg.evidence_items = [
        item for item in polished_msg.evidence_items
        if item["evidence"]["id"] != ev.id
    ]

    # 重置 evidence 状态为 positioned，保留位置信息
    ev.status = "positioned"
    store.update_evidence(ev)

    if not polished_msg.evidence_items:
        # 没有其他 evidence 了，删除 PolishedMessage
        store.delete_polished_message(q.sample_id, polished_msg.dia_id)
        return {"evidence_id": ev.id, "message": "已撤销润色，恢复原文"}
    else:
        # 还有其他 evidence，调用 LLM 去除当前 evidence 的润色
        other_contents = []
        for item in polished_msg.evidence_items:
            cur = store.get_evidence(item["evidence"]["id"])
            if cur:
                other_contents.append(cur.content)

        polished = llm_client.unpolish(
            original_text=polished_msg.original_text,
            polished_text=polished_msg.final_polished_text,
            evidence_to_remove=ev.content,
            other_evidences=other_contents,
        )

        polished_msg.final_polished_text = polished
        polished_msg.updated_at = datetime.now().isoformat()
        store.update_polished_message(polished_msg)

        return {
            "evidence_id": ev.id,
            "final_polished_text": polished_msg.final_polished_text,
            "message": "已成功去润色，保留其余润色内容"
        }
