#!/usr/bin/env python3
"""
LoCoMo JSON 翻译脚本
支持批量翻译、并发处理、长文本分割
"""

import json
import re
import argparse
import time
from pathlib import Path
from typing import Any, List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import tiktoken
import requests
from tqdm import tqdm


class TokenCounter:
    """Token 计数器"""

    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoder = tiktoken.get_encoding(encoding_name)

    def count(self, text: str) -> int:
        """计算文本的 token 数"""
        return len(self.encoder.encode(text))


class TextSplitter:
    """文本分割器，按句子边界分割长文本"""

    def __init__(self, max_tokens: int = 2000, counter: TokenCounter = None):
        self.max_tokens = max_tokens
        self.counter = counter or TokenCounter()
        # 句子分隔符（优先级从高到低）
        self.delimiters = [
            r'([。！？\n]+)',      # 中文句号
            r'([.!?\n]+)',         # 英文句号
            r'([,，;；]+)'         # 逗号
        ]

    def split(self, text: str) -> List[str]:
        """按句子边界分割文本"""
        if self.counter.count(text) <= self.max_tokens:
            return [text]

        chunks = []
        current_chunk = ""

        for delimiter in self.delimiters:
            sentences = re.split(delimiter, text)
            temp_chunks = []
            current = ""

            for i in range(0, len(sentences), 2):
                sentence = sentences[i]
                sep = sentences[i+1] if i+1 < len(sentences) else ""

                if self.counter.count(current + sentence + sep) <= self.max_tokens:
                    current += sentence + sep
                else:
                    if current:
                        temp_chunks.append(current)
                    current = sentence + sep

            if current:
                temp_chunks.append(current)

            # 检查是否所有分片都满足要求
            if all(self.counter.count(chunk) <= self.max_tokens for chunk in temp_chunks):
                return temp_chunks

        # 如果所有分隔符都无法满足，返回最后一次分割结果
        return temp_chunks if temp_chunks else [text]


class Translator:
    """LLM 翻译器"""

    def __init__(self, config: Dict[str, Any]):
        self.endpoint = config['api']['endpoint']
        self.api_key = config['api']['api_key']
        self.model = config['api']['model']
        self.source_lang = config['translation']['source_lang']
        self.target_lang = config['translation']['target_lang']
        self.max_retries = 3
        self.retry_delay = 1  # 秒

    def translate(self, text: str) -> str:
        """翻译单个文本"""
        if not text or not text.strip():
            return text

        prompt = f"Translate the following text from {self.source_lang} to {self.target_lang}. Return ONLY the translation, no explanations:\n\n{text}"

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    },
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()

            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    print(f"\n翻译失败: {text[:50]}... 错误: {e}")
                    return text  # 返回原文

    def translate_batch(self, texts: List[str]) -> List[str]:
        """批量翻译多个文本"""
        if not texts:
            return []

        if len(texts) == 1:
            return [self.translate(texts[0])]

        # 构造批量翻译 prompt
        texts_json = json.dumps(texts, ensure_ascii=False)
        prompt = f"""Translate the following JSON array of {self.source_lang} texts to {self.target_lang}.
Return ONLY a JSON array with the same order, no explanations:

{texts_json}"""

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    },
                    timeout=120
                )
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()

                # 解析 JSON 数组
                translated = json.loads(content)
                if isinstance(translated, list) and len(translated) == len(texts):
                    return translated
                else:
                    raise ValueError("返回的数组长度不匹配")

            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    print(f"\n批量翻译失败，回退到逐个翻译。错误: {e}")
                    return [self.translate(text) for text in texts]

        return texts  # 返回原文


