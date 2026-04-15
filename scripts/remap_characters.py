#!/usr/bin/env python3
"""
人物重映射脚本
将 locomo10_CN.json 中 10 个两两对话重映射为 1v3, 1v3, 1v4 群聊结构
- 结构化字段（speaker key、event/observation key）：直接字符串替换
- 自由文本（对话内容、摘要、QA、事件描述）：LLM 批量替换，确保昵称不遗漏
"""

import json
import copy
import time
import requests
from typing import Any

# ============================================================
# 配置区
# ============================================================
# 分组：
#   组1 (1v3): conv-26, conv-30, conv-41  主角: 林晓
#   组2 (1v3): conv-42, conv-43, conv-44  主角: 张明
#   组3 (1v4): conv-47, conv-48, conv-49, conv-50  主角: 陈华
#
# nicknames: 该人物在对话文本中可能出现的所有昵称/缩写/拼写变体

GROUP_CONFIG = [
    # ── 组1 (1v3) ──────────────────────────────────────────
    {
        "conv_id": "conv-26",
        "speaker_a": {
            "old_cn": "卡罗琳", "old_en": "Caroline",
            "new_cn": "林晓",   "new_en": "Lin Xiao",
            "nicknames": ["卡罗", "罗琳"],
        },
        "speaker_b": {
            "old_cn": "梅兰妮", "old_en": "Melanie",
            "new_cn": "苏梅",   "new_en": "Su Mei",
            "nicknames": ["梅兰", "兰妮", "梅尔", "梅拉妮"],
        },
    },
    {
        "conv_id": "conv-30",
        "speaker_a": {
            "old_cn": "乔恩", "old_en": "Jon",
            "new_cn": "林晓", "new_en": "Lin Xiao",
            "nicknames": [],
        },
        "speaker_b": {
            "old_cn": "吉娜", "old_en": "Gina",
            "new_cn": "陈娜", "new_en": "Chen Na",
            "nicknames": [],
        },
    },
    {
        "conv_id": "conv-41",
        "speaker_a": {
            "old_cn": "约翰", "old_en": "John",
            "new_cn": "林晓", "new_en": "Lin Xiao",
            "nicknames": [],
        },
        "speaker_b": {
            "old_cn": "玛丽亚", "old_en": "Maria",
            "new_cn": "王丽",   "new_en": "Wang Li",
            "nicknames": ["玛丽", "丽亚"],
        },
    },
    # ── 组2 (1v3) ──────────────────────────────────────────
    {
        "conv_id": "conv-42",
        "speaker_a": {
            "old_cn": "乔安娜", "old_en": "Joanna",
            "new_cn": "张明",   "new_en": "Zhang Ming",
            "nicknames": ["乔安", "安娜"],
        },
        "speaker_b": {
            "old_cn": "内特", "old_en": "Nate",
            "new_cn": "李强", "new_en": "Li Qiang",
            "nicknames": [],
        },
    },
    {
        "conv_id": "conv-43",
        "speaker_a": {
            "old_cn": "蒂姆", "old_en": "Tim",
            "new_cn": "张明", "new_en": "Zhang Ming",
            "nicknames": [],
        },
        "speaker_b": {
            "old_cn": "约翰", "old_en": "John",
            "new_cn": "赵刚", "new_en": "Zhao Gang",
            "nicknames": [],
        },
    },
    {
        "conv_id": "conv-44",
        "speaker_a": {
            "old_cn": "奥黛丽", "old_en": "Audrey",
            "new_cn": "张明",   "new_en": "Zhang Ming",
            "nicknames": ["奥黛", "黛丽"],
        },
        "speaker_b": {
            "old_cn": "安德鲁", "old_en": "Andrew",
            "new_cn": "刘伟",   "new_en": "Liu Wei",
            "nicknames": ["安德", "德鲁"],
        },
    },
    # ── 组3 (1v4) ──────────────────────────────────────────
    {
        "conv_id": "conv-47",
        "speaker_a": {
            "old_cn": "詹姆斯", "old_en": "James",
            "new_cn": "陈华",   "new_en": "Chen Hua",
            "nicknames": ["詹姆", "姆斯"],
        },
        "speaker_b": {
            "old_cn": "约翰", "old_en": "John",
            "new_cn": "周杰", "new_en": "Zhou Jie",
            "nicknames": [],
        },
    },
    {
        "conv_id": "conv-48",
        "speaker_a": {
            "old_cn": "黛博拉", "old_en": "Deborah",
            "new_cn": "陈华",   "new_en": "Chen Hua",
            "nicknames": ["黛博", "博拉"],
        },
        "speaker_b": {
            "old_cn": "乔琳", "old_en": "Jolene",
            "new_cn": "吴芳", "new_en": "Wu Fang",
            "nicknames": [],
        },
    },
    {
        "conv_id": "conv-49",
        "speaker_a": {
            "old_cn": "埃文", "old_en": "Evan",
            "new_cn": "陈华", "new_en": "Chen Hua",
            "nicknames": [],
        },
        "speaker_b": {
            "old_cn": "山姆", "old_en": "Sam",
            "new_cn": "郑阳", "new_en": "Zheng Yang",
            "nicknames": [],
        },
    },
    {
        "conv_id": "conv-50",
        "speaker_a": {
            "old_cn": "卡尔文", "old_en": "Calvin",
            "new_cn": "陈华",   "new_en": "Chen Hua",
            "nicknames": ["卡尔", "尔文"],
        },
        "speaker_b": {
            "old_cn": "戴夫", "old_en": "Dave",
            "new_cn": "韩磊", "new_en": "Han Lei",
            "nicknames": [],
        },
    },
]

