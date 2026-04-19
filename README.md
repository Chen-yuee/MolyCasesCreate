# MolyCasesCreate

生成 Moly 业务数据集的测试样例自动创建工具。

## 功能简介

`create_cases.py` 是一个交互式命令行脚本，用于向 Moly 对话数据集中批量插入高质量测试样例。其工作流程如下：

1. **展示数据集摘要** —— 启动时自动加载并展示现有数据集的统计信息与最近几条样例预览。
2. **用户输入 Query 和 Evidence** —— 用户依次输入问题（query）和参考文本（evidence）。
3. **用户映像分析** —— 脚本调用大模型，分析用户的测试意图与核心场景，生成「用户映像」描述。
4. **Evidence 润色** —— 脚本基于意图分析，对原始 evidence 进行润色，使其更加清晰、专业、与 query 高度相关。
5. **生成预期模型响应** —— 脚本自动生成一条基于润色后 evidence 的预期回复，供参考。
6. **用户确认插入** —— 用户确认后，脚本将完整样例（query、polished evidence、预期响应）以 JSONL 格式追加到数据集文件中。

## 数据集格式

数据集采用 JSONL 格式（每行一条 JSON），每条样例字段如下：

```json
{
  "id": "case_20240101_120000",
  "created_at": "2024-01-01T12:00:00",
  "query": "用户的问题",
  "evidence": "润色后的参考文本",
  "messages": [
    {"role": "user", "content": "用户的问题"},
    {"role": "assistant", "content": "预期的模型回复"}
  ]
}
```

`sample_dataset.jsonl` 提供了 3 条示例数据，可直接用于测试。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
export OPENAI_API_KEY="your-api-key"
# 如需使用自定义 API 地址（如私有部署或第三方兼容接口）：
export OPENAI_BASE_URL="https://your-api-endpoint/v1"
# 指定默认模型（可选，也可通过 --model 参数覆盖）：
export MODEL_NAME="gpt-4o-mini"
```

### 3. 运行脚本

```bash
# 使用默认数据集文件 dataset.jsonl
python create_cases.py

# 指定数据集路径
python create_cases.py --dataset my_dataset.jsonl

# 指定模型
python create_cases.py --dataset my_dataset.jsonl --model gpt-4o

# 从示例数据集开始（只读，建议复制后使用）
cp sample_dataset.jsonl dataset.jsonl
python create_cases.py
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|---|---|---|
| `--dataset` | 数据集文件路径 | `dataset.jsonl` |
| `--model` | 使用的模型名称 | `gpt-4o-mini`（或 `MODEL_NAME` 环境变量） |

## 交互示例

```
🤖 MolyCasesCreate - 自动生成测试样例工具
============================================================
📊 数据集摘要 (Dataset Summary)
============================================================
总样例数量: 3
...
============================================================
🚀 开始创建测试样例

------------------------------------------------------------
【第 1 步】请输入 Query（用户问题）:
> Moly 是否支持多语言界面？

【第 2 步】请输入 Evidence（参考文本）。
支持多行，输入完毕后在新行输入 END 或留空行结束:
Moly 目前提供中文和英文两种界面语言，可在设置中切换。

⏳ 正在分析用户映像（User Intent Analysis）...

📋 用户映像分析结果:
1. 用户想测试模型对产品多语言支持能力的问答准确性。
2. 关键挑战：evidence 信息较简短，需要模型补充合理的引导性说明。
3. 预期回复应准确列出支持的语言，并给出切换方式提示。

⏳ 正在润色 Evidence...

✨ 润色后的 Evidence:
Moly 目前支持中文（简体）和英文两种界面语言。用户可在「设置 → 语言」中随时切换，切换后页面即时刷新生效，无需重新登录。

⏳ 正在生成预期模型响应...
...
确认将此样例插入数据集？[y/n]
> y
✅ 样例已插入数据集: dataset.jsonl
📦 数据集现有 4 条样例
```
