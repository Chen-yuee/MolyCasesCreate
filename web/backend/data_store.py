"""
DataStore - 统一数据存储模块

数据文件格式（整理后）:
{
    "queries": [...],          # Query 对象列表，evidences 字段为 evidence ID 列表
    "evidences": [...],        # 顶层 flattened Evidence 对象列表
    "polished_messages": [...] # PolishedMessage 对象列表
}

类:
    StoreFileHandler   - 文件监听处理器，文件变更时触发重新加载
    DataStore          - 统一数据存储，维护 queries/evidences/polished_messages 内存缓存，支持文件持久化

DataStore 方法:
    _load              - 从 JSON 文件加载数据到内存
    _save              - 将内存数据写回 JSON 文件
    _start_file_watcher - 启动 watchdog 文件监听

    get_queries        - 返回所有 Query 对象
    get_query          - 按 ID 获取 Query
    create_query       - 新建 Query 并持久化
    update_query       - 更新 Query 并持久化
    delete_query       - 删除 Query 及关联的 evidences 和 polished_messages

    get_evidence       - 按 ID 获取 Evidence
    add_evidence       - 向指定 query 添加 evidence
    update_evidence    - 更新 evidence 内容
    delete_evidence    - 删除 evidence

    get_polished_message           - 按 (sample_id, dia_id) 获取 PolishedMessage
    get_polished_messages_by_query - 获取与指定 query 关联的所有 PolishedMessage
    update_polished_message         - 更新 PolishedMessage 并持久化
    delete_polished_message         - 删除指定 PolishedMessage
    delete_polished_messages_by_query - 删除与指定 query 关联的所有 PolishedMessage

最后更新: 2026-04-15
"""

import json
import os
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .models import Query, Evidence, PolishedMessage, EvidenceQueryRef
from .config import get_store_path


class StoreFileHandler(FileSystemEventHandler):
    """
    监听数据文件变化，文件变更时自动重新加载 DataStore。
    """
    def __init__(self, store):
        self.store = store

    def on_modified(self, event):
        # 只响应目标数据文件的变化
        if event.src_path == get_store_path():
            print(f"检测到数据文件变化，重新加载...")
            self.store._load()