class LoCoMoTranslator:
    """LoCoMo JSON 翻译器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.counter = TokenCounter()
        self.splitter = TextSplitter(
            max_tokens=config['translation']['max_tokens_per_chunk'],
            counter=self.counter
        )
        self.translator = Translator(config)
        self.batch_size = config['performance']['batch_size']
        self.max_workers = config['performance']['max_workers']

        # 不需要翻译的字段
        self.skip_keys = {
            'dia_id', 'evidence', 'category', 'date', 'date_time',
            'img_url', 're-download', 'sample_id'
        }

        # 统计信息
        self.stats = {
            'total_texts': 0,
            'total_tokens': 0,
            'api_calls': 0
        }

    def should_translate_key(self, key: str) -> bool:
        """判断字段名是否需要翻译"""
        return key not in self.skip_keys

    def translate_text(self, text: str) -> str:
        """翻译单个文本，自动处理长文本分割"""
        if not isinstance(text, str) or not text.strip():
            return text

        self.stats['total_texts'] += 1
        token_count = self.counter.count(text)
        self.stats['total_tokens'] += token_count

        if token_count <= self.config['translation']['max_tokens_per_chunk']:
            self.stats['api_calls'] += 1
            return self.translator.translate(text)
        else:
            # 分割长文本
            chunks = self.splitter.split(text)
            self.stats['api_calls'] += len(chunks)
            translated_chunks = [self.translator.translate(chunk) for chunk in chunks]
            return ''.join(translated_chunks)

    def collect_texts(self, data: Any, path: str = "") -> List[Tuple[str, Any, str]]:
        """收集所有需要翻译的文本，返回 (path, parent, key) 列表"""
        texts = []

        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                if not self.should_translate_key(key):
                    # 递归处理子结构，但不翻译当前值
                    if isinstance(value, (dict, list)):
                        texts.extend(self.collect_texts(value, current_path))
                elif isinstance(value, str) and value.strip():
                    texts.append((current_path, data, key))
                elif isinstance(value, list):
                    # 检查是否是字符串数组
                    if value and isinstance(value[0], str):
                        for i, item in enumerate(value):
                            if isinstance(item, str) and item.strip():
                                texts.append((f"{current_path}[{i}]", value, i))
                    # 检查是否是二元组数组（observation 字段）
                    elif value and isinstance(value[0], list) and len(value[0]) >= 2:
                        for i, item in enumerate(value):
                            if isinstance(item, list) and len(item) >= 2 and isinstance(item[0], str):
                                texts.append((f"{current_path}[{i}][0]", item, 0))
                    else:
                        texts.extend(self.collect_texts(value, current_path))
                elif isinstance(value, dict):
                    texts.extend(self.collect_texts(value, current_path))

        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                texts.extend(self.collect_texts(item, current_path))

        return texts

    def translate_json(self, data: Any) -> Any:
        """翻译整个 JSON 结构"""
        # 收集所有需要翻译的文本
        print("收集待翻译文本...")
        text_refs = self.collect_texts(data)
        print(f"共找到 {len(text_refs)} 个待翻译字段")

        # 分批处理
        batches = []
        current_batch = []
        current_tokens = 0

        for path, parent, key in text_refs:
            text = parent[key]
            if not isinstance(text, str):
                continue

            token_count = self.counter.count(text)

            # 超过阈值的文本单独处理
            if token_count > self.config['translation']['max_tokens_per_chunk']:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = 0
                batches.append([(path, parent, key)])
            else:
                # 检查是否超过批次大小或 token 限制
                if (len(current_batch) >= self.batch_size or
                    current_tokens + token_count > self.config['translation']['max_tokens_per_chunk']):
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = 0

                current_batch.append((path, parent, key))
                current_tokens += token_count

        if current_batch:
            batches.append(current_batch)

        print(f"分为 {len(batches)} 个批次进行翻译")

        # 并发翻译
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for batch in batches:
                future = executor.submit(self._translate_batch, batch)
                futures[future] = batch

            # 显示进度
            for future in tqdm(as_completed(futures), total=len(futures), desc="翻译进度"):
                try:
                    future.result()
                except Exception as e:
                    print(f"\n批次翻译出错: {e}")

        return data

    def _translate_batch(self, batch: List[Tuple[str, Any, str]]):
        """翻译一个批次"""
        if len(batch) == 1:
            # 单个文本，可能需要分割
            path, parent, key = batch[0]
            text = parent[key]
            parent[key] = self.translate_text(text)
        else:
            # 批量翻译
            texts = [parent[key] for path, parent, key in batch]
            self.stats['api_calls'] += 1
            self.stats['total_texts'] += len(texts)
            self.stats['total_tokens'] += sum(self.counter.count(t) for t in texts)

            translated = self.translator.translate_batch(texts)
            for (path, parent, key), trans_text in zip(batch, translated):
                parent[key] = trans_text


def main():
    parser = argparse.ArgumentParser(description="LoCoMo JSON 翻译脚本")
    parser.add_argument("--input", required=True, help="输入 JSON 文件路径")
    parser.add_argument("--output", required=True, help="输出 JSON 文件路径")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--batch-size", type=int, help="批量翻译大小")
    parser.add_argument("--max-workers", type=int, help="并发线程数")

    args = parser.parse_args()

    # 加载配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 覆盖配置
    if args.batch_size:
        config['performance']['batch_size'] = args.batch_size
    if args.max_workers:
        config['performance']['max_workers'] = args.max_workers

    # 加载输入 JSON
    print(f"加载输入文件: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 翻译
    translator = LoCoMoTranslator(config)
    print("开始翻译...")
    start_time = time.time()

    translated_data = translator.translate_json(data)

    elapsed = time.time() - start_time

    # 保存结果
    print(f"保存翻译结果: {args.output}")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(translated_data, f, ensure_ascii=False, indent=2)

    # 输出统计
    print("\n翻译完成！")
    print(f"总文本数: {translator.stats['total_texts']}")
    print(f"总 token 数: {translator.stats['total_tokens']}")
    print(f"API 调用次数: {translator.stats['api_calls']}")
    print(f"耗时: {elapsed:.2f} 秒")


if __name__ == "__main__":
    main()
