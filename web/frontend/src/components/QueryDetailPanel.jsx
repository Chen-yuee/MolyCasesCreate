import { useEffect, useState } from 'react'
import { Layout, Card, Button, Space, List, Tag, Form, Input, Select, InputNumber, message, Popconfirm, Modal } from 'antd'
import { PlusOutlined, DeleteOutlined, ThunderboltOutlined, CloseOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons'
import { getQueries, createEvidence, updateEvidence, deleteEvidence, autoAssign, batchPolish, previewAssign, unpolishEvidence, setPosition, repolish, getPolishedMessages, getConversation, getAllEvidences, attachEvidence, manualAssign } from '../api'

const { Sider } = Layout

export default function QueryDetailPanel({ queryId, onClose, onClickEvidence, onPolishDone, refreshKey }) {
  const [query, setQuery] = useState(null)
  const [speakers, setSpeakers] = useState(null)
  const [mode, setMode] = useState('setup') // setup | polish
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()
  const [previewAssignments, setPreviewAssignments] = useState({})
  const [isDirty, setIsDirty] = useState(false)
  const [editingEvidence, setEditingEvidence] = useState(null)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [polishEditModalOpen, setPolishEditModalOpen] = useState(false)
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [draggedIndex, setDraggedIndex] = useState(null)
  const [polishedMessages, setPolishedMessages] = useState([])
  const [manualAssignModalOpen, setManualAssignModalOpen] = useState(false)
  const [allMessages, setAllMessages] = useState([])
  const [sessionKeys, setSessionKeys] = useState([])
  const [manualAssignments, setManualAssignments] = useState({})
  const [addMode, setAddMode] = useState('new') // 'new' | 'existing'
  const [allEvidences, setAllEvidences] = useState([])
  const [selectedExistingEvidence, setSelectedExistingEvidence] = useState(null)

  const load = async () => {
    const qs = await getQueries()
    const q = qs.find(q => q.id === queryId)
    setQuery(q)
    // 加载 speakers 信息
    if (q && !speakers) {
      const { getSpeakers } = await import('../api')
      const sp = await getSpeakers(q.sample_id)
      setSpeakers(sp)
    }
    // 加载对话消息
    if (q) {
      const msgs = await getConversation(q.sample_id)
      setAllMessages(msgs)
      // 提取所有 session keys
      const sessions = [...new Set(msgs.map(m => m.session_key))].sort()
      setSessionKeys(sessions)
    }
    // 加载所有 evidences（用于添加已有 evidence）
    try {
      const allEvs = await getAllEvidences()
      // 过滤出该 sample 中已经 positioned 或 polished 的 evidence，且不属于当前 query
      const currentQueryEvidenceIds = new Set(q?.evidences?.map(e => e.id) || [])
      const availableEvs = allEvs.filter(ev =>
        ev.target_dia_id && // 有位置
        (ev.status === 'positioned' || ev.status === 'polished') && // 状态是 positioned 或 polished
        !currentQueryEvidenceIds.has(ev.id) && // 不属于当前 query
        ev.queries.length > 0 && // 有关联的 query
        ev.queries[0].id !== queryId // 确保不是当前 query
      )
      setAllEvidences(availableEvs)
    } catch (e) {
      setAllEvidences([])
    }
    // 加载 PolishedMessages
    try {
      const messages = await getPolishedMessages(queryId)
      setPolishedMessages(messages)
    } catch (e) {
      setPolishedMessages([])
    }
  }

  useEffect(() => {
    // 初始化时判断模式
    const initMode = async () => {
      const qs = await getQueries()
      const q = qs.find(q => q.id === queryId)
      const hasPositioned = q?.evidences?.some(e => e.status !== 'draft')
      setMode(hasPositioned ? 'polish' : 'setup')
    }
    initMode()
  }, [queryId])

  useEffect(() => {
    load()
  }, [queryId, refreshKey])

  const handleAddEvidence = async () => {
    try {
      if (addMode === 'new') {
        // 创建新 evidence
        const values = await form.validateFields()
        await createEvidence(queryId, values)
        message.success('已添加')
      } else {
        // 关联已有 evidence
        if (!selectedExistingEvidence) {
          message.warning('请选择要添加的 evidence')
          return
        }
        await attachEvidence(selectedExistingEvidence, queryId)
        message.success('已关联')
      }
      form.resetFields()
      setAddModalOpen(false)
      setAddMode('new')
      setSelectedExistingEvidence(null)
      load()
    } catch (e) {
      message.error(e.response?.data?.detail || '操作失败')
    }
  }

  // 打开手动分配位置弹窗
  const handleOpenManualAssign = () => {
    // 预填已有位置的 evidence
    const initialAssignments = {}
    evidences.forEach(ev => {
      if (ev.target_dia_id && ev.session_key) {
        initialAssignments[ev.id] = {
          session: ev.session_key,
          dia_id: ev.target_dia_id
        }
      }
    })
    setManualAssignments(initialAssignments)
    setManualAssignModalOpen(true)
  }

  // 手动分配位置并应用
  const handleManualAssign = async () => {
    try {
      // 检查是否所有 evidence 都已分配
      const unassigned = evidences.filter(ev => !manualAssignments[ev.id]?.dia_id)
      if (unassigned.length > 0) {
        message.warning('请为所有 evidence 分配位置')
        return
      }

      // 构建 assignments 数组
      const assignments = evidences.map(ev => ({
        evidence_id: ev.id,
        target_dia_id: manualAssignments[ev.id].dia_id
      }))

      // 调用批量手动分配 API（后端会智能处理：只对位置改变的 polished evidence 去除润色）
      await manualAssign(queryId, assignments)

      message.success('位置已分配')
      setManualAssignModalOpen(false)
      setManualAssignments({})
      setMode('polish')
      load()
    } catch (e) {
      message.error(e.response?.data?.detail || '分配失败')
    }
  }

  // 获取指定 session 的消息
  const getSessionMessages = (sessionKey) => {
    if (!sessionKey) return []
    return allMessages.filter(m => m.session_key === sessionKey)
  }

  // 更新某个 evidence 的 session 选择
  const handleSessionChange = (evidenceId, sessionKey) => {
    setManualAssignments(prev => ({
      ...prev,
      [evidenceId]: { session: sessionKey, dia_id: undefined }
    }))
  }

  // 更新某个 evidence 的 turn 选择
  const handleTurnChange = (evidenceId, diaId) => {
    setManualAssignments(prev => ({
      ...prev,
      [evidenceId]: { ...prev[evidenceId], dia_id: diaId }
    }))
  }

  // 预览分配（不改变状态）
  const handlePreviewAssign = async () => {
    try {
      setPreviewAssignments({}) // 先清空旧的预览结果
      const result = await previewAssign(queryId)
      console.log('Preview result:', result)
      const assignMap = {}
      result.assignments.forEach(a => {
        console.log('Assignment:', a)
        assignMap[a.evidence_id] = a
      })
      console.log('AssignMap:', assignMap)
      setPreviewAssignments(assignMap)
      setIsDirty(false) // 清除 dirty 标记
      message.success('预览分配成功，点击「确认并重新应用位置」以保存')
    } catch (e) {
      message.error(e.response?.data?.detail || '分配失败')
    }
  }

  // 确认并应用位置
  const handleConfirmAndApply = async () => {
    // 1. 检查是否有预览结果
    if (Object.keys(previewAssignments).length === 0) {
      message.error('请先点击「1. 自动分配位置（预览）」')
      return
    }

    // 2. 检查是否有已润色的 evidence（polished_text 不为空）
    const polishedEvidences = evidences.filter(e => e.polished_text && e.polished_text.trim() !== '')

    if (polishedEvidences.length > 0) {
      Modal.confirm({
        title: '检测到已润色的 Evidence',
        content: `有 ${polishedEvidences.length} 条 Evidence 已经润色过，重新应用位置将删除旧的润色结果。是否继续？`,
        okText: '确认',
        cancelText: '取消',
        onOk: () => applyPositions(polishedEvidences),
      })
    } else {
      await applyPositions([])
    }
  }

  const applyPositions = async (polishedEvidences) => {
    try {
      // 1. 删除已润色的 evidence
      if (polishedEvidences.length > 0) {
        for (const ev of polishedEvidences) {
          await unpolishEvidence(ev.id)
        }
      }

      // 2. 直接应用预览的分配结果
      for (const ev of evidences) {
        const assignment = previewAssignments[ev.id]
        if (assignment) {
          // 使用 setPosition API 来更新位置和状态
          await setPosition(ev.id, assignment.target_dia_id)
        }
      }

      message.success('位置应用成功')
      setPreviewAssignments({})
      setMode('polish')
      load()
      onPolishDone?.()
    } catch (e) {
      message.error(e.response?.data?.detail || '应用失败')
    }
  }

  // 编辑 evidence
  const handleEditEvidence = (evidence) => {
    setEditingEvidence(evidence)
    editForm.setFieldsValue({
      content: evidence.content,
      speaker: evidence.speaker || query.protagonist,
      constraints: evidence.constraints || [],
    })
    setEditModalOpen(true)
  }

  const handleUpdateEvidence = async () => {
    const values = await editForm.validateFields()
    await updateEvidence(editingEvidence.id, values)
    message.success('已更新')
    setEditModalOpen(false)
    setEditingEvidence(null)
    editForm.resetFields()
    setIsDirty(true) // 设置 dirty 标记
    load()
  }

  // 拖拽排序
  const handleDragStart = (e, index) => {
    setDraggedIndex(index)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e, index) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = async (e, dropIndex) => {
    e.preventDefault()
    if (draggedIndex === null || draggedIndex === dropIndex) {
      setDraggedIndex(null)
      return
    }
    const newEvidences = [...evidences]
    const [draggedItem] = newEvidences.splice(draggedIndex, 1)
    newEvidences.splice(dropIndex, 0, draggedItem)
    setDraggedIndex(null)
    for (let i = 0; i < newEvidences.length; i++) {
      await updateEvidence(newEvidences[i].id, { order: i })
    }
    load()
  }

  const handlePolish = async () => {
    try {
      // 收集所有 positioned 状态的 evidence IDs
      const positionedIds = evidences
        .filter(ev => ev.status === 'positioned')
        .map(ev => ev.id)

      if (positionedIds.length === 0) {
        message.warning('没有需要润色的 evidence')
        return
      }

      await batchPolish(queryId, positionedIds)
      message.success('润色完成')
      load()
      onPolishDone?.()
    } catch (e) {
      message.error(e.response?.data?.detail || '润色失败')
    }
  }

  if (!query) return null

  const evidences = query.evidences?.sort((a, b) => a.order - b.order) || []
  const allPolished = evidences.length > 0 && evidences.every(ev => ev.polished_text)

  return (
    <>
      <Sider width={400} style={{ background: '#fff', borderLeft: '1px solid #f0f0f0', padding: 16, height: 'calc(100vh - 64px)' }}>
        <Card
          size="small"
          title={mode === 'setup' ? 'Evidences 草稿' : '润色确认'}
          extra={
            <Space>
              {mode === 'setup' && allPolished && (
                <Button size="small" onClick={() => setMode('polish')}>
                  进入详情页
                </Button>
              )}
              {mode === 'polish' && (
                <Button size="small" onClick={() => setMode('setup')}>返回设置</Button>
              )}
              <Button size="small" icon={<CloseOutlined />} onClick={onClose} />
            </Space>
          }
          style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
          bodyStyle={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '16px' }}>
            <div style={{ flexShrink: 0 }}>
              <strong>Query:</strong> {query.query_text}
            </div>

            {mode === 'setup' && (
              <>
                <div style={{ flexShrink: 0 }}>
                  <Button type="dashed" block icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)}>
                    添加 Evidence
                  </Button>
                </div>

                <div style={{ flex: 1, overflow: 'auto', minHeight: 0, paddingRight: '8px' }}>
                  <List
                  size="small"
                  header={<strong>Evidence 列表（可拖拽）</strong>}
                  dataSource={evidences}
                  renderItem={(ev, idx) => {
                    const preview = previewAssignments[ev.id]
                    return (
                      <div
                        key={ev.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, idx)}
                        onDragOver={(e) => handleDragOver(e, idx)}
                        onDrop={(e) => handleDrop(e, idx)}
                        style={{
                          cursor: 'grab',
                          opacity: draggedIndex === idx ? 0.4 : 1,
                          borderTop: draggedIndex !== null && draggedIndex !== idx ? '2px solid transparent' : undefined,
                        }}
                      >
                        <List.Item
                          onClick={() => ev.target_dia_id && onClickEvidence?.(ev.id, ev.target_dia_id)}
                          style={{ cursor: ev.target_dia_id ? 'pointer' : 'default', pointerEvents: draggedIndex !== null ? 'none' : undefined }}
                          actions={[
                            <Button
                              size="small"
                              icon={<EditOutlined />}
                              onClick={(e) => { e.stopPropagation(); handleEditEvidence(ev) }}
                            />,
                            <Popconfirm title="确认删除？" onConfirm={() => deleteEvidence(ev.id).then(() => { setIsDirty(true); load() })}>
                              <Button size="small" danger icon={<DeleteOutlined />} />
                            </Popconfirm>
                          ]}
                        >
                          <Space direction="vertical" size={0} style={{ width: '100%' }}>
                            <Space>
                              <Tag>#{idx + 1}</Tag>
                              <Tag color={(ev.speaker || query.protagonist) === query.protagonist ? 'blue' : 'purple'}>
                                {ev.speaker || query.protagonist}
                              </Tag>
                              {ev.target_dia_id && <Tag color="green">{ev.target_dia_id}</Tag>}
                              {preview && <Tag color="orange">预览: {preview.target_dia_id}</Tag>}
                            </Space>
                            <div>{ev.content}</div>
                            {ev.constraints?.length > 0 && (
                              <div style={{ fontSize: 11, color: '#666', marginTop: 4, background: '#ffebee', padding: '4px 8px', borderRadius: 4 }}>
                                {ev.constraints.map((c, cidx) => {
                                  const targetEv = evidences.find(e => e.id === c.target_evidence_id)
                                  const targetName = targetEv ? `#${evidences.indexOf(targetEv) + 1}` : '未知'
                                  const parts = []
                                  if (c.same_session !== null && c.same_session !== undefined) {
                                    parts.push(c.same_session ? '在同一 session' : '不在同一 session')
                                  }
                                  if (c.min_turns !== null && c.min_turns !== undefined) {
                                    parts.push(`距离最小 ${c.min_turns} turns`)
                                  }
                                  if (c.max_turns !== null && c.max_turns !== undefined) {
                                    parts.push(`距离最大 ${c.max_turns} turns`)
                                  }
                                  return (
                                    <div key={cidx}>
                                      约束 {cidx + 1}: 与 {targetName} {parts.join('，')}
                                    </div>
                                  )
                                })}
                              </div>
                            )}
                          </Space>
                        </List.Item>
                      </div>
                    )
                  }}
                />
                </div>

                <div style={{ flexShrink: 0, marginTop: '16px' }}>
                <Button
                  type="default"
                  block
                  icon={<EyeOutlined />}
                  onClick={handlePreviewAssign}
                  disabled={true}
                >
                  1. 自动分配位置（预览）
                </Button>

                <Button
                  type="primary"
                  block
                  icon={<ThunderboltOutlined />}
                  onClick={handleConfirmAndApply}
                  disabled={true}
                >
                  2. 确认并重新应用位置（会删除旧润色）
                </Button>

                <Button
                  type="default"
                  block
                  onClick={handleOpenManualAssign}
                  disabled={evidences.length === 0}
                >
                  手动设置位置并应用（会删除旧润色）
                </Button>
                </div>
              </>
            )}

            {mode === 'polish' && (
              <>
                <div style={{ flex: 1, overflow: 'auto', minHeight: 0, paddingRight: '8px' }}>
                <List
                  size="small"
                  dataSource={evidences}
                  renderItem={(ev, idx) => {
                    const getStatusColor = (status) => {
                      if (status === 'positioned') return 'processing'
                      if (status === 'polished') return 'success'
                      if (status === 'confirmed') return 'success'
                      return 'default'
                    }

                    return (
                      <Card
                        size="small"
                        style={{ marginBottom: 8 }}
                      >
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <Space>
                            <Tag>#{idx + 1}</Tag>
                            <Tag color={(ev.speaker || query.protagonist) === query.protagonist ? 'blue' : 'purple'}>
                              {ev.speaker || query.protagonist}
                            </Tag>
                            <Tag color="cyan">{ev.target_dia_id}</Tag>
                            <Tag color={getStatusColor(ev.status)}>{ev.status}</Tag>
                          </Space>
                          <div
                            style={{ cursor: 'pointer' }}
                            onClick={() => onClickEvidence?.(ev.id, ev.target_dia_id)}
                          >
                            <strong>Evidence:</strong> {ev.content}
                          </div>
                          {(() => {
                            const polishedMsg = polishedMessages.find(m => m.dia_id === ev.target_dia_id)
                            if (polishedMsg) {
                              return (
                                <>
                                  <div style={{ fontSize: 12, color: '#999' }}>原文: {polishedMsg.original_text}</div>
                                  <div style={{ fontSize: 12, color: '#52c41a' }}>润色: {polishedMsg.final_polished_text}</div>
                                </>
                              )
                            }
                            return null
                          })()}
                          <Space>
                            <Button
                              size="small"
                              icon={<EditOutlined />}
                              onClick={() => {
                                setEditingEvidence(ev)
                                editForm.setFieldsValue({ content: ev.content })
                                setPolishEditModalOpen(true)
                              }}
                            >
                              编辑
                            </Button>
                          </Space>
                        </Space>
                      </Card>
                    )
                  }}
                />
                </div>

                <div style={{ flexShrink: 0, marginTop: '16px' }}>
                <Button
                  type="primary"
                  block
                  icon={<ThunderboltOutlined />}
                  onClick={handlePolish}
                >
                  批量润色
                </Button>
                </div>
              </>
            )}
          </div>
        </Card>
      </Sider>

      <Modal
        title="编辑 Evidence"
        open={editModalOpen}
        onOk={handleUpdateEvidence}
        onCancel={() => {
          setEditModalOpen(false)
          setEditingEvidence(null)
          editForm.resetFields()
        }}
        width={600}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="content" label="Evidence 内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>

          <Form.Item name="speaker" label="说话人">
            <Select>
              <Select.Option value={query.protagonist}>{query.protagonist}</Select.Option>
              {speakers && (
                <Select.Option value={speakers.speaker_a === query.protagonist ? speakers.speaker_b : speakers.speaker_a}>
                  对方 ({speakers.speaker_a === query.protagonist ? speakers.speaker_b : speakers.speaker_a})
                </Select.Option>
              )}
            </Select>
          </Form.Item>

          <Form.Item label="约束条件">
            <Form.List name="constraints">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(field => (
                    <Card key={field.key} size="small" style={{ marginBottom: 8 }}>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'target_evidence_id']}
                          label="目标 Evidence"
                          rules={[{ required: true }]}
                        >
                          <Select placeholder="选择目标 Evidence">
                            {evidences
                              .filter(e => e.id !== editingEvidence?.id)
                              .map(e => (
                                <Select.Option key={e.id} value={e.id}>
                                  {e.content.substring(0, 30)}...
                                </Select.Option>
                              ))}
                          </Select>
                        </Form.Item>

                        <Form.Item
                          {...field}
                          name={[field.name, 'same_session']}
                          label="是否在同一 Session"
                        >
                          <Select allowClear placeholder="不限制">
                            <Select.Option value={true}>必须在同一 Session</Select.Option>
                            <Select.Option value={false}>必须不在同一 Session</Select.Option>
                          </Select>
                        </Form.Item>

                        <Space>
                          <Form.Item
                            {...field}
                            name={[field.name, 'min_turns']}
                            label="最小间隔 (turns)"
                          >
                            <InputNumber min={0} placeholder="不限制" />
                          </Form.Item>

                          <Form.Item
                            {...field}
                            name={[field.name, 'max_turns']}
                            label="最大间隔 (turns)"
                          >
                            <InputNumber min={0} placeholder="不限制" />
                          </Form.Item>
                        </Space>

                        <Button danger size="small" onClick={() => remove(field.name)}>
                          删除此约束
                        </Button>
                      </Space>
                    </Card>
                  ))}

                  <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add()}>
                    添加约束条件
                  </Button>
                </>
              )}
            </Form.List>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="添加 Evidence"
        open={addModalOpen}
        onOk={handleAddEvidence}
        onCancel={() => {
          setAddModalOpen(false)
          form.resetFields()
          setAddMode('new')
          setSelectedExistingEvidence(null)
        }}
        width={600}
      >
        <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
          <div>选择添加方式：</div>
          <Select
            value={addMode}
            onChange={(value) => {
              setAddMode(value)
              form.resetFields()
              setSelectedExistingEvidence(null)
            }}
            style={{ width: '100%' }}
          >
            <Select.Option value="new">创建新 Evidence</Select.Option>
            <Select.Option value="existing">关联已有 Evidence（已 positioned/polished）</Select.Option>
          </Select>
        </Space>

        {addMode === 'new' ? (
          <Form form={form} layout="vertical">
          <Form.Item name="content" label="Evidence 内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="speaker" label="说话人">
            <Select placeholder="默认为主角">
              <Select.Option value={query.protagonist}>{query.protagonist}</Select.Option>
              {speakers && (
                <Select.Option value={speakers.speaker_a === query.protagonist ? speakers.speaker_b : speakers.speaker_a}>
                  对方 ({speakers.speaker_a === query.protagonist ? speakers.speaker_b : speakers.speaker_a})
                </Select.Option>
              )}
            </Select>
          </Form.Item>

          <Form.Item label="约束条件">
            <Form.List name="constraints">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(field => (
                    <Card key={field.key} size="small" style={{ marginBottom: 8 }}>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'target_evidence_id']}
                          label="目标 Evidence"
                          rules={[{ required: true }]}
                        >
                          <Select placeholder="选择目标 Evidence">
                            {evidences.map(e => (
                                <Select.Option key={e.id} value={e.id}>
                                  {e.content.substring(0, 30)}...
                                </Select.Option>
                              ))}
                          </Select>
                        </Form.Item>

                        <Form.Item
                          {...field}
                          name={[field.name, 'same_session']}
                          label="是否在同一 Session"
                        >
                          <Select allowClear placeholder="不限制">
                            <Select.Option value={true}>必须在同一 Session</Select.Option>
                            <Select.Option value={false}>必须不在同一 Session</Select.Option>
                          </Select>
                        </Form.Item>

                        <Space>
                          <Form.Item
                            {...field}
                            name={[field.name, 'min_turns']}
                            label="最小间隔 (turns)"
                          >
                            <InputNumber min={0} placeholder="不限制" />
                          </Form.Item>

                          <Form.Item
                            {...field}
                            name={[field.name, 'max_turns']}
                            label="最大间隔 (turns)"
                          >
                            <InputNumber min={0} placeholder="不限制" />
                          </Form.Item>
                        </Space>
                      </Space>

                      <Button danger size="small" onClick={() => remove(field.name)}>
                        删除此约束
                      </Button>
                    </Card>
                  ))}

                  <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add()}>
                    添加约束条件
                  </Button>
                </>
              )}
            </Form.List>
          </Form.Item>
        </Form>
        ) : (
          <div>
            <div style={{ marginBottom: 8 }}>选择要关联的 Evidence：</div>
            <Select
              placeholder="选择已有的 positioned/polished evidence"
              style={{ width: '100%' }}
              value={selectedExistingEvidence}
              onChange={setSelectedExistingEvidence}
              showSearch
              optionFilterProp="children"
            >
              {allEvidences.map(ev => (
                <Select.Option key={ev.id} value={ev.id}>
                  <Space direction="vertical" size={0}>
                    <div>
                      <Tag color={ev.status === 'positioned' ? 'processing' : 'success'}>{ev.status}</Tag>
                      <Tag color="cyan">{ev.target_dia_id}</Tag>
                      {ev.speaker && <Tag>{ev.speaker}</Tag>}
                    </div>
                    <div>{ev.content}</div>
                  </Space>
                </Select.Option>
              ))}
            </Select>
            {allEvidences.length === 0 && (
              <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                当前没有可用的已 positioned/polished 的 evidence
              </div>
            )}
          </div>
        )}
      </Modal>

      <Modal
        title="编辑并润色 Evidence"
        open={polishEditModalOpen}
        okText="保存并单独润色"
        onOk={async () => {
          try {
            const values = await editForm.validateFields()
            await updateEvidence(editingEvidence.id, { content: values.content })
            message.success('已更新')
            await repolish(editingEvidence.id)
            message.success('润色完成')
            setPolishEditModalOpen(false)
            setEditingEvidence(null)
            editForm.resetFields()
            load()
            onPolishDone?.()
          } catch (e) {
            message.error(e.response?.data?.detail || '操作失败')
          }
        }}
        onCancel={() => {
          setPolishEditModalOpen(false)
          setEditingEvidence(null)
          editForm.resetFields()
        }}
        footer={[
          <Button key="cancel" onClick={() => {
            setPolishEditModalOpen(false)
            setEditingEvidence(null)
            editForm.resetFields()
          }}>
            取消
          </Button>,
          (editingEvidence?.status === 'polished' || editingEvidence?.status === 'confirmed') && (
            <Popconfirm
              key="unpolish"
              title="确定要去除润色吗？"
              description="将去除该 evidence 的润色内容，保留位置信息"
              onConfirm={async () => {
                try {
                  await unpolishEvidence(editingEvidence.id)
                  message.success('已去除润色')
                  setPolishEditModalOpen(false)
                  setEditingEvidence(null)
                  editForm.resetFields()
                  load()
                  onPolishDone?.()
                } catch (e) {
                  message.error(e.response?.data?.detail || '操作失败')
                }
              }}
            >
              <Button danger>去除润色</Button>
            </Popconfirm>
          ),
          <Button key="ok" type="primary" onClick={async () => {
            try {
              const values = await editForm.validateFields()
              await updateEvidence(editingEvidence.id, { content: values.content })
              message.success('已更新')
              await repolish(editingEvidence.id)
              message.success('润色完成')
              setPolishEditModalOpen(false)
              setEditingEvidence(null)
              editForm.resetFields()
              load()
              onPolishDone?.()
            } catch (e) {
              message.error(e.response?.data?.detail || '操作失败')
            }
          }}>
            保存并单独润色
          </Button>
        ]}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="content" label="Evidence 内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 手动分配位置弹窗 */}
      <Modal
        title="手动设置位置并应用"
        open={manualAssignModalOpen}
        onOk={handleManualAssign}
        onCancel={() => {
          setManualAssignModalOpen(false)
          setManualAssignments({})
        }}
        okText="确认分配"
        cancelText="取消"
        width={800}
      >
        <List
          size="small"
          dataSource={evidences}
          renderItem={(ev, idx) => (
            <List.Item key={ev.id}>
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <div>
                  <Tag>#{idx + 1}</Tag>
                  <strong>{ev.content}</strong>
                </div>
                <Space style={{ width: '100%' }}>
                  <Select
                    placeholder="选择 Session"
                    style={{ width: 150 }}
                    value={manualAssignments[ev.id]?.session}
                    onChange={(value) => handleSessionChange(ev.id, value)}
                  >
                    {sessionKeys.map(key => (
                      <Select.Option key={key} value={key}>{key}</Select.Option>
                    ))}
                  </Select>
                  <Select
                    placeholder="选择 Turn"
                    style={{ width: 500 }}
                    value={manualAssignments[ev.id]?.dia_id}
                    onChange={(value) => handleTurnChange(ev.id, value)}
                    disabled={!manualAssignments[ev.id]?.session}
                  >
                    {getSessionMessages(manualAssignments[ev.id]?.session).map(msg => (
                      <Select.Option key={msg.dia_id} value={msg.dia_id}>
                        {msg.dia_id} - {msg.speaker}: {msg.text.substring(0, 50)}{msg.text.length > 50 ? '...' : ''}
                      </Select.Option>
                    ))}
                  </Select>
                </Space>
              </Space>
            </List.Item>
          )}
        />
      </Modal>
    </>
  )
}

