import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Layout, Typography, Button, Table, Tag, Space, Modal, Form,
  Input, Select, message, Popconfirm, Card
} from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined, ArrowRightOutlined } from '@ant-design/icons'
import { getQueries, createQuery, updateQuery, deleteQuery, getSamples } from '../api'

const { Header, Content } = Layout
const { Title } = Typography

const STATUS_COLOR = { draft: 'default', confirmed: 'green' }
const STATUS_LABEL = { draft: '草稿', confirmed: '已完成' }

export default function QueryList() {
  const navigate = useNavigate()
  const [queries, setQueries] = useState([])
  const [samples, setSamples] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingQuery, setEditingQuery] = useState(null)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const [qs, ss] = await Promise.all([getQueries(), getSamples()])
      setQueries(qs)
      setSamples(ss)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditingQuery(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (q) => {
    setEditingQuery(q)
    form.setFieldsValue({
      query_text: q.query_text,
      sample_id: q.sample_id,
      protagonist: q.protagonist,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    try {
      if (editingQuery) {
        await updateQuery(editingQuery.id, values)
        message.success('已更新')
      } else {
        await createQuery(values)
        message.success('已创建')
      }
      setModalOpen(false)
      load()
    } catch (e) {
      message.error('操作失败')
    }
  }

  const handleDelete = async (id) => {
    await deleteQuery(id)
    message.success('已删除')
    load()
  }

  // 当选择样本时，自动填充 protagonist 选项
  const selectedSampleIdx = Form.useWatch('sample_id', form)
  const selectedSample = samples.find(s => s.index === selectedSampleIdx)

  const columns = [
    {
      title: 'Query',
      dataIndex: 'query_text',
      ellipsis: true,
      render: (text, record) => (
        <a onClick={() => navigate(`/queries/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '样本',
      dataIndex: 'sample_id',
      width: 80,
      render: (idx) => {
        const s = samples.find(s => s.index === idx)
        return s ? `#${idx} ${s.speaker_a}` : `#${idx}`
      },
    },
    {
      title: '主角',
      dataIndex: 'protagonist',
      width: 80,
    },
    {
      title: 'Evidence 数',
      dataIndex: 'evidences',
      width: 100,
      render: (evs) => evs?.length || 0,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (s) => s === 'draft' ? null : <Tag color={STATUS_COLOR[s]}>{STATUS_LABEL[s] || s}</Tag>,
    },
    {
      title: '操作',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<ArrowRightOutlined />} onClick={() => navigate(`/queries/${record.id}`)}>
            进入
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Title level={4} style={{ color: '#fff', margin: 0 }}>Moly Evidence 插入工具</Title>
      </Header>
      <Content style={{ padding: 24 }}>
        <Card
          title="Query 列表"
          extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建 Query</Button>}
        >
          <Table
            rowKey="id"
            dataSource={queries}
            columns={columns}
            loading={loading}
            pagination={{ pageSize: 20 }}
          />
        </Card>
      </Content>

      <Modal
        title={editingQuery ? '编辑 Query' : '新建 Query'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="query_text" label="Query 内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} placeholder="例：我打算4月1日15点安排毕昇对接会，忘了要通知谁，帮我安排" />
          </Form.Item>
          <Form.Item name="sample_id" label="选择样本" rules={[{ required: true }]}>
            <Select placeholder="选择对话样本">
              {samples.map(s => (
                <Select.Option key={s.index} value={s.index}>
                  #{s.index} {s.speaker_a} & {s.speaker_b}（{s.session_count} sessions）
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="protagonist" label="主角" rules={[{ required: true }]}>
            <Select placeholder="选择主角（evidence 将插入该人物的对话中）" disabled={selectedSampleIdx === undefined}>
              {selectedSample && [
                <Select.Option key="a" value={selectedSample.speaker_a}>{selectedSample.speaker_a}</Select.Option>,
                <Select.Option key="b" value={selectedSample.speaker_b}>{selectedSample.speaker_b}</Select.Option>,
              ]}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  )
}
