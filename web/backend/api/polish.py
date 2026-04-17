from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from ..data_store import store
from ..data_loader import loader
from ..llm_client import llm_client
from ..models import PolishedMessage
from ..logger import get_logger

logger = get_logger("api.polish")

router = APIRouter(tags=["polish"])


class PolishTextBody(BaseModel):
    polished_text: str


class BatchPolishBody(BaseModel):
    evidence_ids: Optional[List[str]] = None  # 要润色的 evidence IDs，None 表示所有 positioned 的


@router.get("/api/queries/{qid}/polished_messages")
def get_polished_messages(qid: str):
    """获取 Query 下所有润色后的消息。"""
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")

    # q.evidences 是 ID 列表，获取每条 evidence 的 target_dia_id
    dia_ids = set()
    for eid in q.evidences:
        ev = store.get_evidence(eid)
        if ev and ev.target_dia_id:
            dia_ids.add(ev.target_dia_id)

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
    """批量润色 Query 下指定的 evidence。"""
    logger.info(f"批量润色开始 - qid: {qid}")
    q = store.get_query(qid)
    if not q:
        logger.error(f"Query 未找到 - qid: {qid}")
        raise HTTPException(status_code=404, detail="Query not found")

    # 从 evidence IDs 获取对象，确定要润色的
    all_evidences = [store.get_evidence(eid) for eid in q.evidences]
    all_evidences = [e for e in all_evidences if e is not None]

    if body and body.evidence_ids:
        to_polish_ids = set(body.evidence_ids)
        to_polish = [e for e in all_evidences if e.id in to_polish_ids]
    else:
        # 默认：所有 positioned 状态且有 target_dia_id 的
        to_polish = [e for e in all_evidences if e.status == "positioned" and e.target_dia_id]

    if not to_polish:
        logger.warning(f"没有要润色的 evidence - qid: {qid}")
        raise HTTPException(status_code=400, detail="没有要润色的 evidence")

    logger.info(f"开始润色 {len(to_polish)} 个 evidence")
    results = []
    for ev in to_polish:
        try:
            result = repolish(ev.id)
            results.append(result)
        except Exception as e:
            logger.error(f"润色失败 - evidence_id: {ev.id}, error: {str(e)}")
            results.append({"evidence_id": ev.id, "error": str(e)})

    logger.info(f"批量润色完成 - qid: {qid}, 成功: {len([r for r in results if 'error' not in r])}")
    return {"results": results}


