#!/usr/bin/env python3
"""
MolyCasesCreate - 自动生成 Moly 业务数据集测试样例

使用方法:
    python create_cases.py
    python create_cases.py --dataset my_dataset.jsonl
    python create_cases.py --dataset my_dataset.jsonl --model gpt-4o

环境变量:
    OPENAI_API_KEY  - API 密钥（必需）
    OPENAI_BASE_URL - 自定义 API 地址（可选，默认为 OpenAI 官方地址）
    MODEL_NAME      - 默认使用的模型名称（可选）
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("错误：未找到 openai 包。请运行: pip install openai")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------

def load_dataset(filepath: str) -> list[dict]:
    """从 JSONL 文件加载数据集。"""
    dataset: list[dict] = []
    path = Path(filepath)
    if not path.exists():
        print(f"数据集文件不存在: {filepath}，将从空数据集开始。")
        return dataset
    with open(filepath, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                dataset.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"警告：第 {lineno} 行解析失败，已跳过：{e}")
    return dataset


def show_dataset_summary(dataset: list[dict]) -> None:
    """展示数据集摘要。"""
    print("\n" + "=" * 60)
    print("📊 数据集摘要 (Dataset Summary)")
    print("=" * 60)
    print(f"总样例数量: {len(dataset)}")
    if dataset:
        print("\n最近 3 条样例预览:")
        for i, case in enumerate(dataset[-3:], 1):
            query_preview = str(case.get("query", "N/A"))[:80]
            evidence_preview = str(case.get("evidence", "N/A"))[:60]
            print(f"\n  [{i}] Query:    {query_preview}{'...' if len(str(case.get('query', ''))) > 80 else ''}")
            print(f"       Evidence: {evidence_preview}{'...' if len(str(case.get('evidence', ''))) > 60 else ''}")
    print("=" * 60)


def append_to_dataset(filepath: str, case: dict) -> None:
    """将新样例追加到数据集文件末尾。"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(case, ensure_ascii=False) + "\n")
    print(f"\n✅ 样例已插入数据集: {filepath}")


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def get_client() -> OpenAI:
    """根据环境变量初始化 OpenAI 客户端。"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL")
    if not api_key:
        print("警告：未设置 OPENAI_API_KEY 环境变量。")
    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def analyze_user_intent(client: OpenAI, query: str, evidence: str, model: str) -> str:
    """
    分析用户意图，生成「用户映像」描述。

    根据 query 和 evidence 推断用户想要测试的场景、能力以及预期的模型行为。
    """
    prompt = f"""你是一个专业的测试用例分析助手。根据用户提供的 query 和 evidence，\
分析用户的测试意图与场景，形成简洁的「用户映像」描述。

Query: {query}

Evidence: {evidence}

请从以下三个维度进行分析（每条不超过 2 句话）：
1. 用户想测试的核心场景或能力
2. 这个测试用例的关键挑战点
3. 预期的模型响应应具备的主要特点

请用中文作答，总字数控制在 200 字以内。"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def polish_evidence(
    client: OpenAI,
    query: str,
    evidence: str,
    intent_analysis: str,
    model: str,
) -> str:
    """
    根据 query、用户意图分析，对 evidence 进行润色。

    保留核心信息，使语言更流畅专业，确保与 query 的相关性。
    """
    prompt = f"""你是一个专业的数据集构建助手。请对用户提供的 evidence 进行润色，\
使其更加清晰、准确、完整，适合作为 RAG 测试数据集的参考文本。

Query: {query}

原始 Evidence:
{evidence}

测试意图分析:
{intent_analysis}

润色要求：
1. 保留原始 evidence 的全部核心信息，不得捏造事实
2. 使语言更流畅、专业，去除冗余，补充必要细节
3. 确保润色后的文本与 query 高度相关
4. 格式整洁，段落清晰

只输出润色后的 evidence 文本，不要包含任何解释性前缀或后缀。"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def generate_expected_response(
    client: OpenAI, query: str, polished_evidence: str, model: str
) -> str:
    """基于润色后的 evidence 生成预期的模型回复。"""
    prompt = f"""你是 Moly，一个专业的 AI 助手。请严格根据以下 evidence 回答用户的问题。

Evidence:
{polished_evidence}

用户问题: {query}

要求：
- 回答必须基于 evidence 中的信息
- 如果 evidence 不足以完整回答，请说明并给出已有信息的总结
- 语言简洁、准确、有帮助"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Case builder
# ---------------------------------------------------------------------------

