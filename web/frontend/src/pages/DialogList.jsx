import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout, Typography, Card, List, Tag, Space, Badge } from 'antd'
import { ArrowRightOutlined, FileTextOutlined } from '@ant-design/icons'
import { getSamples } from '../api'

const { Header, Content } = Layout
const { Title, Text } = Typography

const STATUS_COLOR = { draft: 'default', confirmed: 'success' }
const STATUS_LABEL = { draft: '草稿', confirmed: '已完成' }

export default function DialogList() {
  const navigate = useNavigate()
  const [samples, setSamples] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const data = await getSamples()
        setSamples(data)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <Title level={4} style={{ color: '#fff', margin: 0 }}>Moly Evidence 插入工具</Title>
      </Header>
      <Content style={{ padding: 24 }}>
        <Card title="Dialog 列表">
          <List
            loading={loading}
            dataSource={samples}
            renderItem={(sample) => (
              <Card
                key={sample.index}
                size="small"
                style={{ marginBottom: 12 }}
                hoverable
                onClick={() => navigate(`/dialog/${sample.index}`)}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <Text strong>#{sample.index}</Text>
                    <Text>{sample.speaker_a} & {sample.speaker_b}</Text>
                    <Tag>{sample.session_count} sessions</Tag>
                    <Badge count={sample.queries?.length || 0} showZero style={{ backgroundColor: '#52c41a' }}>
                      <FileTextOutlined style={{ fontSize: 16 }} />
                    </Badge>
                  </Space>

                  {sample.queries && sample.queries.length > 0 && (
                    <div style={{ paddingLeft: 16, borderLeft: '2px solid #f0f0f0' }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>已有 Query：</Text>
                      {sample.queries.map(q => (
                        <div key={q.id} style={{ marginTop: 4 }}>
                          <Space size="small">
                            <Tag color={STATUS_COLOR[q.status]}>{STATUS_LABEL[q.status]}</Tag>
                            <Text ellipsis style={{ maxWidth: 400 }}>{q.query_text}</Text>
                            <Text type="secondary">({q.evidence_count} evidences)</Text>
                          </Space>
                        </div>
                      ))}
                    </div>
                  )}
                </Space>
              </Card>
            )}
          />
        </Card>
      </Content>
    </Layout>
  )
}
