# queries_store.json 数据结构

## 顶层结构

```json
{
  "queries": [...],
  "evidences": [...],
  "polished_messages": [...]
}
```

---

## queries

用户查询列表，每个 query 对应一条业务需求。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 查询唯一 ID (UUID) |
| `query_text` | string | 用户输入的原始查询文本 |
| `sample_id` | integer | 所属样本集 ID |
| `protagonist` | string | 主角名称（查询的执行者） |
| `status` | string | 状态，如 `"draft"`, `"polished"` |
| `created_at` | string | 创建时间，ISO 格式 |

---

## evidences

从各 query 中提取的事实片段，供润色时引用。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 证据唯一 ID (UUID) |
| `content` | string | 事实内容文本 |
| `speaker` | string | 该证据的说话人 |
| `order` | integer | 在原始对话中的顺序（保留原始顺序） |
| `constraints` | array | 约束条件，结构见下方 |
| `target_dia_id` | string | 目标对话消息 ID，格式 `"D{sample}:{msg}"` |
| `session_key` | string | 所属对话 session |
| `status` | string | 状态，如 `"polished"` |
| `created_at` | string | 创建时间，ISO 格式 |
| `queries` | array | 关联的 query 列表，结构见下方 |

### constraints 子结构

约束条件，限制某条 evidence 在润色时与其他 evidence 的共现关系。

| 字段 | 类型 | 说明 |
|------|------|------|
| `target_evidence_id` | string | 关联的另一条 evidence ID |
| `same_session` | boolean | 是否要求同 session |
| `min_turns` | integer/null | 与目标 evidence 的最小间隔轮数 |
| `max_turns` | integer/null | 与目标 evidence 的最大间隔轮数 |

### queries 子结构（evidence 内）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 关联的 query ID |
| `order` | integer | 该 evidence 在该 query 中的顺序（从 0 开始） |

---

## polished_messages

已完成润色的对话消息，包含原始文本和润色后文本及其引用的 evidence。

| 字段 | 类型 | 说明 |
|------|------|------|
| `sample_id` | integer | 所属样本集 ID |
| `dia_id` | string | 对话消息 ID，格式 `"D{sample}:{msg}"` |
| `session_key` | string | 所属 session |
| `original_text` | string | 润色前的原始文本 |
| `final_polished_text` | string | 润色后的文本（已插入 evidence 内容） |
| `evidence_items` | array | 本条消息引用的 evidence 列表 |
| `updated_at` | string | 最后更新时间，ISO 格式 |

### evidence_items 子结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `evidence` | object | 被引用的 evidence，包含 `id` 和 `content` |
