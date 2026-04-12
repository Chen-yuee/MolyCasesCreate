import json
import copy
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from ..data_store import store
from ..data_loader import loader

router = APIRouter(tags=["export"])


@router.post("/api/export/{qid}")
def export_query(qid: str):
    """导出某个 query 对应的修改后 sample JSON"""
    q = store.get_query(qid)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")

    confirmed = [e for e in q.evidences if e.status == "confirmed" and e.target_dia_id]
    if not confirmed:
        raise HTTPException(status_code=400, detail="没有已确认的 evidence 可以导出")

    # 深拷贝原始 sample
    sample = loader.get_sample(q.sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    modified = copy.deepcopy(sample)

    # 获取所有 PolishedMessage，应用润色结果
    polished_messages = store.get_polished_messages_by_query(qid)
    polish_map = {m.dia_id: m.final_polished_text for m in polished_messages}

    conv = modified["conversation"]
    for key, val in conv.items():
        if not key.startswith("session_") or key.endswith("_date_time"):
            continue
        if not isinstance(val, list):
            continue
        for msg in val:
            if msg["dia_id"] in polish_map:
                msg["text"] = polish_map[msg["dia_id"]]

    # 添加 metadata
    output = {
        "metadata": {
            "query_id": q.id,
            "query_text": q.query_text,
            "sample_id": q.sample_id,
            "protagonist": q.protagonist,
            "exported_at": datetime.now().isoformat(),
            "insertions": [
                {
                    "evidence_id": e.id,
                    "content": e.content,
                    "type": e.type,
                    "target_dia_id": e.target_dia_id,
                }
                for e in confirmed
            ],
            "polished_messages": [
                {
                    "dia_id": m.dia_id,
                    "original_text": m.original_text,
                    "final_polished_text": m.final_polished_text,
                    "evidence_count": len(m.evidence_ids)
                }
                for m in polished_messages
            ]
        },
        "modified_sample": modified,
    }

    return JSONResponse(
        content=output,
        headers={
            "Content-Disposition": f'attachment; filename="query_{qid[:8]}_sample_{q.sample_id}.json"'
        },
    )
