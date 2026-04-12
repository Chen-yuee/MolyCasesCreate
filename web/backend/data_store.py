import json
import os
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .models import Query, Evidence, PolishedMessage
from .config import get_store_path


class StoreFileHandler(FileSystemEventHandler):
    """监听数据文件变化"""
    def __init__(self, store):
        self.store = store

    def on_modified(self, event):
        if event.src_path == get_store_path():
            print(f"检测到数据文件变化，重新加载...")
            self.store._load()


class DataStore:
    def __init__(self):
        self._queries: Dict[str, Query] = {}
        self._evidences: Dict[str, Evidence] = {}
        self._polished_messages: Dict[str, PolishedMessage] = {}
        self._load()
        self._start_file_watcher()

    def _start_file_watcher(self):
        """启动文件监听"""
        store_path = get_store_path()
        if not os.path.exists(store_path):
            return

        event_handler = StoreFileHandler(self)
        self.observer = Observer()
        watch_dir = os.path.dirname(store_path)
        self.observer.schedule(event_handler, watch_dir, recursive=False)
        self.observer.start()
        print(f"已启动文件监听: {store_path}")

    def _load(self):
        path = get_store_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for q in data.get("queries", []):
                query = Query(**q)
                self._queries[query.id] = query
                for e in query.evidences:
                    self._evidences[e.id] = e
            for m in data.get("polished_messages", []):
                msg = PolishedMessage(**m)
                key = f"{msg.sample_id}:{msg.dia_id}"
                self._polished_messages[key] = msg
        except Exception:
            pass

    def _save(self):
        path = get_store_path()
        data = {
            "queries": [q.dict() for q in self._queries.values()],
            "polished_messages": [m.dict() for m in self._polished_messages.values()]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # Query operations
    def get_queries(self) -> List[Query]:
        return list(self._queries.values())

    def get_query(self, qid: str) -> Optional[Query]:
        return self._queries.get(qid)

    def create_query(self, query: Query) -> Query:
        self._queries[query.id] = query
        self._save()
        return query

    def update_query(self, query: Query) -> Query:
        self._queries[query.id] = query
        self._save()
        return query

    def delete_query(self, qid: str):
        query = self._queries.pop(qid, None)
        if query:
            for e in query.evidences:
                self._evidences.pop(e.id, None)
            # 删除关联的 PolishedMessage
            self.delete_polished_messages_by_query(qid)
        self._save()

    # Evidence operations
    def get_evidence(self, eid: str) -> Optional[Evidence]:
        return self._evidences.get(eid)

    def add_evidence(self, qid: str, evidence: Evidence) -> Optional[Evidence]:
        query = self._queries.get(qid)
        if not query:
            return None
        query.evidences.append(evidence)
        self._evidences[evidence.id] = evidence
        self._save()
        return evidence

    def update_evidence(self, evidence: Evidence) -> Optional[Evidence]:
        if evidence.id not in self._evidences:
            return None
        self._evidences[evidence.id] = evidence
        # sync into query
        query = self._queries.get(evidence.query_id)
        if query:
            query.evidences = [
                evidence if e.id == evidence.id else e
                for e in query.evidences
            ]
        self._save()
        return evidence

    def delete_evidence(self, eid: str) -> bool:
        evidence = self._evidences.pop(eid, None)
        if not evidence:
            return False
        query = self._queries.get(evidence.query_id)
        if query:
            query.evidences = [e for e in query.evidences if e.id != eid]
        self._save()
        return True

    # PolishedMessage operations
    def get_polished_message(self, sample_id: int, dia_id: str) -> Optional[PolishedMessage]:
        key = f"{sample_id}:{dia_id}"
        return self._polished_messages.get(key)

    def get_polished_messages_by_query(self, query_id: str) -> List[PolishedMessage]:
        """获取包含该 query 的 evidences 的所有 PolishedMessages"""
        result = []
        for msg in self._polished_messages.values():
            if any(item.get("query", {}).get("id") == query_id for item in msg.evidence_items):
                result.append(msg)
        return result

    def update_polished_message(self, msg: PolishedMessage) -> PolishedMessage:
        key = f"{msg.sample_id}:{msg.dia_id}"
        self._polished_messages[key] = msg
        self._save()
        return msg

    def delete_polished_message(self, sample_id: int, dia_id: str):
        key = f"{sample_id}:{dia_id}"
        self._polished_messages.pop(key, None)
        self._save()

    def delete_polished_messages_by_query(self, query_id: str):
        """删除包含该 query 的 evidences 的所有 PolishedMessages"""
        for msg in list(self._polished_messages.values()):
            # 移除该 query 的 evidence_items
            msg.evidence_items = [item for item in msg.evidence_items if item.get("query", {}).get("id") != query_id]
            if not msg.evidence_items:
                # 如果没有 evidence 了，删除整个 PolishedMessage
                key = f"{msg.sample_id}:{msg.dia_id}"
                self._polished_messages.pop(key, None)
        self._save()


store = DataStore()
