import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from ..data_store import store
from ..models import Evidence, EvidenceCreate, EvidenceUpdate
from ..config import classify_evidence

router = APIRouter(tags=["evidences"])


@router.get("/api/queries/{qid}/evidences")
def list_evidences(qid: str):
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    return q.evidences


@router.post("/api/queries/{qid}/evidences")
def create_evidence(qid: str, body: EvidenceCreate):
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    # 自动分配 order（最大值 + 1）
    max_order = max([e.order for e in q.evidences], default=-1)
    ev = Evidence(
        id=str(uuid.uuid4()),
        query_id=qid,
        content=body.content,
        type=classify_evidence(body.content),
        speaker=body.speaker,
        order=body.order if body.order is not None else max_order + 1,
        constraints=body.constraints or [],
        status="draft",
        created_at=datetime.now().isoformat(),
    )
    return store.add_evidence(qid, ev)


@router.put("/api/evidences/{eid}")
def update_evidence(eid: str, body: EvidenceUpdate):
    ev = store.get_evidence(eid)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if body.content is not None:
        ev.content = body.content
        ev.type = classify_evidence(body.content)
    if body.speaker is not None:
        ev.speaker = body.speaker
    if body.order is not None:
        ev.order = body.order
    if body.constraints is not None:
        ev.constraints = body.constraints
    return store.update_evidence(ev)


@router.delete("/api/evidences/{eid}")
def delete_evidence(eid: str):
    if not store.delete_evidence(eid):
        raise HTTPException(status_code=404, detail="Evidence not found")
    return {"ok": True}


@router.post("/api/evidences/{eid}/unpolish")
def unpolish_evidence(eid: str):
    """撤销指定 evidence 的润色，重新累积润色该消息"""
    from ..llm_client import llm_client
    from ..data_loader import loader

    ev = store.get_evidence(eid)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not ev.target_dia_id:
        raise HTTPException(status_code=400, detail="该 evidence 没有分配位置")

    q = store.get_query(ev.query_id)

    # 获取该消息的 PolishedMessage（使用 sample_id）
    polished_msg = store.get_polished_message(q.sample_id, ev.target_dia_id)
    if not polished_msg:
        raise HTTPException(status_code=400, detail="该消息没有润色结果")

    # 移除该 evidence 的关联
    polished_msg.evidence_items = [
        item for item in polished_msg.evidence_items
        if item["evidence"]["id"] != ev.id
    ]

    # 重置 evidence 状态
    ev.target_dia_id = None
    ev.session_key = None
    ev.status = "draft"
    store.update_evidence(ev)

    # 重新累积润色剩余的 evidences
    if not polished_msg.evidence_items:
        # 没有其他 evidence 了，删除 PolishedMessage
        store.delete_polished_message(q.sample_id, polished_msg.dia_id)
        return {
            "evidence_id": ev.id,
            "message": "已撤销润色，恢复原文"
        }
    else:
        # 使用大模型直接去除指定润色，保留其他润色结果
        other_evidences = []
        for item in polished_msg.evidence_items:
            current_ev = store.get_evidence(item["evidence"]["id"])
            if current_ev:
                other_evidences.append(current_ev.content)

        polished = llm_client.unpolish(
            original_text=polished_msg.original_text,
            polished_text=polished_msg.final_polished_text,
            evidence_to_remove=ev.content,
            other_evidences=other_evidences
        )

        polished_msg.final_polished_text = polished
        polished_msg.updated_at = datetime.now().isoformat()
        store.update_polished_message(polished_msg)

        return {
            "evidence_id": ev.id,
            "final_polished_text": polished_msg.final_polished_text,
            "message": "已成功去润色，保留其余润色内容"
        }
