import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from ..data_store import store
from ..models import Query, QueryCreate, QueryUpdate

router = APIRouter(prefix="/api/queries", tags=["queries"])


@router.get("")
def list_queries():
    return store.get_queries()


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
    return q


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