INPUT_FILE  = "data/CN/locomo10_CN.json"
OUTPUT_FILE = "data/CN/locomo10_CN_remapped.json"

# ============================================================
# LLM 客户端（复用 insert_evidence_v2.py 的模式）
# ============================================================

class LLMClient:
    def __init__(self, config: dict[str, Any]):
        self.endpoint = config["api"]["endpoint"]
        self.api_key  = config["api"]["api_key"]
        self.model    = config["api"]["model"]
        self.max_retries = 3

    def call(self, prompt: str, temperature: float = 0.1) -> str:
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(
                    self.endpoint,
                    headers={"Authorization": f"Bearer {self.api_key}",
                             "Content-Type": "application/json"},
                    json={"model": self.model,
                          "messages": [{"role": "user", "content": prompt}],
                          "temperature": temperature},
                    timeout=120,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise RuntimeError(f"LLM 调用失败: {e}")


# ============================================================
# 名字替换规则构建
# ============================================================

def build_name_rules(cfg: dict) -> list[dict]:
    """返回替换规则列表，每条规则含 old/new/nicknames"""
    rules = []
    for role in ("speaker_a", "speaker_b"):
        p = cfg[role]
        rules.append({
            "old_cn":    p["old_cn"],
            "old_en":    p["old_en"],
            "new_cn":    p["new_cn"],
            "new_en":    p["new_en"],
            "nicknames": p["nicknames"],
        })
    return rules


def build_mapping(rules: list[dict]) -> dict[str, str]:
    """构建 {旧字符串: 新字符串} 字典（用于结构化字段的直接替换）"""
    m = {}
    for r in rules:
        m[r["old_cn"]] = r["new_cn"]
        m[r["old_en"]] = r["new_en"]
        for nick in r["nicknames"]:
            m[nick] = r["new_cn"]
    return dict(sorted(m.items(), key=lambda x: -len(x[0])))


def replace_str(text: str, mapping: dict[str, str]) -> str:
    if not isinstance(text, str):
        return text
    for old, new in mapping.items():
        text = text.replace(old, new)
    return text


# ============================================================
# LLM 批量替换自由文本
# ============================================================

def build_llm_prompt(texts: list[str], rules: list[dict]) -> str:
    """
    构建提示词：把所有自由文本打包成 JSON 数组发给 LLM，
    明确列出全名和所有昵称，要求逐条替换后原样返回 JSON。
    """
    mapping_lines = []
    for r in rules:
        nicks = "、".join(r["nicknames"]) if r["nicknames"] else "无"
        mapping_lines.append(
            f'  - 将"{r["old_cn"]}"（昵称/缩写：{nicks}）→ 替换为"{r["new_cn"]}"'
        )
    mapping_desc = "\n".join(mapping_lines)

    texts_json = json.dumps(texts, ensure_ascii=False, indent=2)

    n = len(texts)
    return f"""你是一个文本替换助手。请将下面 JSON 数组中每条字符串里的人名按照规则替换，其他内容保持不变。

【替换规则】
{mapping_desc}

【注意事项】
1. 全名和所有昵称/缩写都必须替换，不能遗漏。
2. 只替换人名，不修改任何其他内容（标点、语气、事件描述等）。
3. 输入数组共 {n} 条，输出也必须是 {n} 条，顺序一一对应。
4. 只返回 JSON 数组本身，不要有任何解释、markdown 代码块或额外文字。

【待替换文本（共 {n} 条）】
{texts_json}"""


BATCH_SIZE = 20  # 每批发给 LLM 的文本条数


def llm_replace_batch(texts: list[str], rules: list[dict], client: LLMClient) -> list[str]:
    """单批替换；解析失败时缩半重试，最终降级为字符串替换"""
    mapping = build_mapping(rules)

    def _try_batch(batch: list[str]) -> list[str]:
        prompt = build_llm_prompt(batch, rules)
        raw = client.call(prompt)
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError("未找到 JSON 数组")
        result = json.loads(raw[start:end])
        if len(result) != len(batch):
            raise ValueError(f"条数不匹配: 期望 {len(batch)}, 实际 {len(result)}")
        return result

    # 第一次尝试
    try:
        return _try_batch(texts)
    except Exception as e:
        print(f"\n  [重试×{len(texts)}条] {e}", end=" ", flush=True)

    # 缩半重试：把 batch 拆成两半分别处理
    if len(texts) > 1:
        try:
            mid = len(texts) // 2
            left  = _try_batch(texts[:mid])
            right = _try_batch(texts[mid:])
            return left + right
        except Exception as e:
            print(f"\n  [降级字符串替换] {e}", end=" ", flush=True)

    # 最终降级
    return [replace_str(t, mapping) for t in texts]


def llm_replace_texts(texts: list[str], rules: list[dict], client: LLMClient) -> list[str]:
    """分批调用 LLM 替换所有文本"""
    if not texts:
        return texts
    result = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i: i + BATCH_SIZE]
        result.extend(llm_replace_batch(batch, rules, client))
    return result


