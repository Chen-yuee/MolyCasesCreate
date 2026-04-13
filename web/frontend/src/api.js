import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8024',
  timeout: 60000,
})

// Samples
export const getSamples = () => api.get('/api/samples').then(r => r.data)
export const getConversation = (idx) => api.get(`/api/samples/${idx}/conversation`).then(r => r.data)
export const getSpeakers = (idx) => api.get(`/api/samples/${idx}/speakers`).then(r => r.data)

// Queries
export const getQueries = () => api.get('/api/queries').then(r => r.data)
export const createQuery = (body) => api.post('/api/queries', body).then(r => r.data)
export const updateQuery = (id, body) => api.put(`/api/queries/${id}`, body).then(r => r.data)
export const deleteQuery = (id) => api.delete(`/api/queries/${id}`).then(r => r.data)
export const getPolishedMessages = (qid) => api.get(`/api/queries/${qid}/polished_messages`).then(r => r.data)

// Evidences
export const getEvidences = (qid) => api.get(`/api/queries/${qid}/evidences`).then(r => r.data)
export const createEvidence = (qid, body) => api.post(`/api/queries/${qid}/evidences`, body).then(r => r.data)
export const updateEvidence = (eid, body) => api.put(`/api/evidences/${eid}`, body).then(r => r.data)
export const deleteEvidence = (eid) => api.delete(`/api/evidences/${eid}`).then(r => r.data)
export const setPosition = (eid, target_dia_id) => api.put(`/api/evidences/${eid}/position`, { target_dia_id }).then(r => r.data)
export const setPolishText = (eid, polished_text) => api.put(`/api/evidences/${eid}/polish_text`, { polished_text }).then(r => r.data)
export const unpolishEvidence = (eid) => api.post(`/api/evidences/${eid}/unpolish`).then(r => r.data)

// Insertion
export const autoAssign = (qid) => api.post(`/api/queries/${qid}/assign`).then(r => r.data)
export const previewAssign = (qid) => api.post(`/api/queries/${qid}/preview-assign`).then(r => r.data)

// Polish
export const batchPolish = (qid, evidence_ids = null) => api.post(`/api/queries/${qid}/polish`, { evidence_ids }).then(r => r.data)
export const repolish = (eid) => api.post(`/api/evidences/${eid}/repolish`).then(r => r.data)

// Export
export const exportQuery = (qid) => api.post(`/api/export/${qid}`, {}, { responseType: 'blob' }).then(r => r.data)
