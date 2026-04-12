import { useEffect, useState, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Layout, Card, List, Tag, Space, Typography, Badge } from 'antd'
import { getConversation } from '../api'

const { Content } = Layout
const { Text } = Typography

export default function ConversationPanel({ selectedEvidenceId, highlightDiaId, onClickMessage, refreshKey }) {
  const { dialogId } = useParams()
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const messageRefs = useRef({})

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const msgs = await getConversation(parseInt(dialogId))
        setMessages(msgs)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [dialogId, refreshKey])

  // 滚动到高亮的消息
  useEffect(() => {
    if (highlightDiaId && messageRefs.current[highlightDiaId]) {
      messageRefs.current[highlightDiaId].scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      })
    }
  }, [highlightDiaId])

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
    const baseStyle = {
      padding: '8px',
      marginBottom: 8,
      borderRadius: 4,
      cursor: onClickMessage ? 'pointer' : 'default',
    }

    // 高亮选中的消息
    if (highlightDiaId === msg.dia_id) {
      return {
        ...baseStyle,
        background: '#e6f7ff',
        border: '2px solid #1890ff',
        boxShadow: '0 0 8px rgba(24, 144, 255, 0.3)'
      }
    }

    // 有 evidence 的消息
    if (msg.evidences?.length > 0) {
      return {
        ...baseStyle,
        background: '#f6ffed',
        border: '1px solid #b7eb8f'
      }
    }

    // 普通消息
    return {
      ...baseStyle,
      background: '#fff',
      border: '1px solid #f0f0f0'
    }
  }

  return (
    <Content style={{ padding: 16, overflow: 'auto', background: '#fafafa', height: 'calc(100vh - 64px)' }}>
      {sessionGroups.map(session => (
        <Card
          key={session.key}
          size="small"
          title={
            <Space>
              <Text type="secondary">{session.key}</Text>
              <Text style={{ color: '#1890ff' }}>·</Text>
              <Text style={{ color: '#1890ff', background: '#e6f7ff', padding: '2px 8px', borderRadius: 4 }}>{session.date}</Text>
            </Space>
          }
          style={{ marginBottom: 12 }}
        >
          {session.messages.map(msg => (
            <div
              key={msg.dia_id}
              ref={el => messageRefs.current[msg.dia_id] = el}
              style={getMessageStyle(msg)}
              onClick={() => onClickMessage && onClickMessage(msg)}
            >
              <Space>
                <Text code style={{ fontSize: 11 }}>{msg.dia_id}</Text>
                <Text strong>{msg.speaker}</Text>
                {msg.evidences?.length > 0 && (
                  <Badge count={msg.evidences.length} style={{ backgroundColor: '#52c41a' }} />
                )}
              </Space>
              <div style={{ marginTop: 4 }}>{msg.polished_text || msg.text}</div>
              {msg.evidences?.map(ev => (
                <div key={ev.evidence_id} style={{ marginTop: 4, padding: '4px 8px', background: '#d9f7be', borderRadius: 4 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    📌 {ev.evidence_content}
                  </Text>
                </div>
              ))}
            </div>
          ))}
        </Card>
      ))}
    </Content>
  )
}
