# LoCoMo JSON 格式

## 顶层结构

每条数据是一个对象，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `sample_id` | string | 唯一标识，如 `"conv-1"` |
| `conversation` | object | 对话内容，按 session 组织 |
| `qa` | array | 问答对列表 |
| `event_summary` | object | 每个 session 的事件摘要 |
| `observation` | object | 每个 session 的观察（含证据 dia_id） |
| `session_summary` | object | 每个 session 的文字摘要 |

## conversation 结构

```json
{
  "speaker_a": "人物A名字",
  "speaker_b": "人物B名字",
  "session_1_date_time": "8 May, 2023, 01:56 pm",
  "session_1": [
    { "speaker": "人物A", "dia_id": "D1:1", "text": "对话内容" },
    { "speaker": "人物B", "dia_id": "D1:2", "text": "对话内容" }
  ]
}
```

## qa 结构

```json
{
  "question": "问题",
  "answer": "答案",
  "evidence": ["D1:3", "D2:5"],
  "category": 1
}
```

category 含义：1=单跳事实，2=时间，3=推理，4=单轮对话

## 完整示例

```json
[
  {
    "sample_id": "conv-1",
    "conversation": {
      "speaker_a": "小明",
      "speaker_b": "小红",
      "session_1_date_time": "1 Jan, 2024, 10:00 am",
      "session_1": [
        { "speaker": "小明", "dia_id": "D1:1", "text": "最近在忙什么？" },
        { "speaker": "小红", "dia_id": "D1:2", "text": "我报名了一个瑜伽课，每周三上课。" },
        { "speaker": "小明", "dia_id": "D1:3", "text": "听起来不错，我最近在学吉他。" }
      ],
      "session_2_date_time": "15 Jan, 2024, 03:00 pm",
      "session_2": [
        { "speaker": "小红", "dia_id": "D2:1", "text": "瑜伽课今天特别累，但很充实。" },
        { "speaker": "小明", "dia_id": "D2:2", "text": "吉他老师说我进步很快！" }
      ]
    },
    "qa": [
      {
        "question": "小红报名了什么课？",
        "answer": "瑜伽课",
        "evidence": ["D1:2"],
        "category": 1
      },
      {
        "question": "小明在学什么乐器？",
        "answer": "吉他",
        "evidence": ["D1:3"],
        "category": 1
      },
      {
        "question": "小红的瑜伽课是哪天？",
        "answer": "每周三",
        "evidence": ["D1:2"],
        "category": 2
      }
    ],
    "event_summary": {
      "events_session_1": {
        "小明": ["小明开始学吉他"],
        "小红": ["小红报名瑜伽课"],
        "date": "1 Jan, 2024"
      }
    },
    "observation": {
      "session_1_observation": {
        "小红": [
          ["小红报名了瑜伽课，每周三上课。", "D1:2"]
        ],
        "小明": [
          ["小明最近在学吉他。", "D1:3"]
        ]
      }
    },
    "session_summary": {
      "session_1_summary": "小明和小红于2024年1月1日交流近况。小红报名了瑜伽课，每周三上课；小明开始学吉他，进展顺利。"
    }
  }
]
```
