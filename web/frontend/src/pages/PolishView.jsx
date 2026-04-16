import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Layout, Typography, Button, Card, Space, Tag, message, Spin,
  Input, Popconfirm, Alert, Divider
} from 'antd'
import {
  ArrowLeftOutlined, ThunderboltOutlined, ReloadOutlined,
  CheckOutlined
} from '@ant-design/icons'
import { getQueries, batchPolish, repolish } from '../api'

const { Header, Content } = Layout
const { Title, Text, Paragraph } = Typography

export default function PolishView() {
  const { qid } = useParams()
  const navigate = useNavigate()
  const [query, setQuery] = useState(null)
  const [polishing, setPolishing] = useState(false)
  const [repolishingId, setRepolishingId] = useState(null)

  const load = async () => {
    const qs = await getQueries()
    setQuery(qs.find(q => q.id === qid) || null)
  }

  useEffect(() => { load() }, [qid])

  const handleBatchPolish = async () => {
    setPolishing(true)
    try {
      const res = await batchPolish(qid)
      message.success(`润色完成，共 ${res.results.length} 条`)
      load()
    } catch (e) {
      message.error(e.response?.data?.detail || '润色失败')
    } finally {
      setPolishing(false)
    }
  }

  const handleRepolish = async (eid) => {
    setRepolishingId(eid)
    try {
      await repolish(eid)
      message.success('重新润色完成')
      load()
    } catch (e) {
      message.error(e.response?.data?.detail || '润色失败')
    } finally {
      setRepolishingId(null)
    }
  }

  if (!query) return <Spin style={{ padding: 48 }} />

  const evidences = query.evidences || []
  const positioned = evidences.filter(e => e.target_dia_id)
  const polished = evidences.filter(e => e.polished_text)

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Button icon={<ArrowLeftOutlined />} type="text" style={{ color: '#fff' }} onClick={() => navigate(`/queries/${qid}`)} />
        <Title level={4} style={{ color: '#fff', margin: 0 }}>润色确认</Title>
      </Header>
      <Content style={{ padding: 24, maxWidth: 900, margin: '0 auto', width: '100%' }}>
        <Card
          title={`润色（${polished.length}/${positioned.length} 已润色）`}
          extra={
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              loading={polishing}
              onClick={handleBatchPolish}
              disabled={positioned.filter(e => e.status === 'positioned').length === 0}
            >
              批量润色未润色的
            </Button>
          }
        >
          {positioned.length === 0 && (
            <Alert message="没有已定位的 evidence，请先在详情页分配插入位置" type="warning" showIcon />
          )}
          {positioned.map((ev, idx) => (
            <Card
              key={ev.id}
              size="small"
              style={{ marginBottom: 12 }}
              title={
                <Space>
                  <Text>#{idx + 1}</Text>
                  <Tag color="blue">{ev.target_dia_id}</Tag>
                  <Tag color={ev.status === 'confirmed' ? 'success' : ev.status === 'polished' ? 'warning' : 'default'}>
                    {ev.status === 'confirmed' ? '已确认' : ev.status === 'polished' ? '已润色' : ev.status}
                  </Tag>
                </Space>
              }
              extra={
                <Space>
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    loading={repolishingId === ev.id}
                    onClick={() => handleRepolish(ev.id)}
                  >
                    重新润色
                  </Button>
                </Space>
              }
            >
              <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                📌 Evidence: {ev.content}
              </Text>
              <Divider style={{ margin: '8px 0' }} />
              <div style={{ display: 'flex', gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>原文</Text>
                  <Paragraph style={{ background: '#fafafa', padding: 8, borderRadius: 4, marginTop: 4 }}>
                    {ev.original_text || '—'}
                  </Paragraph>
                </div>
                <div style={{ flex: 1 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>润色后</Text>
                  <Paragraph
                    style={{
                      background: ev.polished_text ? '#f6ffed' : '#fafafa',
                      padding: 8, borderRadius: 4, marginTop: 4,
                      border: ev.polished_text ? '1px solid #b7eb8f' : undefined,
                    }}
                  >
                    {ev.polished_text || <Text type="secondary">尚未润色</Text>}
                  </Paragraph>
                </div>
              </div>
            </Card>
          ))}
        </Card>
      </Content>
    </Layout>
  )
}
