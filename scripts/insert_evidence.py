#!/usr/bin/env python3
"""
Evidence 插入与润色脚本
将用户提供的 evidence 自然融入到 locomo 数据集的对话中
"""

import json
import random
import time
import argparse
import copy
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

import requests


class LLMClient:
    """LLM 调用客户端，复用 translate_json.py 的 API 调用逻辑"""

    def __init__(self, config: dict[str, Any]):
        self.endpoint = config['api']['endpoint']
        self.api_key = config['api']['api_key']
        self.model = config['api']['model']
        self.max_retries = 3
        self.retry_delay = 1

    def call(self, prompt: str, temperature: float = 0.7) -> str:
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
                        "temperature": temperature
                    },
                    timeout=60
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise RuntimeError(f"LLM 调用失败: {e}")


class ConversationLoader:
    """加载和解析 locomo JSON 数据"""

    def __init__(self, data_path: str):
        self.data_path = data_path
        self.data = self.load()

    def load(self) -> list[dict]:
        with open(self.data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_sample(self, index: int) -> dict:
        if 0 <= index < len(self.data):
            return self.data[index]
        raise ValueError(f"Invalid sample index: {index}")

    def get_speakers(self, sample: dict) -> tuple[str, str]:
        conv = sample['conversation']
        return conv['speaker_a'], conv['speaker_b']

    def get_sessions(self, sample: dict) -> list[tuple[str, str, list]]:
        """返回 [(session_key, date_time, messages), ...]"""
        conv = sample['conversation']
        sessions = []

        session_num = 1
        while f'session_{session_num}' in conv:
            session_key = f'session_{session_num}'
            date_time = conv.get(f'{session_key}_date_time', '')
            messages = conv[session_key]
            sessions.append((session_key, date_time, messages))
            session_num += 1

        return sessions

    def get_messages_by_speaker(self, sample: dict, speaker: str) -> list[dict]:
        """返回该 speaker 的所有消息，附带 session 信息"""
        messages = []
        sessions = self.get_sessions(sample)

        for session_key, date_time, session_messages in sessions:
            for idx, msg in enumerate(session_messages):
                if msg['speaker'] == speaker:
                    messages.append({
                        'session_key': session_key,
                        'message_index': idx,
                        'dia_id': msg['dia_id'],
                        'text': msg['text'],
                        'speaker': msg['speaker']
                    })

        return messages

    def get_session_summary(self, sample: dict) -> str:
        """拼接所有 session_summary 作为对话摘要"""
        summaries = []
        session_summary = sample.get('session_summary', {})

        session_num = 1
        while f'session_{session_num}_summary' in session_summary:
            summary = session_summary[f'session_{session_num}_summary']
            summaries.append(f"Session {session_num}: {summary}")
            session_num += 1

        return '\n'.join(summaries)


class EvidenceInserter:
    """核心业务逻辑：evidence 插入和 LLM 润色"""

    def __init__(self, llm: LLMClient, loader: ConversationLoader):
        self.llm = llm
        self.loader = loader

    def select_random_insertion_point(
        self,
        sample: dict,
        speaker: str,
        used_dia_ids: set
    ) -> Optional[dict]:
        """从指定 speaker 的消息中随机选择一条（避免重复）"""
        all_messages = self.loader.get_messages_by_speaker(sample, speaker)
        available = [m for m in all_messages if m['dia_id'] not in used_dia_ids]

        if not available:
            # 如果所有消息都已使用，允许重复
            available = all_messages

        if not available:
            return None

        return random.choice(available)

    def build_context_window(
        self,
        sample: dict,
        session_key: str,
        message_index: int,
        window_size: int = 3
    ) -> list[dict]:
        """获取目标消息前后各 window_size 条消息"""
        session_messages = sample['conversation'][session_key]
        start = max(0, message_index - window_size)
        end = min(len(session_messages), message_index + window_size + 1)
        return session_messages[start:end]

    def polish_with_evidence(
        self,
        original_text: str,
        evidence: str,
        context_messages: list[dict],
        speaker: str,
        target_index_in_context: int
    ) -> str:
        """调用 LLM 将 evidence 融入原对话"""
        context_lines = []
        for i, msg in enumerate(context_messages):
            prefix = ">>> " if i == target_index_in_context else "    "
            context_lines.append(f"{prefix}[{msg['dia_id']}] {msg['speaker']}: {msg['text']}")

        context_str = '\n'.join(context_lines)

        prompt = f"""You are helping to naturally integrate a piece of evidence into an existing conversation message.

Context (surrounding messages, >>> marks the target message):
{context_str}

Task:
The speaker "{speaker}" needs to naturally incorporate the following evidence into their message:
Evidence: "{evidence}"

Original message: "{original_text}"

Requirements:
1. Modify the original message to naturally include the evidence information
2. Keep the speaker's tone and style consistent with the context
3. The modified message should flow naturally with surrounding messages
4. Keep it conversational and natural (1-3 sentences typically)
5. Return ONLY the modified message text, no explanations or quotes

Modified message:"""

        return self.llm.call(prompt, temperature=0.7)

    def process_evidence(
        self,
        sample: dict,
        speaker: str,
        evidence_list: list[str]
    ) -> list[dict]:
        """批量处理所有 evidence，返回插入结果列表"""
        results = []
        used_dia_ids: set[str] = set()

        for i, evidence in enumerate(evidence_list):
            print(f"\n处理 evidence {i+1}/{len(evidence_list)}...")

            target = self.select_random_insertion_point(sample, speaker, used_dia_ids)
            if not target:
                print(f"  警告：找不到可用的插入位置，跳过")
                continue

            used_dia_ids.add(target['dia_id'])

            session_messages = sample['conversation'][target['session_key']]
            msg_idx = target['message_index']
            window_size = 3
            start = max(0, msg_idx - window_size)
            end = min(len(session_messages), msg_idx + window_size + 1)
            context_window = session_messages[start:end]
            target_index_in_context = msg_idx - start

            print(f"  选中对话: [{target['dia_id']}] {target['text'][:60]}...")
            print(f"  正在调用 LLM 润色...")

            try:
                polished_text = self.polish_with_evidence(
                    target['text'],
                    evidence,
                    context_window,
                    speaker,
                    target_index_in_context
                )
            except RuntimeError as e:
                print(f"  LLM 调用失败: {e}")
                polished_text = None

            results.append({
                'evidence': evidence,
                'target_dia_id': target['dia_id'],
                'session': target['session_key'],
                'message_index': target['message_index'],
                'original_text': target['text'],
                'polished_text': polished_text,
                'context_window': [
                    {'dia_id': m['dia_id'], 'speaker': m['speaker'], 'text': m['text']}
                    for m in context_window
                ],
                'target_index_in_context': target_index_in_context
            })

        return results

    def apply_insertions(self, sample: dict, results: list[dict]) -> dict:
        """将确认后的润色结果应用到 sample 数据中"""
        modified = copy.deepcopy(sample)

        for result in results:
            if not result.get('polished_text'):
                continue

            session_key = result['session']
            msg_idx = result['message_index']
            modified['conversation'][session_key][msg_idx]['text'] = result['polished_text']

        return modified


class InteractiveUI:
    """处理用户交互界面"""

    def __init__(self, loader: ConversationLoader):
        self.loader = loader

    def show_samples(self) -> int:
        """显示所有 sample 并让用户选择"""
        print("\n" + "="*60)
        print("可用的对话样本:")
        print("="*60)

        for i, sample in enumerate(self.loader.data):
            sample_id = sample.get('sample_id', f'sample-{i}')
            print(f"  [{i}] {sample_id}")

        print()
        while True:
            try:
                choice = input("请选择样本编号: ").strip()
                index = int(choice)
                if 0 <= index < len(self.loader.data):
                    return index
                print(f"无效的编号，请输入 0-{len(self.loader.data)-1}")
            except (ValueError, KeyboardInterrupt):
                print("\n已取消")
                exit(0)

    def show_conversation_summary(self, sample: dict):
        """显示对话摘要"""
        print("\n" + "="*60)
        print("对话摘要")
        print("="*60)

        speaker_a, speaker_b = self.loader.get_speakers(sample)
        print(f"\nSpeaker A: {speaker_a}")
        print(f"Speaker B: {speaker_b}")

        sessions = self.loader.get_sessions(sample)
        print(f"\n共 {len(sessions)} 个 sessions")

        summary = self.loader.get_session_summary(sample)
        if summary:
            print("\n" + summary)

    def prompt_speaker_selection(self, sample: dict) -> str:
        """提示用户选择 speaker"""
        speaker_a, speaker_b = self.loader.get_speakers(sample)

        print("\n" + "="*60)
        print("选择目标人物")
        print("="*60)
        print(f"  [A] {speaker_a}")
        print(f"  [B] {speaker_b}")

        while True:
            choice = input("\n请选择 (A/B): ").strip().upper()
            if choice == 'A':
                return speaker_a
            elif choice == 'B':
                return speaker_b
            print("无效选择，请输入 A 或 B")

    def prompt_evidence_input(self) -> list[str]:
        """提示用户输入多段 evidence"""
        print("\n" + "="*60)
        print("输入 Evidence")
        print("="*60)
        print("每行输入一段 evidence，输入空行结束\n")

        evidences = []
        while True:
            line = input(f"Evidence {len(evidences)+1}: ").strip()
            if not line:
                break
            evidences.append(line)

        return evidences

    def show_results(self, results: list[dict]):
        """展示所有润色结果"""
        print("\n" + "="*60)
        print("润色结果")
        print("="*60)

        for i, result in enumerate(results):
            print(f"\n[{i+1}] Evidence: {result['evidence']}")
            print(f"    位置: {result['target_dia_id']} ({result['session']})")
            print(f"\n    原始对话:")
            print(f"      {result['original_text']}")
            print(f"\n    润色后:")
            if result['polished_text']:
                print(f"      {result['polished_text']}")
            else:
                print(f"      [LLM 调用失败，需要手动输入]")

            print(f"\n    上下文:")
            for j, msg in enumerate(result['context_window']):
                prefix = ">>>" if j == result['target_index_in_context'] else "   "
                text_preview = msg['text'][:80] + "..." if len(msg['text']) > 80 else msg['text']
                print(f"      {prefix} [{msg['dia_id']}] {msg['speaker']}: {text_preview}")

    def confirm_and_edit(self, results: list[dict], llm: LLMClient, sample: dict, speaker: str) -> list[dict]:
        """让用户确认或修改结果"""
        while True:
            print("\n" + "="*60)
            print("确认与修改")
            print("="*60)
            print("  [Enter] 确认并保存")
            print("  [编号] 修改指定项 (例如: 1)")
            print("  [q] 取消并退出")

            choice = input("\n请选择: ").strip().lower()

            if not choice:
                return results
            elif choice == 'q':
                print("已取消")
                exit(0)
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(results):
                        results[idx] = self._edit_result(results[idx], llm, sample, speaker)
                        self.show_results(results)
                    else:
                        print(f"无效编号，请输入 1-{len(results)}")
                except ValueError:
                    print("无效输入")

    def _edit_result(self, result: dict, llm: LLMClient, sample: dict, speaker: str) -> dict:
        """编辑单个结果"""
        print("\n修改选项:")
        print("  [1] 重新生成")
        print("  [2] 手动输入")
        print("  [3] 取消")

        choice = input("\n请选择: ").strip()

        if choice == '1':
            print("正在重新生成...")
            try:
                inserter = EvidenceInserter(llm, self.loader)
                context_window = result['context_window']
                target_idx = result['target_index_in_context']
                polished = inserter.polish_with_evidence(
                    result['original_text'],
                    result['evidence'],
                    context_window,
                    speaker,
                    target_idx
                )
                result['polished_text'] = polished
                print(f"新结果: {polished}")
            except RuntimeError as e:
                print(f"重新生成失败: {e}")
        elif choice == '2':
            new_text = input("\n请输入新的对话内容: ").strip()
            if new_text:
                result['polished_text'] = new_text

        return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Evidence 插入与润色脚本')
    parser.add_argument('--data', required=True, help='输入的 JSON 数据文件')
    parser.add_argument('--config', default='config.json', help='API 配置文件')
    parser.add_argument('--output', default='.', help='输出目录')
    args = parser.parse_args()

    # 加载配置
    print("加载配置...")
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 初始化组件
    llm = LLMClient(config)
    loader = ConversationLoader(args.data)
    ui = InteractiveUI(loader)

    # 1. 选择样本
    sample_idx = ui.show_samples()
    sample = loader.get_sample(sample_idx)

    # 2. 显示对话摘要
    ui.show_conversation_summary(sample)

    # 3. 选择目标 speaker
    speaker = ui.prompt_speaker_selection(sample)
    print(f"\n已选择: {speaker}")

    # 4. 输入 evidence
    evidences = ui.prompt_evidence_input()
    if not evidences:
        print("未输入任何 evidence，退出")
        return

    print(f"\n共输入 {len(evidences)} 段 evidence")

    # 5. 批量处理
    inserter = EvidenceInserter(llm, loader)
    results = inserter.process_evidence(sample, speaker, evidences)

    # 6. 展示结果
    ui.show_results(results)

    # 7. 确认与修改
    results = ui.confirm_and_edit(results, llm, sample, speaker)

    # 8. 应用修改并保存
    modified_sample = inserter.apply_insertions(sample, results)

    # 生成输出文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    input_filename = Path(args.data).stem
    output_filename = f"{input_filename}_enhanced_{timestamp}.json"
    output_path = Path(args.output) / output_filename

    # 构建输出数据
    output_data = {
        'metadata': {
            'source_file': args.data,
            'sample_id': sample.get('sample_id', f'sample-{sample_idx}'),
            'target_speaker': speaker,
            'timestamp': datetime.now().isoformat(),
            'num_insertions': len(results)
        },
        'insertions': results,
        'modified_sample': modified_sample
    }

    # 保存
    print(f"\n保存到: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print("\n完成！")


if __name__ == '__main__':
    main()

