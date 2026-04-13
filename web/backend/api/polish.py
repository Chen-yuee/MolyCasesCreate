from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from ..data_store import store
from ..data_loader import loader
from ..llm_client import llm_client
from ..models import PolishedMessage

router = APIRouter(tags=["polish"])


class PolishTextBody(BaseModel):
    polished_text: str


class BatchPolishBody(BaseModel):
    evidence_ids: Optional[List[str]] = None  # 要润色的 evidence IDs，None 表示所有 positioned 的


@router.get("/api/queries/{qid}/polished_messages")
def get_polished_messages(qid: str):
    """获取 Query 下所有润色后的消息"""
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")

    # 收集该 query 所有 evidence 的 target_dia_id
    dia_ids = set(e.target_dia_id for e in q.evidences if e.target_dia_id)

    results = []
    for dia_id in dia_ids:
        polished_msg = store.get_polished_message(q.sample_id, dia_id)
        if polished_msg:
            results.append({
                "dia_id": dia_id,
                "original_text": polished_msg.original_text,
                "final_polished_text": polished_msg.final_polished_text,
                "evidence_items": polished_msg.evidence_items,
                "updated_at": polished_msg.updated_at
            })

    return {"polished_messages": results}


@router.post("/api/queries/{qid}/polish")
def batch_polish(qid: str, body: BatchPolishBody = None):
    """批量润色 Query 下指定的 evidence"""
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")

    # 确定要润色的 evidence IDs
    if body and body.evidence_ids:
        to_polish_ids = set(body.evidence_ids)
        to_polish = [e for e in q.evidences if e.id in to_polish_ids]
    else:
        # 默认：所有 positioned 状态的
        to_polish = [e for e in q.evidences if e.status == "positioned" and e.target_dia_id]

    if not to_polish:
        raise HTTPException(status_code=400, detail="没有要润色的 evidence")

    # 对每个 evidence 调用 repolish
    results = []
    for ev in to_polish:
        try:
            result = repolish(ev.id)
            results.append(result)
        except Exception as e:
            results.append({
                "evidence_id": ev.id,
                "error": str(e)
            })

    return {"results": results}


@router.post("/api/evidences/{eid}/repolish")
def repolish(eid: str):
    """重新润色单条 evidence"""
    ev = store.get_evidence(eid)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not ev.target_dia_id:
        raise HTTPException(status_code=400, detail="该 evidence 尚未分配插入位置")

    q = store.get_query(ev.query_id)

    # 获取或创建该消息的 PolishedMessage
    polished_msg = store.get_polished_message(q.sample_id, ev.target_dia_id)
    if not polished_msg:
        # 首次润色：创建 PolishedMessage
        ctx = loader.get_context_window(q.sample_id, ev.target_dia_id, window=3)
        if not ctx:
            raise HTTPException(status_code=400, detail="无法获取上下文")
        original = ctx["context"][ctx["target_index"]]["text"]
        polished_msg = PolishedMessage(
            sample_id=q.sample_id,
            dia_id=ev.target_dia_id,
            session_key=ev.session_key,
            original_text=original,
            final_polished_text=original,
            evidence_items=[],
            updated_at=datetime.now().isoformat()
        )

    # 收集该消息关联的所有 evidences
    all_evidences = []
    for item in polished_msg.evidence_items:
        evidence = store.get_evidence(item["evidence"]["id"])
        if evidence:
            all_evidences.append(evidence)

    # 添加本次申请润色的 evidence（如果不在列表中）
    if ev.id not in [e.id for e in all_evidences]:
        all_evidences.append(ev)

    # 按 (query_id, order) 排序
    all_evidences.sort(key=lambda e: (e.query_id, e.order))

    # 获取上下文
    ctx = loader.get_context_window(q.sample_id, ev.target_dia_id, window=3)
    if not ctx:
        raise HTTPException(status_code=400, detail="无法获取上下文")

    # 准备已润色的 evidence 列表（不包括当前要润色的）
    already_polished = [e.content for e in all_evidences if e.id != ev.id]

    # 一次性调用 LLM，传入当前 evidence 和已润色的列表
    polished = llm_client.polish(
        evidence=ev.content,
        original_text=polished_msg.original_text,
        context=ctx["context"],
        target_index=ctx["target_index"],
        speaker=q.protagonist,
        already_polished=already_polished
    )

    # 更新所有 evidence 的状态和 evidence_items
    new_evidence_items = []
    for current_ev in all_evidences:
        current_ev.status = "polished"
        store.update_evidence(current_ev)

        ev_query = store.get_query(current_ev.query_id)
        if ev_query:
            new_evidence_items.append({
                "query": {
                    "id": current_ev.query_id,
                    "text": ev_query.query_text
                },
                "evidence": {
                    "id": current_ev.id,
                    "content": current_ev.content
                }
            })

    base_text = polished

    # 保存最终润色结果
    polished_msg.final_polished_text = base_text
    polished_msg.evidence_items = new_evidence_items
    polished_msg.updated_at = datetime.now().isoformat()
    store.update_polished_message(polished_msg)

    return {
        "dia_id": ev.target_dia_id,
        "original_text": polished_msg.original_text,
        "final_polished_text": polished_msg.final_polished_text,
        "evidence_count": len(polished_msg.evidence_items)
    }


@router.put("/api/evidences/{eid}/polish_text")
def set_polish_text(eid: str, body: PolishTextBody):
    """手动编辑润色结果"""
    ev = store.get_evidence(eid)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not ev.target_dia_id:
        raise HTTPException(status_code=400, detail="该 evidence 尚未分配插入位置")

    # 获取或创建 PolishedMessage
    polished_msg = store.get_polished_message(ev.query_id, ev.target_dia_id)
    if not polished_msg:
        q = store.get_query(ev.query_id)
        ctx = loader.get_context_window(q.sample_id, ev.target_dia_id, window=3)
        if not ctx:
            raise HTTPException(status_code=400, detail="无法获取上下文")
        original = ctx["context"][ctx["target_index"]]["text"]
        polished_msg = PolishedMessage(
            query_id=ev.query_id,
            sample_id=q.sample_id,
            dia_id=ev.target_dia_id,
            session_key=ev.session_key,
            original_text=original,
            final_polished_text=body.polished_text,
            evidence_ids=[ev.id],
            updated_at=datetime.now().isoformat()
        )
    else:
        polished_msg.final_polished_text = body.polished_text
        polished_msg.updated_at = datetime.now().isoformat()
        if ev.id not in polished_msg.evidence_ids:
            polished_msg.evidence_ids.append(ev.id)

    ev.status = "confirmed"
    store.update_evidence(ev)
    store.update_polished_message(polished_msg)

    return {
        "dia_id": ev.target_dia_id,
        "original_text": polished_msg.original_text,
        "final_polished_text": polished_msg.final_polished_text
    }
