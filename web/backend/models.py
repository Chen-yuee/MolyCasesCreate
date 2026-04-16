from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class EvidenceConstraint(BaseModel):
    """Evidence 之间的约束"""
    target_evidence_id: str  # 约束的目标 evidence id
    same_session: Optional[bool] = None  # 是否必须在同一个 session
    min_turns: Optional[int] = None  # 最小间隔（消息数，不管谁说的）
    max_turns: Optional[int] = None  # 最大间隔


class EvidenceCreate(BaseModel):
    content: str
    speaker: Optional[str] = None  # 指定由谁说（主角或对方），None 表示主角
    constraints: Optional[List[EvidenceConstraint]] = []  # 与其他 evidence 的约束


class EvidenceUpdate(BaseModel):
    content: Optional[str] = None
    speaker: Optional[str] = None
    constraints: Optional[List[EvidenceConstraint]] = None


class EvidencePositionUpdate(BaseModel):
    target_dia_id: str


class EvidencePolishUpdate(BaseModel):
    polished_text: str


class EvidenceQueryRef(BaseModel):
    """Evidence 所属的 query 引用"""
    id: str        # query id


class Evidence(BaseModel):
    id: str
    content: str
    queries: List[EvidenceQueryRef] = []  # 所属的 query 列表（含顺序）
    speaker: Optional[str] = None       # 由谁说（主角或对方），None 表示主角
    constraints: List[EvidenceConstraint] = []  # 与其他 evidence 的约束
    target_dia_id: Optional[str] = None
    session_key: Optional[str] = None
    status: str = "draft"               # draft/positioned/polished/confirmed
    created_at: str


class PolishedMessage(BaseModel):
    """消息级润色结果 - 支持多个 query 的 evidences 累积"""
    sample_id: int
    dia_id: str                          # 对话消息 ID（与 sample_id 组成唯一标识）
    session_key: str
    original_text: str                   # 原始文本
    final_polished_text: str             # 最终润色文本
    evidence_items: List[dict]           # [{"evidence": {"id": str, "content": str}}, ...]（按润色顺序）
    updated_at: str                      # 最后更新时间


class QueryCreate(BaseModel):
    query_text: str
    sample_id: int
    protagonist: str


class QueryUpdate(BaseModel):
    query_text: Optional[str] = None
    sample_id: Optional[int] = None
    protagonist: Optional[str] = None
    status: Optional[str] = None


class Query(BaseModel):
    id: str
    query_text: str
    sample_id: int
    protagonist: str
    status: str = "draft"
    created_at: str
    evidences: List[str] = []  # 关联的 evidence id 列表

    @property
    def sorted_evidences(self):
        """按 order 排序的 evidences（需要外部注入 _evidences_map）"""
        return self.evidences  # 顺序已在 queries 字段中维护


class SampleInfo(BaseModel):
    index: int
    sample_id: str
    speaker_a: str
    speaker_b: str
    session_count: int


class MessageItem(BaseModel):
    dia_id: str
    speaker: str
    text: str
    session_key: str
    session_date: Optional[str] = None


class AssignResult(BaseModel):
    success: bool
    assignments: Optional[List[dict]] = None
    error: Optional[str] = None
    details: Optional[str] = None


class PolishResult(BaseModel):
    evidence_id: str
    original_text: str
    polished_text: str
    dia_id: str
