import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Layout, Typography, Button, Table, Tag, Space, Modal, Form,
  Input, InputNumber, Select, message, Popconfirm, Card, Descriptions,
  Tooltip, Alert
} from 'antd'
import {
  PlusOutlined, DeleteOutlined, EditOutlined, ThunderboltOutlined,
  EyeOutlined, ArrowLeftOutlined, ExportOutlined
} from '@ant-design/icons'
import {
  getQueries, createEvidence, updateEvidence, deleteEvidence,
  autoAssign, exportQuery
} from '../api'

const { Header, Content } = Layout
const { Title, Text } = Typography

const TYPE_COLOR = { contact: 'blue', schedule: 'green', todo: 'orange', general: 'default' }
const TYPE_LABEL = { contact: '联系人', schedule: '日程', todo: '待办', general: '通用' }
const STATUS_COLOR = { draft: 'default', positioned: 'processing', polished: 'success', confirmed: 'success' }
const STATUS_LABEL = { draft: '草稿', positioned: '已定位', polished: '已润色', confirmed: '已确认' }

export default function QueryDetail() {
  const { qid } = useParams()
  const navigate = useNavigate()
  const [query, setQuery] = useState(null)
  const [loading, setLoading] = useState(false)
  const [assigning, setAssigning] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingEv, setEditingEv] = useState(null)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const qs = await getQueries()
      const q = qs.find(q => q.id === qid)
      setQuery(q || null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [qid])

  const openCreate = () => {
    setEditingEv(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (ev) => {
    setEditingEv(ev)
    form.setFieldsValue({
      content: ev.content,
      update_from: ev.update_from || undefined,
      min_gap_sessions: ev.min_gap_sessions,
      max_gap_sessions: ev.max_gap_sessions,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    try {
      if (editingEv) {
        await updateEvidence(editingEv.id, values)
        message.success('已更新')
      } else {
        await createEvidence(qid, { content: values.content })
        // 如果有更新关系，再 patch
        if (values.update_from) {
          // 需要获取新创建的 ev id，先 reload
        }
        message.success('已创建')
      }
      setModalOpen(false)
      load()
    } catch (e) {
      message.error('操作失败')
    }
  }

  const handleDelete = async (eid) => {
    await deleteEvidence(eid)
    message.success('已删除')
    load()
  }

  const handleAutoAssign = async () => {
    setAssigning(true)
    try {
      const res = await autoAssign(qid)
      message.success(`已为 ${res.assignments?.length || 0} 条 evidence 分配插入位置`)
      load()
    } catch (e) {
      message.error(e.response?.data?.detail || '分配失败')
    } finally {
      setAssigning(false)
    }
  }

  const handleExport = async () => {
    try {
      const blob = await exportQuery(qid)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `query_${qid.slice(0, 8)}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      message.error(e.response?.data?.detail || '导出失败')
    }
  }

  if (!query) return <div style={{ padding: 24 }}>加载中...</div>

  const evidences = query.evidences || []
  const positionedCount = evidences.filter(e => e.status !== 'draft').length
  const confirmedCount = evidences.filter(e => e.status === 'confirmed').length

  const columns = [
    {
      title: '#',
      width: 40,
      render: (_, __, idx) => idx + 1,
    },
    {
      title: 'Evidence 内容',
      dataIndex: 'content',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'type',
      width: 80,
      render: (t) => <Tag color={TYPE_COLOR[t]}>{TYPE_LABEL[t] || t}</Tag>,
    },
    {
      title: '插入位置',
      dataIndex: 'target_dia_id',
      width: 120,
      render: (dia_id, rec) => dia_id
        ? <Tooltip title={rec.original_text}><Tag color="blue">{dia_id}</Tag></Tooltip>
        : <Text type="secondary">未分配</Text>,
    },
    {
      title: '更新关系',
      width: 100,
      render: (_, rec) => {
        if (!rec.update_from) return null
        const old = evidences.find(e => e.id === rec.update_from)
        return (
          <Tooltip title={`旧 evidence: ${old?.content?.slice(0, 30) || rec.update_from}`}>
            <Tag color="purple">覆盖前者</Tag>
          </Tooltip>
        )
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (s) => <Tag color={STATUS_COLOR[s]}>{STATUS_LABEL[s] || s}</Tag>,
    },
    {
      title: '操作',
      width: 120,
      render: (_, rec) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(rec)} />
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(rec.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Button icon={<ArrowLeftOutlined />} type="text" style={{ color: '#fff' }} onClick={() => navigate('/queries')} />
        <Title level={4} style={{ color: '#fff', margin: 0 }}>Moly Evidence 插入工具</Title>
      </Header>
      <Content style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Query 信息 */}
        <Card>
          <Descriptions title="Query 信息" column={3}>
            <Descriptions.Item label="内容" span={3}>{query.query_text}</Descriptions.Item>
            <Descriptions.Item label="样本">#{query.sample_id}</Descriptions.Item>
            <Descriptions.Item label="主角">{query.protagonist}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={query.status === 'confirmed' ? 'green' : 'default'}>
                {query.status === 'confirmed' ? '已完成' : '草稿'}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        {/* Evidence 列表 */}
        <Card
          title={`Evidence 列表（${positionedCount}/${evidences.length} 已定位，${confirmedCount} 已确认）`}
          extra={
            <Space>
              <Button icon={<PlusOutlined />} onClick={openCreate}>添加 Evidence</Button>
              <Button
                icon={<ThunderboltOutlined />}
                onClick={handleAutoAssign}
                loading={assigning}
                disabled={evidences.length === 0}
              >
                自动分配位置
              </Button>
              <Button
                icon={<EyeOutlined />}
                onClick={() => navigate(`/queries/${qid}/conversation`)}
                disabled={positionedCount === 0}
              >
                查看对话
              </Button>
              <Button
                icon={<EyeOutlined />}
                onClick={() => navigate(`/queries/${qid}/polish`)}
                disabled={positionedCount === 0}
              >
                润色
              </Button>
              <Button
                icon={<ExportOutlined />}
                onClick={handleExport}
                disabled={confirmedCount === 0}
              >
                导出 JSON
              </Button>
            </Space>
          }
        >
          {evidences.length === 0 && (
            <Alert
              message="还没有 Evidence，点击「添加 Evidence」开始添加"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}
          <Table
            rowKey="id"
            dataSource={evidences}
            columns={columns}
            loading={loading}
            pagination={false}
            size="small"
          />
        </Card>
      </Content>

      <Modal
        title={editingEv ? '编辑 Evidence' : '添加 Evidence'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="保存"
        cancelText="取消"
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="content" label="Evidence 内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} placeholder="例：联系人：张三，北京某公司，AI 负责人" />
          </Form.Item>
          {editingEv && evidences.filter(e => e.id !== editingEv.id).length > 0 && (
            <>
              <Form.Item name="update_from" label="覆盖旧 Evidence（记忆更新场景，可选）">
                <Select allowClear placeholder="如果此 evidence 是对旧 evidence 的更新，请选择旧的那条">
                  {evidences.filter(e => e.id !== editingEv?.id).map(e => (
                    <Select.Option key={e.id} value={e.id}>
                      [{TYPE_LABEL[e.type]}] {e.content.slice(0, 40)}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
              <Space>
                <Form.Item name="min_gap_sessions" label="最小间隔（session 数）">
                  <InputNumber min={1} placeholder="1" style={{ width: 160 }} />
                </Form.Item>
                <Form.Item name="max_gap_sessions" label="最大间隔（session 数）">
                  <InputNumber min={1} placeholder="不限" style={{ width: 160 }} />
                </Form.Item>
              </Space>
            </>
          )}
        </Form>
      </Modal>
    </Layout>
  )
}