# ============================================================
# 各字段处理
# ============================================================

def remap_struct_keys(mapping: dict[str, str], *dicts):
    """替换字典的 key（用于 event_summary / observation 的英文名 key）"""
    for d in dicts:
        for session_key in list(d.keys()):
            session_val = d[session_key]
            if not isinstance(session_val, dict):
                continue
            new_session_val = {}
            for k, v in session_val.items():
                new_k = replace_str(k, mapping)
                new_session_val[new_k] = v
            d[session_key] = new_session_val


def collect_free_texts(sample: dict) -> tuple[list[str], list[tuple]]:
    """
    收集样本中所有自由文本，返回 (texts, refs)
    refs 是 (setter_fn,) 的列表，用于回写替换结果
    """
    texts = []
    refs  = []   # 每条对应一个 (object, key_or_index)

    conv = sample["conversation"]

    # 1. 对话消息 text / query
    for key, val in conv.items():
        if isinstance(val, list):
            for msg in val:
                if isinstance(msg, dict):
                    for field in ("text", "query"):
                        if field in msg and isinstance(msg[field], str):
                            texts.append(msg[field])
                            refs.append((msg, field))

    # 2. session_summary
    ss = sample.get("session_summary", {})
    for k in ss:
        if isinstance(ss[k], str):
            texts.append(ss[k])
            refs.append((ss, k))

    # 3. qa question / answer / adversarial_answer
    for qa in sample.get("qa", []):
        for field in ("question", "answer", "adversarial_answer"):
            if isinstance(qa.get(field), str):
                texts.append(qa[field])
                refs.append((qa, field))

    # 4. event_summary 文本值（value 是字符串列表）
    es = sample.get("event_summary", {})
    for session_key, session_val in es.items():
        if not isinstance(session_val, dict):
            continue
        for person_key, events in session_val.items():
            if isinstance(events, list):
                for i, ev in enumerate(events):
                    if isinstance(ev, str):
                        texts.append(ev)
                        refs.append((events, i))

    # 5. observation 文本值（value 是 [[text, dia_id], ...] 的列表）
    obs = sample.get("observation", {})
    for session_key, session_val in obs.items():
        if not isinstance(session_val, dict):
            continue
        for person_key, entries in session_val.items():
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, list) and len(entry) >= 1 and isinstance(entry[0], str):
                        texts.append(entry[0])
                        refs.append((entry, 0))

    return texts, refs


