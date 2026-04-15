# Evidence 插入与润色脚本使用说明

## 功能概述

`insert_evidence.py` 是一个用于将 evidence 信息自然融入 locomo 数据集对话中的工具。通过 LLM 润色，可以将新的证据信息无缝地整合到指定人物的对话中，生成增强后的数据集。

## 主要特性

- **随机插入**：从指定人物的对话中随机选择位置插入 evidence
- **智能润色**：使用 LLM 将 evidence 自然融入原有对话，保持对话风格一致
- **上下文感知**：提供前后各 3 条消息作为上下文，确保润色结果自然流畅
- **批量处理**：支持一次性处理多段 evidence
- **交互式确认**：展示所有润色结果，支持用户修改和重新生成
- **完整输出**：保存包含元数据、插入记录和完整修改后对话的 JSON 文件

## 安装依赖

```bash
pip3 install requests
```

## 使用方法

### 基本用法

```bash
python3 insert_evidence.py --data locomo10.json --config config.json
```

### 命令行参数

- `--data`: 输入的 JSON 数据文件（必需）
- `--config`: API 配置文件（默认：config.json）
- `--output`: 输出目录（默认：当前目录）

### 交互流程

1. **选择样本**
   - 脚本会显示所有可用的对话样本
   - 输入样本编号进行选择

2. **查看对话摘要**
   - 显示对话双方的名字
   - 显示 session 数量和摘要信息

3. **选择目标人物**
   - 选择 A 或 B，指定要插入 evidence 的人物

4. **输入 Evidence**
   - 每行输入一段 evidence
   - 输入空行结束

5. **自动处理**
   - 脚本会为每段 evidence 随机选择该人物的一条对话
   - 调用 LLM 进行润色，将 evidence 自然融入对话

6. **查看结果**
   - 显示所有润色结果
   - 包含原始对话、润色后对话和上下文

7. **确认与修改**
   - 按 Enter 确认并保存
   - 输入编号（如 1）可以修改指定项
   - 支持重新生成或手动输入

8. **保存结果**
   - 生成带时间戳的 JSON 文件
   - 包含完整的修改后数据

## 输出格式

输出文件命名：`{原文件名}_enhanced_{时间戳}.json`

输出结构：

```json
{
  "metadata": {
    "source_file": "locomo10.json",
    "sample_id": "conv-26",
    "target_speaker": "Caroline",
    "timestamp": "2026-04-07T10:30:00",
    "num_insertions": 3
  },
  "insertions": [
    {
      "evidence": "用户输入的原始 evidence",
      "target_dia_id": "D3:5",
      "session": "session_3",
      "message_index": 4,
      "original_text": "原始对话文本",
      "polished_text": "润色后的对话文本",
      "context_window": [
        {"dia_id": "D3:2", "speaker": "Melanie", "text": "..."},
        {"dia_id": "D3:3", "speaker": "Caroline", "text": "..."}
      ],
      "target_index_in_context": 2
    }
  ],
  "modified_sample": {
    "sample_id": "conv-26",
    "conversation": { ... },
    "qa": [ ... ]
  }
}
```

## 配置文件

确保 `config.json` 包含正确的 API 配置：

```json
{
  "api": {
    "endpoint": "https://api.deepseek.com/v1/chat/completions",
    "api_key": "your-api-key",
    "model": "deepseek-chat"
  }
}
```

## 示例

```bash
# 使用默认配置
python3 insert_evidence.py --data locomo10.json

# 指定输出目录
python3 insert_evidence.py --data locomo10.json --output ./output/

# 使用自定义配置文件
python3 insert_evidence.py --data locomo10.json --config my_config.json
```

## 注意事项

1. **API 调用**：每段 evidence 需要调用一次 LLM API，请确保 API 配额充足
2. **随机性**：每次运行会随机选择不同的对话位置
3. **数据完整性**：只修改对话的 text 字段，其他字段（dia_id、speaker 等）保持不变
4. **重复处理**：默认避免在同一条对话上插入多个 evidence，但如果 evidence 数量超过该人物的对话数量，会允许重复
5. **错误处理**：如果 LLM 调用失败，会提示手动输入润色文本

## 技术细节

### 核心类

- **LLMClient**：封装 LLM API 调用，支持自动重试
- **ConversationLoader**：加载和解析 locomo JSON 数据
- **EvidenceInserter**：处理 evidence 插入和润色的核心逻辑
- **InteractiveUI**：处理用户交互界面

### LLM Prompt 设计

脚本使用精心设计的 prompt 来确保润色结果自然：

- 提供上下文消息（前后各 3 条）
- 明确标记目标消息
- 要求保持说话风格一致
- 要求结果简洁自然（1-3 句话）

## 故障排除

### 问题：LLM 调用失败

- 检查 API key 是否正确
- 检查网络连接
- 查看 API 配额是否充足

### 问题：找不到可用的插入位置

- 确认选择的 speaker 在对话中有消息
- 检查数据文件格式是否正确

### 问题：润色结果不理想

- 使用"重新生成"功能多次尝试
- 使用"手动输入"功能自定义结果
- 调整 config.json 中的 model 参数

## 许可证

本脚本基于 MIT 许可证开源。
