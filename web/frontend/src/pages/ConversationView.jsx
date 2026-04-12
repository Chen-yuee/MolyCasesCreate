import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Layout, Typography, Button, List, Tag, Space, Card, message, Tooltip, Badge
} from 'antd'
import { ArrowLeftOutlined, CheckOutlined } from '@ant-design/icons'
import { getQueries, getConversation, setPosition } from '../api'

const { Header, Content } = Layout
const { Title, Text } = Typography

export default function ConversationView() {
  const { qid } = useParams()
  const navigate = useNavigate()
  const [query, setQuery] = useState(null)
  const [messages, setMessages] = useState([])
  const [selectedDiaId, setSelectedDiaId] = useState(null)
  const [targetEvidenceId, setTargetEvidenceId] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const qs = await getQueries()
        const q = qs.find(q => q.id === qid)
        if (!q) return
        setQuery(q)
        const msgs = await getConversation(q.sample_id)
        setMessages(msgs)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [qid])

  const evidences = query?.evidences || []
  const positionedDiaIds = new Set(evidences.map(e => e.target_dia_id).filter(Boolean))

  // 哪些 dia_id 是主角的
  const protagonistDiaIds = new Set(
    messages.filter(m => m.speaker === query?.protagonist).map(m => m.dia_id)
  )

  const handleClickMessage = (msg) => {
    if (!targetEvidenceId) return
    if (msg.speaker !== query?.protagonist) {
      message.warning('只能选择主角的消息作为插入位置')
      return
    }
    setSelectedDiaId(msg.dia_id)
  }

  const handleConfirmPosition = async () => {
    if (!selectedDiaId || !targetEvidenceId) return
    try {
      await setPosition(targetEvidenceId, selectedDiaId)
      message.success(`已设置插入位置：${selectedDiaId}`)
      setSelectedDiaId(null)
      setTargetEvidenceId(null)
      // reload
      const qs = await getQueries()
      const q = qs.find(q => q.id === qid)
      setQuery(q)
    } catch (e) {
      message.error(e.response?.data?.detail || '设置失败')
    }
  }

  // 按 session 分组
  const sessionGroups = []
  let currentSession = null
  for (const msg of messages) {
    if (!currentSession || currentSession.key !== msg.session_key) {
      currentSession = { key: msg.session_key, date: msg.session_date, messages: [] }
      sessionGroups.push(currentSession)
    }
    currentSession.messages.push(msg)
  }

  const getMessageStyle = (msg) => {
    if (selectedDiaId === msg.dia_id) return { background: '#e6f7ff', border: '2px solid #1890ff', borderRadius: 4 }
    if (positionedDiaIds.has(msg.dia_id)) return { background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 4 }
    if (protagonistDiaIds.has(msg.dia_id) && targetEvidenceId) return { cursor: 'pointer', background: '#fffbe6', borderRadius: 4 }
    return {}
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Button icon={<ArrowLeftOutlined />} type="text" style={{ color: '#fff' }} onClick={() => navigate(`/queries/${qid}`)} />
        <Title level={4} style={{ color: '#fff', margin: 0 }}>对话视图</Title>
      </Header>
      <Content style={{ padding: 24, display: 'flex', gap: 16 }}>

        {/* 左侧：对话 */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {sessionGroups.map(session => (
            <Card
              key={session.key}
              size="small"
              title={<Text type="secondary">{session.key.replace('_', ' ').toUpperCase()} · {session.date}</Text>}
              style={{ marginBottom: 8 }}
            >
              {session.messages.map(msg => {
                const positioned = positionedDiaIds.has(msg.dia_id)
                const ev = positioned ? evidences.find(e => e.target_dia_id === msg.dia_id) : null
                return (
                  <div
                    key={msg.dia_id}
                    style={{ padding: '4px 8px', marginBottom: 4, ...getMessageStyle(msg) }}
                    onClick={() => handleClickMessage(msg)}
                  >
                    <Space>
                      <Text code style={{ fontSize: 11 }}>{msg.dia_id}</Text>
                      <Text strong={msg.speaker === query?.protagonist}>{msg.speaker}</Text>
                      {positioned && (
                        <Tooltip title={`Evidence: ${ev?.content}`}>
                          <Badge count="✓" style={{ backgroundColor: '#52c41a' }} />
                        </Tooltip>
                      )}
                    </Space>
                    <div style={{ marginLeft: 8, marginTop: 2 }}>
                      <Text>{msg.text}</Text>
                    </div>
                    {positioned && ev && (
                      <div style={{ marginLeft: 8, marginTop: 4, padding: '2px 8px', background: '#d9f7be', borderRadius: 4 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          📌 {ev.content}
                        </Text>
                      </div>
                    )}
                  </div>
                )
              })}
            </Card>
          ))}
        </div>

        {/* 右侧：Evidence 面板 */}
        <div style={{ width: 300, flexShrink: 0 }}>
          <Card title="手动调整插入位置" size="small" style={{ position: 'sticky', top: 24 }}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              选择一条 evidence，然后在左侧点击主角消息设置插入位置
            </Text>
            <List
              size="small"
              dataSource={evidences}
              renderItem={ev => (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    background: targetEvidenceId === ev.id ? '#e6f7ff' : undefined,
                    borderRadius: 4,
                    padding: '4px 8px',
                  }}
                  onClick={() => setTargetEvidenceId(ev.id === targetEvidenceId ? null : ev.id)}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text style={{ fontSize: 12 }}>{ev.content.slice(0, 60)}</Text>
                    <Space>
                      <Tag color={ev.target_dia_id ? 'green' : 'default'} style={{ fontSize: 11 }}>
                        {ev.target_dia_id || '未定位'}
                      </Tag>
                    </Space>
                  </Space>
                </List.Item>
              )}
            />
            {selectedDiaId && targetEvidenceId && (
              <Button
                type="primary"
                icon={<CheckOutlined />}
                block
                style={{ marginTop: 8 }}
                onClick={handleConfirmPosition}
              >
                确认设置 {selectedDiaId}
              </Button>
            )}
          </Card>
        </div>
      </Content>
    </Layout>
  )
}