def apply_free_texts(refs: list[tuple], new_texts: list[str]):
    """将 LLM 替换结果写回原始数据结构"""
    for (obj, key), new_text in zip(refs, new_texts):
        obj[key] = new_text


def remap_struct_speakers(sample: dict, mapping: dict[str, str]):
    """替换结构化字段中的 speaker（speaker_a/b、消息 speaker 字段）"""
    conv = sample["conversation"]
    conv["speaker_a"] = replace_str(conv["speaker_a"], mapping)
    conv["speaker_b"] = replace_str(conv["speaker_b"], mapping)
    for key, val in conv.items():
        if isinstance(val, list):
            for msg in val:
                if isinstance(msg, dict) and "speaker" in msg:
                    msg["speaker"] = replace_str(msg["speaker"], mapping)


# ============================================================
# 主流程
# ============================================================

def main():
    with open("config.json", encoding="utf-8") as f:
        config = json.load(f)
    client = LLMClient(config)

    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    config_index = {cfg["conv_id"]: cfg for cfg in GROUP_CONFIG}

    result = []
    for sample in data:
        sample   = copy.deepcopy(sample)
        conv_id  = sample["sample_id"]
        cfg      = config_index.get(conv_id)

        if cfg is None:
            print(f"[跳过] {conv_id}")
            result.append(sample)
            continue

        rules   = build_name_rules(cfg)
        mapping = build_mapping(rules)

        # 1. 结构化字段：直接替换 speaker
        remap_struct_speakers(sample, mapping)

        # 2. 结构化字段：替换 event_summary / observation 的英文名 key
        remap_struct_keys(
            mapping,
            sample.get("event_summary", {}),
            sample.get("observation", {}),
        )

        # 3. 自由文本：LLM 分批替换
        texts, refs = collect_free_texts(sample)
        batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"[{conv_id}] LLM 替换 {len(texts)} 条文本（{batches} 批）...", end=" ", flush=True)
        new_texts = llm_replace_texts(texts, rules, client)
        apply_free_texts(refs, new_texts)

        # 4. 字符串替换兜底（处理 LLM 遗漏的名字）
        texts2, refs2 = collect_free_texts(sample)
        apply_free_texts(refs2, [replace_str(t, mapping) for t in texts2])

        # 4. 检查残留
        old_names = [r["old_cn"] for r in rules] + [r["old_en"] for r in rules]
        dump = json.dumps(sample, ensure_ascii=False)
        remaining = {n: dump.count(n) for n in old_names if dump.count(n) > 0}
        status = "✓" if not remaining else f"⚠ 残留: {remaining}"
        print(status)

        result.append(sample)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n输出: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
