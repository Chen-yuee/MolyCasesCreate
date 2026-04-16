import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException
from ..data_store import store
from ..models import Query, QueryCreate, QueryUpdate, Evidence

router = APIRouter(prefix="/api/queries", tags=["queries"])


def _populate_evidences(query: Query) -> List[dict]:
    """
    将 query.evidences (ID列表) 转换为完整的 Evidence 对象列表
    按 query.evidences 列表顺序返回（列表索引即为顺序）
    """
    result = []
    for eid in query.evidences:
        ev = store.get_evidence(eid)
        if ev:
            result.append(ev.model_dump())
    return result


@router.get("")
def list_queries():
    queries = store.get_queries()
    # 填充完整 evidence 对象并转换为字典
    result = []
    for q in queries:
        q_dict = q.model_dump()
        q_dict['evidences'] = _populate_evidences(q)
        result.append(q_dict)
    return result


@router.post("")
def create_query(body: QueryCreate):
    query = Query(
        id=str(uuid.uuid4()),
        query_text=body.query_text,
        sample_id=body.sample_id,
        protagonist=body.protagonist,
        status="draft",
        created_at=datetime.now().isoformat(),
        evidences=[],
    )
    return store.create_query(query)


@router.get("/{qid}")
def get_query(qid: str):
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    # 填充完整 evidence 对象并转换为字典
    q_dict = q.model_dump()
    q_dict['evidences'] = _populate_evidences(q)
    return q_dict


@router.get("/{qid}/polished_messages")
def get_query_polished_messages(qid: str):
    """获取该 query 的所有 PolishedMessage"""
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    messages = store.get_polished_messages_by_query(qid)
    return messages


@router.put("/{qid}")
def update_query(qid: str, body: QueryUpdate):
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    if body.query_text is not None:
        q.query_text = body.query_text
    if body.sample_id is not None:
        q.sample_id = body.sample_id
    if body.protagonist is not None:
        q.protagonist = body.protagonist
    if body.status is not None:
        q.status = body.status
    return store.update_query(q)


@router.delete("/{qid}")
def delete_query(qid: str):
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    store.delete_query(qid)
    return {"ok": True}
