# API 参考文档

> 最后更新: 2026-04-15

## 概述

后端 API 基于 FastAPI 实现，所有接口均以 `/api` 为前缀。数据存储使用 `DataStore` 统一管理 `queries`、`evidences`、`polished_messages` 三类数据。

**数据文件格式（整理后）:**
```json
{
  "queries": [...],
  "evidences": [...],
  "polished_messages": [...]
}
```

---

## queries.py — Query 管理

### `GET /api/queries`

获取所有 Query 列表。

### `POST /api/queries`

创建新 Query。

### `GET /api/queries/{qid}`

获取指定 Query 详情。

### `PUT /api/queries/{qid}`

更新 Query。

### `DELETE /api/queries/{qid}`

删除 Query 及关联的 evidences 和 polished_messages。

### `GET /api/queries/{qid}/evidences`

返回该 Query 关联的所有 evidence 对象（按 order 排序）。

### `POST /api/queries/{qid}/evidences`

为指定 Query 创建新的 evidence。

**请求体:** `EvidenceCreate`
```json
{
  "content": "evidence 内容",
  "speaker": "说话人",
  "order": 0,
  "constraints": []
}
```

### `GET /api/queries/{qid}/assign`

为 Query 下所有 draft evidence 自动分配插入位置（按 order 排序）。调用 `inserter.assign_positions`。

**返回:**
```json
{
  "success": true,
  "assignments": [
    {
      "evidence_id": "...",
      "target_dia_id": "D11:11",
      "session_key": "session_11"
    }
  ]
}
```

### `GET /api/queries/{qid}/preview-assign`

预览自动分配结果，不改变 evidence 状态。

### `GET /api/queries/{qid}/polished_messages`

获取该 Query 下所有已润色的消息。

**返回:**
```json
{
  "polished_messages": [
    {
      "dia_id": "D11:11",
      "original_text": "原文",
      "final_polished_text": "润色后",
      "evidence_items": [...],
      "updated_at": "..."
    }
  ]
}
```

### `POST /api/queries/{qid}/polish`

批量润色 Query 下指定的 evidence。

**请求体 (可选):** `BatchPolishBody`
```json
{
  "evidence_ids": ["id1", "id2"]  // 空则润色所有 positioned 的
}
```

---

## evidences.py — Evidence 管理

### `PUT /api/evidences/{eid}`

更新 evidence 内容。

**请求体:** `EvidenceUpdate`
```json
{
  "content": "新内容",
  "speaker": "新说话人",
  "order": 1,
  "constraints": [...]
}
```

### `DELETE /api/evidences/{eid}`

删除 evidence（同步清理关联的 query 和 polished_message）。

### `POST /api/evidences/{eid}/repolish`

重新润色单条 evidence。一次性收集该消息所有关联的 evidence，按 `(query_id, order)` 排序后整体润色。

### `PUT /api/evidences/{eid}/polish_text`

手动编辑润色结果。

**请求体:** `PolishTextBody`
```json
{
  "polished_text": "手动润色的文本"
}
```

### `POST /api/evidences/{eid}/unpolish`

撤销指定 evidence 的润色，从 PolishedMessage 中移除并重新去润色。

---

## insertion.py — 插入位置管理

### `PUT /api/evidences/{eid}/position`

手动设置 evidence 的插入位置。

**请求体:** `ManualPositionBody`
```json
{
  "target_dia_id": "D11:11"
}
```

---

## polish.py — 润色

### `POST /api/evidences/{eid}/repolish`

重新润色单条 evidence（见 evidences.py）。

### `PUT /api/evidences/{eid}/polish_text`

手动编辑润色结果（见 evidences.py）。

---

## samples.py — 样本数据

**前缀:** `/api/samples`

### `GET /api/samples`

获取所有 dialog 列表，每条包含该 dialog 下的 query 列表。

**返回:**
```json
[
  {
    "index": 1,
    "queries": [
      {
        "id": "...",
        "query_text": "...",
        "protagonist": "林晓",
        "status": "draft",
        "evidence_count": 3
      }
    ]
  }
]
```

### `GET /api/samples/{index}/conversation`

获取对话内容，每条消息附带被哪些 query/evidence 影响。

### `GET /api/samples/{index}/speakers`

获取对话双方名称。

**返回:**
```json
{
  "speaker_a": "林晓",
  "speaker_b": "王丽"
}
```

---

## 数据模型

### Query
| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | UUID |
| query_text | string | Query 文本 |
| sample_id | int | 关联的样本 ID |
| protagonist | string | 主角名 |
| status | string | draft/active 等 |
| evidences | list[string] | evidence ID 列表 |
| created_at | string | ISO 时间 |

### Evidence
| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | UUID |
| content | string | evidence 内容 |
| speaker | string | 说话人 |
| order | int | 在 query 中的顺序 |
| constraints | list | 位置约束 |
| target_dia_id | string | 目标消息 dia_id |
| session_key | string | 所属 session |
| status | string | draft/positioned/polished/confirmed |
| queries | list[EvidenceQueryRef] | 关联的 query 引用 |
| created_at | string | ISO 时间 |

### PolishedMessage
| 字段 | 类型 | 说明 |
|------|------|------|
| sample_id | int | 样本 ID |
| dia_id | string | 消息 dia_id |
| session_key | string | session key |
| original_text | string | 原文 |
| final_polished_text | string | 润色后文本 |
| evidence_items | list | 引用的 evidence 列表 |
| updated_at | string | ISO 时间 |

### EvidenceQueryRef
```json
{
  "id": "query_id",
  "order": 0
}
```
