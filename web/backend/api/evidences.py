import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from ..data_store import store
from ..models import Evidence, EvidenceCreate, EvidenceUpdate, EvidenceQueryRef
from ..logger import get_logger

logger = get_logger("api.evidences")

router = APIRouter(tags=["evidences"])


@router.get("/api/evidences")
def list_all_evidences():
    """返回所有 evidence 对象列表。"""
    return store.list_evidences()


@router.get("/api/queries/{qid}/evidences")
def list_evidences(qid: str):
    """返回该 query 关联的所有 evidence 对象（按 query.evidences 列表顺序）。"""
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    # q.evidences 是 ID 列表，按列表顺序返回对象
    evidences = [store.get_evidence(eid) for eid in q.evidences]
    return [e for e in evidences if e is not None]


@router.post("/api/evidences/{eid}/attach")
def attach_evidence_to_query(eid: str, qid: str):
    """将已有的 evidence 关联到另一个 query。"""
    ev = store.get_evidence(eid)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")

    # 检查是否已关联该 query
    if any(ref.id == qid for ref in ev.queries):
        raise HTTPException(status_code=400, detail="该 evidence 已关联此 query")

    # 添加 query 引用（不需要 order）
    ev.queries.append(EvidenceQueryRef(id=qid))
    store.update_evidence(ev)

    # 在 query.evidences 中也追加该 evidence ID
    if eid not in q.evidences:
        q.evidences.append(eid)
        store.update_query(q)

    return ev


@router.post("/api/queries/{qid}/evidences")
def create_evidence(qid: str, body: EvidenceCreate):
    """创建新的 evidence 并关联到指定 query。"""
    logger.info(f"创建 evidence - qid: {qid}, speaker: {body.speaker}")
    q = store.get_query(qid)
    if not q:
        logger.error(f"Query 未找到 - qid: {qid}")
        raise HTTPException(status_code=404, detail="Query not found")

    ev = Evidence(
        id=str(uuid.uuid4()),
        content=body.content,
        speaker=body.speaker,
        constraints=body.constraints or [],
        status="draft",
        created_at=datetime.now().isoformat(),
    )
    ev.queries = [EvidenceQueryRef(id=qid)]
    result = store.add_evidence(qid, ev)
    logger.info(f"Evidence 创建成功 - id: {ev.id}")
    return result


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
    if body.constraints is not None:
        ev.constraints = body.constraints
    return store.update_evidence(ev)


@router.delete("/api/evidences/{eid}")
def delete_evidence(eid: str):
    """删除 evidence（会同步清理关联的 query 和 polished_message）。"""
    logger.info(f"删除 evidence - eid: {eid}")
    if not store.delete_evidence(eid):
        logger.error(f"Evidence 未找到 - eid: {eid}")
        raise HTTPException(status_code=404, detail="Evidence not found")
    logger.info(f"Evidence 删除成功 - eid: {eid}")
    return {"ok": True}


@router.post("/api/evidences/{eid}/unpolish")
def unpolish_evidence(eid: str):
    """撤销指定 evidence 的润色，从 PolishedMessage 中移除并重新去润色。"""
    from ..llm_client import llm_client

    logger.info(f"撤销润色 - eid: {eid}")
    ev = store.get_evidence(eid)
    if not ev:
        logger.error(f"Evidence 未找到 - eid: {eid}")
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not ev.target_dia_id:
        logger.error(f"Evidence 没有分配位置 - eid: {eid}")
        raise HTTPException(status_code=400, detail="该 evidence 没有分配位置")

    # 从 evidence.queries 获取关联的 query
    if not ev.queries:
        logger.error(f"Evidence 未关联任何 query - eid: {eid}")
        raise HTTPException(status_code=400, detail="该 evidence 未关联任何 query")
    q = store.get_query(ev.queries[0].id)
    if not q:
        logger.error(f"关联的 Query 不存在 - qid: {ev.queries[0].id}")
        raise HTTPException(status_code=404, detail="关联的 Query 不存在")

    # 获取该消息的 PolishedMessage
    polished_msg = store.get_polished_message(q.sample_id, ev.target_dia_id)
    if not polished_msg:
        logger.error(f"该消息没有润色结果 - sample_id: {q.sample_id}, dia_id: {ev.target_dia_id}")
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
        logger.info(f"删除 PolishedMessage - sample_id: {q.sample_id}, dia_id: {polished_msg.dia_id}")
        store.delete_polished_message(q.sample_id, polished_msg.dia_id)
        return {"evidence_id": ev.id, "message": "已撤销润色，恢复原文"}
    else:
        # 还有其他 evidence，调用 LLM 去除当前 evidence 的润色
        logger.info(f"调用 LLM 去除润色 - eid: {eid}")
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
        logger.info(f"去润色成功 - eid: {eid}")

        return {
            "evidence_id": ev.id,
            "final_polished_text": polished_msg.final_polished_text,
            "message": "已成功去润色，保留其余润色内容"
        }
