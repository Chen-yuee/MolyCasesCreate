import axios from 'axios'

const api = axios.create({
  baseURL: '', // 使用相对路径，开发环境通过 Vite proxy，生产环境由于同源直接生效
  timeout: 60000,
})

// Samples
// → DialogList 页面加载
export const getSamples = () => api.get('/api/samples').then(r => r.data)
// → ConversationPanel 加载对话内容，受 refreshKey 控制刷新
export const getConversation = (idx) => api.get(`/api/samples/${idx}/conversation?_t=${Date.now()}`).then(r => r.data)
// → QueryListPanel 中显示说话人标签
export const getSpeakers = (idx) => api.get(`/api/samples/${idx}/speakers`).then(r => r.data)

// Queries
// → QueryListPanel / ConversationView / QueryDetailPanel / PolishView 加载时获取 query 列表
export const getQueries = () => api.get('/api/queries').then(r => r.data)
// → QueryListPanel "新建 Query"按钮
export const createQuery = (body) => api.post('/api/queries', body).then(r => r.data)
// → QueryListPanel 编辑 query 后保存
export const updateQuery = (id, body) => api.put(`/api/queries/${id}`, body).then(r => r.data)
// → QueryListPanel "删除 Query"按钮
export const deleteQuery = (id) => api.delete(`/api/queries/${id}`).then(r => r.data)
// → QueryDetailPanel / PolishView 查看润色结果列表（"润色"tab）
export const getPolishedMessages = (qid) => api.get(`/api/queries/${qid}/polished_messages`).then(r => r.data)

// Evidences
// → 暂未直接调用
export const getEvidences = (qid) => api.get(`/api/queries/${qid}/evidences`).then(r => r.data)
// → QueryDetailPanel "新增 Evidence"按钮
export const createEvidence = (qid, body) => api.post(`/api/queries/${qid}/evidences`, body).then(r => r.data)
// → QueryDetailPanel 编辑 evidence 内容/说话人/顺序后保存
export const updateEvidence = (eid, body) => api.put(`/api/evidences/${eid}`, body).then(r => r.data)
// → QueryDetailPanel "删除 Evidence"按钮
export const deleteEvidence = (eid) => api.delete(`/api/evidences/${eid}`).then(r => r.data)
// → ConversationView 点击消息行，手动设置 evidence 的插入位置
export const setPosition = (eid, target_dia_id) => api.put(`/api/evidences/${eid}/position`, { target_dia_id }).then(r => r.data)
// → QueryListPanel / QueryDetailPanel "减退"按钮
export const unpolishEvidence = (eid) => api.post(`/api/evidences/${eid}/unpolish`).then(r => r.data)

// Insertion
// → QueryDetailPanel "自动分配"按钮
export const autoAssign = (qid) => api.post(`/api/queries/${qid}/assign`).then(r => r.data)
// → QueryDetailPanel "预览分配"按钮
export const previewAssign = (qid) => api.post(`/api/queries/${qid}/preview-assign`).then(r => r.data)
// → ConversationView 
export const manualAssign = (qid, assignments) => api.post(`/api/queries/${qid}/manual-assign`, { assignments }).then(r => r.data)

// Polish
// → QueryDetailPanel / PolishView "批量润色"按钮
export const batchPolish = (qid, evidence_ids = null) => api.post(`/api/queries/${qid}/polish`, { evidence_ids }).then(r => r.data)
// → QueryDetailPanel 单条 positioned evidence 的"重新润色"按钮
export const repolish = (eid) => api.post(`/api/evidences/${eid}/repolish`).then(r => r.data)
