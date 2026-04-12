import time
import requests
from typing import Optional
from .config import load_config


class LLMClient:
    def __init__(self):
        cfg = load_config()
        api = cfg["api"]
        self.endpoint = api["endpoint"]
        self.api_key = api["api_key"]
        self.model = api["model"]

    def call(self, prompt: str, temperature: float = 0.7, max_retries: int = 3) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        for attempt in range(max_retries):
            try:
                resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise e
        return None

    def polish(self, evidence: str, original_text: str, context: list, target_index: int, speaker: str) -> str:
        ctx_lines = []
        for i, msg in enumerate(context):
            marker = "→ [目标]" if i == target_index else "  "
            ctx_lines.append(f"{marker} {msg['speaker']}: {msg['text']}")
        ctx_str = "\n".join(ctx_lines)

        prompt = f"""你是一个对话数据标注助手。请将以下 evidence 信息自然地融入目标消息中，使对话保持流畅自然。

Evidence（需要融入的信息）：
{evidence}

对话上下文：
{ctx_str}

当前消息文本（可能已包含其他 evidence）：
{original_text}

要求：
1. 只修改「→ [目标]」标记的那条消息
2. 将 evidence 信息自然地融入该消息，保持说话人「{speaker}」的语气风格
3. 如果当前消息已经包含其他信息，请在此基础上继续融入新的 evidence
4. 修改后的消息长度控制在 1-3 句话
5. 不要添加任何解释，直接输出修改后的消息文本

修改后的消息："""
        result = self.call(prompt, temperature=0.7)
        return result or original_text

    def unpolish(self, original_text: str, polished_text: str, evidence_to_remove: str, other_evidences: list) -> str:
        """
        从润色后的文本中删除指定的 evidence，保留其他 evidence 的润色效果。

        Args:
            original_text: 原始消息
            polished_text: 润色后的消息（包含多个 evidence）
            evidence_to_remove: 要删除的 evidence 内容
            other_evidences: 其他要保留的 evidence 列表
        """
        other_ev_str = "\n".join([f"- {ev}" for ev in other_evidences]) if other_evidences else "（无）"

        prompt = f"""你是一个对话数据标注助手。一条原始消息被融入了多个 evidence 信息后变成了润色后的消息。现在需要删除其中一个 evidence，但保留其他 evidence 的效果。

原始消息：
{original_text}

润色后的消息（包含多个 evidence）：
{polished_text}

要删除的 evidence：
{evidence_to_remove}

要保留的其他 evidence：
{other_ev_str}

要求：
1. 从润色后的消息中删除「要删除的 evidence」相关的内容
2. 保留其他 evidence 的润色效果
3. 如果其他 evidence 为空，则恢复到原始消息
4. 保持对话自然流畅
5. 不要添加任何解释，直接输出修改后的消息文本

修改后的消息："""
        result = self.call(prompt, temperature=0.7)
        return result or original_text


llm_client = LLMClient()
