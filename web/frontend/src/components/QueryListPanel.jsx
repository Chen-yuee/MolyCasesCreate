import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Layout, Card, List, Tag, Space, Button, Modal, Form, Input, Select, message, Typography, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { getQueries, getSpeakers, createQuery, updateQuery, deleteQuery, unpolishEvidence, setLinkType } from '../api'

const { Sider } = Layout
const { Text } = Typography

export default function QueryListPanel({ onSelectQuery, selectedQueryId, refreshKey, onQueryDeleted }) {
  const { dialogId } = useParams()
  const [queries, setQueries] = useState([])
  const [speakers, setSpeakers] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingQuery, setEditingQuery] = useState(null)
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()

  const load = async () => {
    const [qs, sp] = await Promise.all([
      getQueries(),
      getSpeakers(parseInt(dialogId))
    ])
    setQueries(qs.filter(q => q.sample_id === parseInt(dialogId)))
    setSpeakers(sp)
  }

  useEffect(() => { load() }, [dialogId, refreshKey])

  const handleCreate = async () => {
    const values = await form.validateFields()
    await createQuery({
      query_text: values.query_text,
      sample_id: parseInt(dialogId),
      protagonist: speakers.speaker_a
    })
    message.success('已创建')
    setModalOpen(false)
    form.resetFields()
    load()
  }

  const handleEdit = (query) => {
    setEditingQuery(query)
    editForm.setFieldsValue({ query_text: query.query_text })
    setEditModalOpen(true)
  }

  const handleUpdate = async () => {
    const values = await editForm.validateFields()
    await updateQuery(editingQuery.id, values)
    message.success('已更新')
    setEditModalOpen(false)
    setEditingQuery(null)
    editForm.resetFields()
    load()
  }

  const getEvidenceCount = (evidences) => {
    return evidences?.length || 0
  }

  const handleDelete = async (queryId) => {
    try {
      // 找到要删除的 query
      const query = queries.find(q => q.id === queryId)

      // 先对所有已润色的 evidence 调用 unpolish
      if (query?.evidences) {
        const polishedEvidences = query.evidences.filter(ev => ev.polished_text)
        for (const ev of polishedEvidences) {
          await unpolishEvidence(ev.id)
        }
      }

      // 然后删除 query
      await deleteQuery(queryId)
      message.success('已删除')
      load()
      onQueryDeleted?.(queryId)
    } catch (e) {
      message.error(e.response?.data?.detail || '删除失败')
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      draft: 'default',
      positioned: 'processing',
      polished: 'success',
      confirmed: 'success'
    }
    return colors[status] || 'default'
  }

  // 取出该 evidence 在指定 query 上下文中的 link 类型（默认 final_ev）
  const getLinkType = (ev, qid) => {
    const ref = ev.queries?.find(r => r.id === qid)
    return ref?.type || 'final_ev'
  }

  // 点击 F/R 标签切换类型
  const handleToggleLinkType = async (e, qid, ev) => {
    e.stopPropagation()
    const cur = getLinkType(ev, qid)
    const next = cur === 'reason_ev' ? 'final_ev' : 'reason_ev'
    try {
      await setLinkType(qid, ev.id, next)
      load()
    } catch (err) {
      message.error(err.response?.data?.detail || '切换失败')
    }
  }

  return (
    <>
      <Sider width="30%" style={{ background: '#fff', borderRight: '1px solid #f0f0f0', padding: 16, height: 'calc(100vh - 64px)', overflow: 'auto' }}>
        <Card
          size="small"
          title="Query 列表"
          extra={<Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建</Button>}
          style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
          bodyStyle={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
        >
          <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
          <List
            size="small"
            dataSource={queries}
            split={false}
            renderItem={(q, idx) => (
              <List.Item
                style={{
                  cursor: 'pointer',
                  background: selectedQueryId === q.id ? '#e6f7ff' : undefined,
                  padding: '8px',
                  borderRadius: 4,
                  alignItems: 'flex-start',
                  marginBottom: '8px',
                  border: '1px solid #f0f0f0',
                }}
                onClick={() => onSelectQuery(q.id)}
              >
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Text strong style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}><Tag>#{idx + 1}</Tag>{q.query_text}</Text>
                  <Space size="small" style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Space size="small">
                      <Tag size="small">{q.protagonist}</Tag>
                      <Tag size="small" color="blue">{getEvidenceCount(q.evidences)}</Tag>
                    </Space>
                    <Space size="small">
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={(e) => { e.stopPropagation(); handleEdit(q) }}
                      />
                      <Popconfirm
                        title="确认删除此 Query？"
                        onConfirm={(e) => { e.stopPropagation(); handleDelete(q.id) }}
                        onCancel={(e) => e.stopPropagation()}
                      >
                        <Button
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </Popconfirm>
                    </Space>
                  </Space>
                  {q.evidences?.length > 0 && (
                    <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                      {q.evidences.map(ev => {
                        const lt = getLinkType(ev, q.id)
                        const isReason = lt === 'reason_ev'
                        return (
                          <div key={ev.id} style={{ marginBottom: 2 }}>
                            <Tag style={{ fontSize: 10 }} color={getStatusColor(ev.status)}>{ev.status}</Tag>
                            <Tag
                              style={{ fontSize: 10, cursor: 'pointer', fontWeight: 'bold' }}
                              color={isReason ? 'orange' : 'cyan'}
                              title={isReason ? 'reason_ev（点击切换为 final_ev）' : 'final_ev（点击切换为 reason_ev）'}
                              onClick={(e) => handleToggleLinkType(e, q.id, ev)}
                            >
                              {isReason ? 'R' : 'F'}
                            </Tag>
                            {ev.content}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </Space>
              </List.Item>
            )}
          />
          </div>
        </Card>
      </Sider>

      <Modal
        title="新建 Query"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="query_text" label="Query 内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="编辑 Query"
        open={editModalOpen}
        onOk={handleUpdate}
        onCancel={() => {
          setEditModalOpen(false)
          setEditingQuery(null)
          editForm.resetFields()
        }}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="query_text" label="Query 内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