class DataStore:
    """
    统一数据存储。
    维护 queries、evidences、polished_messages 三类数据的内存缓存，支持文件持久化。

    数据文件格式（整理后）:
    {
        "queries": [...],          # 不再内嵌 evidences，改为 evidences 字段存 ID 列表
        "evidences": [...],        # 顶层 flattened
        "polished_messages": [...]
    }
    """
    def __init__(self):
        self._queries: Dict[str, Query] = {}
        self._evidences: Dict[str, Evidence] = {}
        self._polished_messages: Dict[str, PolishedMessage] = {}
        self._load()
        self._start_file_watcher()

    # ── 文件监听 ────────────────────────────────────────────────────────────────

    def _start_file_watcher(self):
        """启动 watchdog 监听数据文件变更，变更时触发 _load 重新加载内存缓存。"""
        store_path = get_store_path()
        if not os.path.exists(store_path):
            return

        event_handler = StoreFileHandler(self)
        self.observer = Observer()
        watch_dir = os.path.dirname(store_path)
        self.observer.schedule(event_handler, watch_dir, recursive=False)
        self.observer.start()
        print(f"已启动文件监听: {store_path}")

    # ── 持久化 ──────────────────────────────────────────────────────────────────

    def _load(self):
        """
        从 JSON 文件加载所有数据到内存。
        - queries.evidences 字段现为 evidence ID 列表（不再内嵌 Evidence 对象）
        - evidences 从顶层 data["evidences"] 加载
        """
        path = get_store_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 清空缓存
            self._queries.clear()
            self._evidences.clear()
            self._polished_messages.clear()

            # 加载顶层 evidences（flattend）
            for e in data.get("evidences", []):
                # queries 字段反序列化为 EvidenceQueryRef 列表
                if "queries" in e:
                    e["queries"] = [EvidenceQueryRef(**q) for q in e["queries"]]
                evidence = Evidence(**e)
                self._evidences[evidence.id] = evidence

            # 加载 queries（evidences 字段现为 ID 列表）
            for q in data.get("queries", []):
                query = Query(**q)
                self._queries[query.id] = query

            # 加载 polished_messages
            for m in data.get("polished_messages", []):
                msg = PolishedMessage(**m)
                key = f"{msg.sample_id}:{msg.dia_id}"
                self._polished_messages[key] = msg

            # 验证并修复双向引用一致性
            self._verify_and_fix_bidirectional_refs()
        except Exception:
            pass

    def _verify_and_fix_bidirectional_refs(self):
        """
        验证并修复 Query ↔ Evidence 双向引用一致性。
        - 确保 query.evidences 包含所有引用它的 evidence ID
        - 确保 evidence.queries 包含所有引用它的 query ID
        """
        modified = False

        # 从 evidence.queries 重建 query.evidences
        for query in self._queries.values():
            expected_evidence_ids = set()
            for evidence in self._evidences.values():
                if any(ref.id == query.id for ref in evidence.queries):
                    expected_evidence_ids.add(evidence.id)

            current_evidence_ids = set(query.evidences)
            if expected_evidence_ids != current_evidence_ids:
                query.evidences = list(expected_evidence_ids)
                modified = True

        if modified:
            print("检测到数据不一致，已自动修复")
            self._save()

    def _save(self):
        """
        将内存数据写回 JSON 文件。
        输出格式与 _load 对应：queries.evidences 为 ID 列表，evidences 顶层存放。
        """
        path = get_store_path()
        data = {
            "queries": [q.dict() for q in self._queries.values()],
            "evidences": [e.dict() for e in self._evidences.values()],
            "polished_messages": [m.dict() for m in self._polished_messages.values()],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Query ───────────────────────────────────────────────────────────────────

    def get_queries(self) -> List[Query]:
        """返回所有 Query 对象。"""
        return list(self._queries.values())

    def get_query(self, qid: str) -> Optional[Query]:
        """按 ID 获取 Query，不存在返回 None。"""
        return self._queries.get(qid)

    def create_query(self, query: Query) -> Query:
        """
        新建 Query，初始化空 evidence 列表并持久化。
        注意：evidences 字段默认为空列表 ID，不内嵌 Evidence 对象。
        """
        self._queries[query.id] = query
        self._save()
        return query

    def update_query(self, query: Query) -> Query:
        """更新 Query（内容变更不影响 evidence 关联）。"""
        self._queries[query.id] = query
        self._save()
        return query

    def delete_query(self, qid: str):
        """
        删除 Query，智能处理关联的 evidence：
        - 如果 evidence 被多个 query 共享，仅移除当前 query 的引用
        - 如果 evidence 仅属于当前 query，则完全删除
        """
        query = self._queries.get(qid)
        if not query:
            return

        # 处理每个关联的 evidence
        for eid in list(query.evidences):
            evidence = self._evidences.get(eid)
            if not evidence:
                continue

            # 检查是否被其他 query 共享
            if len(evidence.queries) > 1:
                # 共享的 evidence：仅移除当前 query 的引用
                evidence.queries = [ref for ref in evidence.queries if ref.id != qid]
            else:
                # 独占的 evidence：完全删除（包括 polished messages）
                self.delete_evidence(eid)

        # 移除 query
        self._queries.pop(qid)
        self._save()

    # ── Evidence ────────────────────────────────────────────────────────────────

    def get_evidence(self, eid: str) -> Optional[Evidence]:
        """按 ID 获取 Evidence。"""
        return self._evidences.get(eid)

    def list_evidences(self) -> List[Evidence]:
        """返回所有 Evidence 对象列表。"""
        return list(self._evidences.values())

    def add_evidence(self, qid: str, evidence: Evidence) -> Optional[Evidence]:
        """
        向指定 query 添加 evidence。
        1. 验证 query 存在
        2. 构造 queries 字段（含当前 query 的引用）
        3. 写入顶层 _evidences
        4. 在 query.evidences 列表中追加 evidence ID
        """
        query = self._queries.get(qid)
        if not query:
            return None

        # 构造 queries 引用字段
        evidence.queries = [EvidenceQueryRef(id=qid)]

        self._evidences[evidence.id] = evidence
        query.evidences.append(evidence.id)
        self._save()
        return evidence

    def update_evidence(self, evidence: Evidence) -> Optional[Evidence]:
        """
        更新 evidence 内容。找到所有引用该 evidence 的 query，同步更新它们的 evidence 列表。
        注意：queries 字段本身不修改（如需变更归属应使用其他逻辑）。
        """
        if evidence.id not in self._evidences:
            return None
        self._evidences[evidence.id] = evidence

        # 同步到所有关联 query 的 evidence ID 列表
        for q in self._queries.values():
            if evidence.id not in q.evidences:
                q.evidences.append(evidence.id)

        self._save()
        return evidence

    def _unpolish_evidence_from_message(self, ev: Evidence, q: Query):
        """
        将 evidence 从关联的 PolishedMessage 中解绑并减退。
        - 若无剩余 evidence_items，删除 PolishedMessage
        - 若有其他 evidence，重新调用 LLM 减退
        """
        from .llm_client import llm_client
        from datetime import datetime

        if not ev.target_dia_id:
            return

        polished_msg = self.get_polished_message(q.sample_id, ev.target_dia_id)
        if not polished_msg:
            return

        polished_msg.evidence_items = [
            item for item in polished_msg.evidence_items
            if item["evidence"]["id"] != ev.id
        ]

        if not polished_msg.evidence_items:
            self.delete_polished_message(q.sample_id, polished_msg.dia_id)
        else:
            other_contents = []
            for item in polished_msg.evidence_items:
                cur_ev = self._evidences.get(item["evidence"]["id"])
                if cur_ev:
                    other_contents.append(cur_ev.content)
            polished = llm_client.unpolish(
                original_text=polished_msg.original_text,
                polished_text=polished_msg.final_polished_text,
                evidence_to_remove=ev.content,
                other_evidences=other_contents,
            )
            polished_msg.final_polished_text = polished
            polished_msg.updated_at = datetime.now().isoformat()
            self.update_polished_message(polished_msg)

    def unpolish_evidence_from_message(self, ev: Evidence, q: Query):
        """
        将 evidence 从 PolishedMessage 解绑并减退（公开版本）。
        减退后将 evidence.status 改为 "positioned" 并持久化。
        """
        self._unpolish_evidence_from_message(ev, q)
        ev.status = "positioned"
        self.update_evidence(ev)

    def delete_evidence(self, eid: str) -> bool:
        """
        删除 evidence，同时处理关联的 PolishedMessage 减退。
        1. 找到关联的 query
        2. 从 PolishedMessage 中解绑并减退
        3. 从 query.evidences 列表中移除 ID
        4. 从 _evidences 中移除
        """
        evidence = self._evidences.get(eid)
        if not evidence:
            return False

        # 找到关联的 query
        q = None
        if evidence.queries:
            q = self._queries.get(evidence.queries[0].id)

        # 处理 PolishedMessage 减退
        if q:
            self._unpolish_evidence_from_message(evidence, q)

        # 从 query.evidences 列表中移除
        for query in self._queries.values():
            if eid in query.evidences:
                query.evidences.remove(eid)

        # 从顶层移除
        self._evidences.pop(eid)
        self._save()
        return True

    # ── PolishedMessage ─────────────────────────────────────────────────────────

    def get_polished_message(self, sample_id: int, dia_id: str) -> Optional[PolishedMessage]:
        """按 (sample_id, dia_id) 获取 PolishedMessage。"""
        key = f"{sample_id}:{dia_id}"
        return self._polished_messages.get(key)

    def get_polished_messages_by_query(self, query_id: str) -> List[PolishedMessage]:
        """
        获取与指定 query 关联的所有 PolishedMessage。
        通过 evidence 桥接：找到该 query 的所有 evidence IDs，再找引用了这些 IDs 的 PolishedMessage。
        """
        # 1. 找出该 query 的所有 evidence IDs
        evidence_ids = [
            eid for eid, ev in self._evidences.items()
            if any(ref.id == query_id for ref in ev.queries)
        ]

        # 2. 找出引用了这些 evidence IDs 的 PolishedMessage
        result = []
        for msg in self._polished_messages.values():
            msg_evidence_ids = {item["evidence"]["id"] for item in msg.evidence_items}
            if msg_evidence_ids & set(evidence_ids):
                result.append(msg)
        return result

    def update_polished_message(self, msg: PolishedMessage) -> PolishedMessage:
        """更新 PolishedMessage 内容并持久化。"""
        key = f"{msg.sample_id}:{msg.dia_id}"
        self._polished_messages[key] = msg
        self._save()
        return msg

    def delete_polished_message(self, sample_id: int, dia_id: str):
        """删除指定 PolishedMessage。"""
        key = f"{sample_id}:{dia_id}"
        self._polished_messages.pop(key, None)
        self._save()

    # def delete_polished_messages_by_query(self, query_id: str):
    #     """
    #     删除与指定 query 关联的所有 PolishedMessage。
    #     通过 evidence IDs 桥接，逻辑同 get_polished_messages_by_query。
    #     """
    #     evidence_ids = {
    #         eid for eid, ev in self._evidences.items()
    #         if any(ref.id == query_id for ref in ev.queries)
    #     }

    #     for msg in list(self._polished_messages.values()):
    #         msg_evidence_ids = {item["evidence"]["id"] for item in msg.evidence_items}
    #         intersecting = msg_evidence_ids & evidence_ids
    #         if intersecting:
    #             # 移除属于该 query 的 evidence_items
    #             msg.evidence_items = [
    #                 item for item in msg.evidence_items
    #                 if item["evidence"]["id"] not in intersecting
    #             ]
    #             if not msg.evidence_items:
    #                 self.delete_polished_message(msg.sample_id, msg.dia_id)
    #     self._save()


# 全局单例
store = DataStore()
