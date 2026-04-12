import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Typography, Button } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import QueryListPanel from '../components/QueryListPanel'
import ConversationPanel from '../components/ConversationPanel'
import QueryDetailPanel from '../components/QueryDetailPanel'

const { Header } = Layout
const { Title } = Typography

export default function DialogView() {
  const { dialogId } = useParams()
  const navigate = useNavigate()
  const [selectedQueryId, setSelectedQueryId] = useState(null)
  const [selectedEvidenceId, setSelectedEvidenceId] = useState(null)
  const [highlightDiaId, setHighlightDiaId] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  // 轮询刷新
  useEffect(() => {
    const interval = setInterval(() => {
      setRefreshKey(k => k + 1)
    }, 500) // 每0.5秒刷新一次

    return () => clearInterval(interval)
  }, [])

  const handleClickEvidence = (evidenceId, diaId) => {
    setSelectedEvidenceId(evidenceId)
    setHighlightDiaId(diaId)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          type="text"
          style={{ color: '#fff' }}
          onClick={() => navigate('/')}
        />
        <Title level={4} style={{ color: '#fff', margin: 0 }}>
          Dialog #{dialogId}
        </Title>
      </Header>
      <Layout>
        <QueryListPanel
          onSelectQuery={setSelectedQueryId}
          selectedQueryId={selectedQueryId}
          refreshKey={refreshKey}
          onQueryDeleted={(deletedQueryId) => {
            if (selectedQueryId === deletedQueryId) {
              setSelectedQueryId(null)
            }
            setRefreshKey(k => k + 1)
          }}
        />
        <Layout style={{ flex: 1 }}>
          <ConversationPanel
            selectedEvidenceId={selectedEvidenceId}
            highlightDiaId={highlightDiaId}
            refreshKey={refreshKey}
          />
        </Layout>
        {selectedQueryId && (
          <QueryDetailPanel
            queryId={selectedQueryId}
            onClose={() => setSelectedQueryId(null)}
            onClickEvidence={handleClickEvidence}
            onPolishDone={() => setRefreshKey(k => k + 1)}
            refreshKey={refreshKey}
          />
        )}
      </Layout>
    </Layout>
  )
}
