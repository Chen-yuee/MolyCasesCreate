import json
from typing import List, Optional, Dict, Any
from .config import get_data_path


class DataLoader:
    """数据加载器，从 JSON 文件加载样本数据，提供查询接口"""

    def __init__(self):
        self._data: List[Dict] = []
        self._load()

    def _load(self):
        """从配置文件指定路径加载 JSON 数据"""
        path = get_data_path()
        with open(path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    def get_samples_info(self) -> List[dict]:
        """返回所有样本的基本信息摘要"""
        result = []
        for i, sample in enumerate(self._data):
            conv = sample["conversation"]
            session_count = sum(
                1 for k in conv if k.startswith("session_") and not k.endswith("_date_time")
            )
            result.append({
                "index": i,
                "sample_id": sample.get("sample_id", str(i)),
                "speaker_a": conv["speaker_a"],
                "speaker_b": conv["speaker_b"],
                "session_count": session_count,
            })
        return result

    def get_sample(self, index: int) -> Optional[Dict]:
        """根据索引获取单个样本"""
        if 0 <= index < len(self._data):
            return self._data[index]
        return None

    def get_all_messages(self, index: int) -> List[dict]:
        """返回该 sample 所有消息，附带 session_key 和 session_date"""
        sample = self.get_sample(index)
        if not sample:
            return []
        conv = sample["conversation"]
        messages = []
        for key, val in conv.items():
            if not key.startswith("session_") or key.endswith("_date_time"):
                continue
            if not isinstance(val, list):
                continue
            date_key = key + "_date_time"
            session_date = conv.get(date_key, "")
            for msg in val:
                messages.append({
                    "dia_id": msg["dia_id"],
                    "speaker": msg["speaker"],
                    "text": msg["text"],
                    "session_key": key,
                    "session_date": session_date,
                })
        return messages

    def get_speaker_messages(self, index: int, speaker: str) -> List[dict]:
        """返回指定说话者的所有消息"""
        return [m for m in self.get_all_messages(index) if m["speaker"] == speaker]

    def get_session_summaries(self, index: int) -> Dict[str, str]:
        """返回该样本的 session 摘要字典"""
        sample = self.get_sample(index)
        if not sample:
            return {}
        return sample.get("session_summary", {})

    def get_session_number(self, session_key: str) -> int:
        """从 'session_3' 提取数字 3"""
        try:
            return int(session_key.split("_")[1])
        except (IndexError, ValueError):
            return 0

    def get_message_by_dia_id(self, index: int, dia_id: str) -> Optional[dict]:
        """根据 dia_id 查找对应消息"""
        for msg in self.get_all_messages(index):
            if msg["dia_id"] == dia_id:
                return msg
        return None

    def get_context_window(self, index: int, dia_id: str, window: int = 3) -> dict:
        """返回目标消息及前后 window 条消息，包含上下文和目标位置索引"""
        all_msgs = self.get_all_messages(index)
        target_idx = next((i for i, m in enumerate(all_msgs) if m["dia_id"] == dia_id), None)
        if target_idx is None:
            return {}
        start = max(0, target_idx - window)
        end = min(len(all_msgs), target_idx + window + 1)
        return {
            "context": all_msgs[start:end],
            "target_index": target_idx - start,
            "target": all_msgs[target_idx],
        }


loader = DataLoader()