@router.post("/api/evidences/{eid}/repolish")
def repolish(eid: str):
    """
    重新润色单条 evidence。
    一次性收集该消息所有关联的 evidence
    """
    logger.info(f"重新润色 - eid: {eid}")
    ev = store.get_evidence(eid)
    if not ev:
        logger.error(f"Evidence 未找到 - eid: {eid}")
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not ev.target_dia_id:
        logger.error(f"Evidence 尚未分配插入位置 - eid: {eid}")
        raise HTTPException(status_code=400, detail="该 evidence 尚未分配插入位置")

    # 直接通过 dia_id 查找 PolishedMessage，不需要通过 query
    logger.debug(f"获取 PolishedMessage - dia_id: {ev.target_dia_id}")
    polished_msg = store.get_polished_message_by_dia_id(ev.target_dia_id)

    # 如果没有找到，需要获取 sample_id 来创建新的 PolishedMessage
    sample_id = None
    if not polished_msg:
        # 从关联的 query 获取 sample_id
        if not ev.queries:
            logger.error(f"Evidence 未关联任何 query，无法获取 sample_id - eid: {eid}")
            raise HTTPException(status_code=400, detail="该 evidence 未关联任何 query，无法创建润色消息")

        # 尝试从所有关联的 query 中找到一个有效的
        q = None
        for qRef in ev.queries:
            q = store.get_query(qRef.id)
            if q:
                break

        if not q:
            logger.error(f"所有关联的 Query 都不存在 - evidence_id: {eid}")
            raise HTTPException(status_code=404, detail="所有关联的 Query 都不存在")
        sample_id = q.sample_id

        # 创建新的 PolishedMessage
        logger.debug(f"首次润色，创建 PolishedMessage - sample_id: {sample_id}, dia_id: {ev.target_dia_id}")
        ctx = loader.get_context_window(sample_id, ev.target_dia_id, window=3)
        if not ctx:
            logger.error(f"无法获取上下文 - sample_id: {sample_id}, dia_id: {ev.target_dia_id}")
            raise HTTPException(status_code=400, detail="无法获取上下文")
        original = ctx["context"][ctx["target_index"]]["text"]
        polished_msg = PolishedMessage(
            sample_id=sample_id,
            dia_id=ev.target_dia_id,
            session_key=ev.session_key,
            original_text=original,
            final_polished_text=original,
            evidence_items=[],
            updated_at=datetime.now().isoformat()
        )
    else:
        sample_id = polished_msg.sample_id

    # 收集该消息关联的所有 evidence 对象
    all_evidences = []
    for item in polished_msg.evidence_items:
        evidence = store.get_evidence(item["evidence"]["id"])
        if evidence:
            all_evidences.append(evidence)

    # 添加本次申请润色的 evidence（如果不在列表中）
    if ev.id not in [e.id for e in all_evidences]:
        all_evidences.append(ev)

    logger.info(f"收集到 {len(all_evidences)} 个 evidence 进行润色")

    # 按 query_id 排序
    all_evidences.sort(key=lambda e: e.queries[0].id if e.queries else "")

    # 获取上下文
    ctx = loader.get_context_window(polished_msg.sample_id, ev.target_dia_id, window=3)
    if not ctx:
        logger.error(f"无法获取上下文 - sample_id: {polished_msg.sample_id}, dia_id: {ev.target_dia_id}")
        raise HTTPException(status_code=400, detail="无法获取上下文")

    # 准备已润色的 evidence 内容（不包括当前要润色的）
    already_polished = [e.content for e in all_evidences if e.id != ev.id]
    logger.debug(f"已润色的 evidence 数量: {len(already_polished)}")

    # 调用 LLM 整体润色
    logger.info(f"调用 LLM 润色 - eid: {eid}")
    polished = llm_client.polish(
        evidence=ev.content,
        original_text=polished_msg.original_text,
        context=ctx["context"],
        target_index=ctx["target_index"],
        speaker=ev.speaker,
        already_polished=already_polished
    )

    # 更新所有 evidence 的状态并构建 evidence_items
    new_evidence_items = []
    for current_ev in all_evidences:
        current_ev.status = "polished"
        store.update_evidence(current_ev)
        # evidence_items 中不再包含嵌套 query 对象
        new_evidence_items.append({
            "evidence": {
                "id": current_ev.id,
                "content": current_ev.content
            }
        })

    # 保存润色结果
    polished_msg.final_polished_text = polished
    polished_msg.evidence_items = new_evidence_items
    polished_msg.updated_at = datetime.now().isoformat()
    store.update_polished_message(polished_msg)

    logger.info(f"润色完成 - eid: {eid}, evidence_count: {len(polished_msg.evidence_items)}")

    return {
        "dia_id": ev.target_dia_id,
        "original_text": polished_msg.original_text,
        "final_polished_text": polished_msg.final_polished_text,
        "evidence_count": len(polished_msg.evidence_items)
    }


# @router.put("/api/evidences/{eid}/polish_text")
# def set_polish_text(eid: str, body: PolishTextBody):
#     """手动编辑润色结果。"""
#     ev = store.get_evidence(eid)
#     if not ev:
#         raise HTTPException(status_code=404, detail="Evidence not found")
#     if not ev.target_dia_id:
#         raise HTTPException(status_code=400, detail="该 evidence 尚未分配插入位置")

#     # 从 evidence.queries 获取关联 query
#     if not ev.queries:
#         raise HTTPException(status_code=400, detail="该 evidence 未关联任何 query")
#     q = store.get_query(ev.queries[0].id)
#     if not q:
#         raise HTTPException(status_code=404, detail="关联的 Query 不存在")

#     # 获取或创建 PolishedMessage
#     polished_msg = store.get_polished_message(q.sample_id, ev.target_dia_id)
#     if not polished_msg:
#         ctx = loader.get_context_window(q.sample_id, ev.target_dia_id, window=3)
#         if not ctx:
#             raise HTTPException(status_code=400, detail="无法获取上下文")
#         original = ctx["context"][ctx["target_index"]]["text"]
#         polished_msg = PolishedMessage(
#             sample_id=q.sample_id,
#             dia_id=ev.target_dia_id,
#             session_key=ev.session_key,
#             original_text=original,
#             final_polished_text=body.polished_text,
#             evidence_items=[{"evidence": {"id": ev.id, "content": ev.content}}],
#             updated_at=datetime.now().isoformat()
#         )
#     else:
#         polished_msg.final_polished_text = body.polished_text
#         polished_msg.updated_at = datetime.now().isoformat()
#         # 将该 evidence 加入 evidence_items（如果不在）
#         if not any(item["evidence"]["id"] == ev.id for item in polished_msg.evidence_items):
#             polished_msg.evidence_items.append({"evidence": {"id": ev.id, "content": ev.content}})

#     ev.status = "confirmed"
#     store.update_evidence(ev)
#     store.update_polished_message(polished_msg)

#     return {
#         "dia_id": ev.target_dia_id,
#         "original_text": polished_msg.original_text,
#         "final_polished_text": polished_msg.final_polished_text
#     }