def build_case(query: str, evidence: str, expected_response: str) -> dict:
    """构造一条数据集样例记录。"""
    return {
        "id": f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "created_at": datetime.now().isoformat(),
        "query": query,
        "evidence": evidence,
        "messages": [
            {"role": "user", "content": query},
            {"role": "assistant", "content": expected_response},
        ],
    }


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def read_multiline(prompt: str, end_marker: str = "END") -> str:
    """
    读取多行用户输入，直到遇到 end_marker 单独成行为止。
    如果用户输入了非空单行内容并直接按 Enter，也视作单行输入完成。
    """
    print(prompt)
    lines: list[str] = []
    try:
        while True:
            line = input()
            if line.strip() == end_marker:
                break
            # 如果已经有内容，且当前行为空行，结束输入（不追加空行）
            if lines and line.strip() == "":
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Interactive session
# ---------------------------------------------------------------------------

def interactive_session(
    client: OpenAI,
    dataset: list[dict],
    dataset_path: str,
    model: str,
) -> None:
    """主交互循环：引导用户逐步创建测试样例。"""
    print("\n🚀 开始创建测试样例")
    print("（随时输入 'quit' 或 'exit' 退出程序）\n")

    while True:
        print("-" * 60)

        # ── Step 1: Query ──────────────────────────────────────────
        print("【第 1 步】请输入 Query（用户问题）:")
        query = input("> ").strip()
        if query.lower() in ("quit", "exit", "q"):
            print("再见！")
            break
        if not query:
            print("⚠️  Query 不能为空，请重新输入。\n")
            continue

        # ── Step 2: Evidence ───────────────────────────────────────
        evidence = read_multiline(
            "\n【第 2 步】请输入 Evidence（参考文本）。\n"
            "支持多行，输入完毕后在新行输入 END 或留空行结束:"
        )
        if not evidence:
            print("⚠️  Evidence 不能为空，请重新输入。\n")
            continue

        # ── Step 3: Intent analysis ────────────────────────────────
        print("\n⏳ 正在分析用户映像（User Intent Analysis）...")
        try:
            intent_analysis = analyze_user_intent(client, query, evidence, model)
        except Exception as e:
            print(f"❌ 意图分析失败: {e}")
            continue

        print("\n📋 用户映像分析结果:")
        print(intent_analysis)

        # ── Step 4: Polish evidence ────────────────────────────────
        print("\n⏳ 正在润色 Evidence...")
        try:
            polished = polish_evidence(client, query, evidence, intent_analysis, model)
        except Exception as e:
            print(f"❌ Evidence 润色失败: {e}")
            continue

        print("\n✨ 润色后的 Evidence:")
        print(polished)

        # ── Step 5: Expected response ──────────────────────────────
        print("\n⏳ 正在生成预期模型响应...")
        try:
            expected_response = generate_expected_response(client, query, polished, model)
        except Exception as e:
            print(f"❌ 预期响应生成失败: {e}")
            continue

        print("\n💬 预期模型响应:")
        print(expected_response)

        # ── Step 6: Confirmation ───────────────────────────────────
        print("\n" + "=" * 60)
        print("确认将此样例插入数据集？")
        print("  [y / yes / 是] 确认插入")
        print("  [n / no  / 否] 放弃此样例")
        print("  [r / redo    ] 重新输入 query 和 evidence")

        choice = input("> ").strip().lower()

        if choice in ("y", "yes", "是"):
            case = build_case(query, polished, expected_response)
            append_to_dataset(dataset_path, case)
            dataset.append(case)
            print(f"📦 数据集现有 {len(dataset)} 条样例")
        elif choice in ("r", "redo", "重做"):
            print("↩️  重新开始输入...\n")
            continue
        else:
            print("❌ 已放弃此样例")

        # ── Ask to continue ────────────────────────────────────────
        print("\n继续创建新样例？[y/n]")
        cont = input("> ").strip().lower()
        if cont not in ("y", "yes", "是"):
            print("再见！")
            break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MolyCasesCreate - 自动生成 Moly 业务数据集测试样例",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python create_cases.py
  python create_cases.py --dataset my_dataset.jsonl
  python create_cases.py --dataset my_dataset.jsonl --model gpt-4o

环境变量:
  OPENAI_API_KEY   API 密钥（必需）
  OPENAI_BASE_URL  自定义 API 地址（可选）
  MODEL_NAME       默认使用的模型（可选，优先级低于 --model 参数）
        """,
    )
    parser.add_argument(
        "--dataset",
        default="dataset.jsonl",
        help="数据集文件路径，默认为 dataset.jsonl",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("MODEL_NAME", "gpt-4o-mini"),
        help="使用的模型名称，默认为 gpt-4o-mini（或 MODEL_NAME 环境变量）",
    )
    args = parser.parse_args()

    print("🤖 MolyCasesCreate - 自动生成测试样例工具")
    print("=" * 60)

    client = get_client()
    dataset = load_dataset(args.dataset)
    show_dataset_summary(dataset)
    interactive_session(client, dataset, args.dataset, args.model)


if __name__ == "__main__":
    main()
