from fastapi import APIRouter, HTTPException
from ..data_loader import loader
from ..data_store import store

router = APIRouter(prefix="/api/samples", tags=["samples"])


@router.get("")
def list_samples():
    """获取所有 dialog 列表，包含每个 dialog 下的 query 列表"""
    samples = loader.get_samples_info()
    queries = store.get_queries()

    # 按 sample_id 分组 query
    for sample in samples:
        sample["queries"] = [
            {
                "id": q.id,
                "query_text": q.query_text,
                "protagonist": q.protagonist,
                "status": q.status,
                "evidence_count": len(q.evidences),
            }
            for q in queries if q.sample_id == sample["index"]
        ]

    return samples


@router.get("/{index}/conversation")
def get_conversation(index: int):
    """获取对话内容，每条消息附带被哪些 query/evidence 影响"""
    msgs = loader.get_all_messages(index)
    if not msgs:
        raise HTTPException(status_code=404, detail="Sample not found")

    # 获取该 sample 的所有 query
    queries = [q for q in store.get_queries() if q.sample_id == index]

    # 为每条消息附加 evidence 信息和润色结果
    for msg in msgs:
        msg["evidences"] = []
        msg["polished_text"] = None

        # 检查是否有 PolishedMessage（使用 sample_id）
        polished_msg = store.get_polished_message(index, msg["dia_id"])
        if polished_msg:
            msg["polished_text"] = polished_msg.final_polished_text

        for q in queries:
            # 附加 evidence 信息
            for ev in q.evidences:
                if ev.target_dia_id == msg["dia_id"]:
                    msg["evidences"].append({
                        "query_id": q.id,
                        "query_text": q.query_text,
                        "evidence_id": ev.id,
                        "evidence_content": ev.content,
                        "status": ev.status,
                    })

    return msgs


@router.get("/{index}/speakers")
def get_speakers(index: int):
    sample = loader.get_sample(index)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    conv = sample["conversation"]
    return {"speaker_a": conv["speaker_a"], "speaker_b": conv["speaker_b"]}
