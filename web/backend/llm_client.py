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

        prompt = f"""你是一个对话数据标注专家。这里有一段"润色后的消息"，它包含了几条额外的信息(Evidence)。
请你从"润色后的消息"中，完全剔除**需要删除的Evidence**对应的内容，并尽量保留**其他保留的Evidence**的内容不变。

【输入信息】
原始消息（未添加任何Evidence）：
{original_text}

当前的润色消息：
{polished_text}

🚩需要删除的Evidence：
{evidence_to_remove}

✅需要保留的其他Evidence：
{other_ev_str}

【处理要求】
1. 仔细对比"当前的润色消息"和"需要删除的Evidence"，找出属于该Evidence特有的描述和信息。
2. 将这部分内容从"当前的润色消息"中彻底删除。
3. **绝对不要**删除属于"需要保留的其他Evidence"的内容，必须维持它们原本的润色结构和用词。
4. 修复由于删除导致的语句不通顺，但不要改变其他不相关的句子。
5. 请直接输出修改后的消息文本，不允许有任何解释性的语言。

【输出消息】"""
        result = self.call(prompt, temperature=0.1)
        return result or original_text


llm_client = LLMClient()
