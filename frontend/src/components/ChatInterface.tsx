'use client'

import { useState, useRef, useEffect } from 'react'
import MarkdownRenderer from './MarkdownRenderer'

interface Source {
  filename: string
  text: string
  score: number
  category?: string
  source_url?: string
  // エビデンス情報（新追加）
  full_text?: string
  law_name?: string
  article_number?: string
  section?: string
  document_title?: string
  evidence_text?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  timestamp: string
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at: string
  updated_at: string
  message_count?: number
}

interface ChatInterfaceProps {
  accessToken: string
  onLogout: () => void
}

const API_BASE = '/api'

export default function ChatInterface({ accessToken, onLogout }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null)
  const [showSidebar, setShowSidebar] = useState(true)
  const [isCreatingNew, setIsCreatingNew] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 会話一覧をロード
  useEffect(() => {
    loadConversations()
  }, [])

  // 新しいメッセージが表示されたらスクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadConversations = async () => {
    try {
      const response = await fetch(`${API_BASE}/chat/conversations`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setConversations(data)
      }
    } catch (error) {
      console.error('会話一覧の取得に失敗しました:', error)
    }
  }

  const loadConversation = async (id: string) => {
    setIsCreatingNew(false)
    setConversationId(id)
    setActiveConversation(null)
    setMessages([])
    
    try {
      const response = await fetch(`${API_BASE}/chat/conversations/${id}`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setActiveConversation(data)
        setMessages(data.messages || [])
      }
    } catch (error) {
      console.error('会話をロード出来ませんでした:', error)
    }
  }

  const handleNewChat = async () => {
    setIsCreatingNew(true)
    setConversationId(null)
    setActiveConversation(null)
    setMessages([])
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE}/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_id: conversationId,
        }),
      })

      if (!response.ok) {
        // 401エラーの場合は認証エラー、それ以外のエラーは処理エラー
        if (response.status === 401) {
          throw new Error('認証エラー：ログインが必要です。')
        }
        const errorData = await response.json().catch(() => ({ detail: 'チャット処理に失敗しました' }))
        throw new Error(errorData.detail || 'チャット処理に失敗しました')
      }

      const data = await response.json()

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        timestamp: new Date().toISOString(),
      }

      setMessages(prev => [...prev, assistantMessage])
      
      // 会話IDを更新
      if (data.conversation_id && data.conversation_id !== conversationId) {
        setConversationId(data.conversation_id)
      }

      // 会話一覧を更新
      loadConversations()
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: error instanceof Error ? error.message : 'エラーが発生しました。もう一度お試しください。',
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    
    if (!confirm('この会話を削除しますか？')) return

    try {
      const response = await fetch(`${API_BASE}/chat/conversations/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      })

      if (response.ok) {
        // 現在アクティブな会話を削除した場合
        if (conversationId === id) {
          handleNewChat()
        }
        // 会話一覧を更新
        loadConversations()
      }
    } catch (error) {
      console.error('会話の削除に失敗しました:', error)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 参照元情報をフォーマットして表示
  const renderSourceInfo = (source: Source) => {
    const hasEvidenceInfo = source.law_name || source.article_number || source.evidence_text
    
    return (
      <div key={source.filename} style={{ marginBottom: '1rem' }}>
        {/* ドキュメントタイトル */}
        {source.document_title && (
          <div style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem' }}>
            {source.document_title}
          </div>
        )}
        
        {/* ファイル名 */}
        <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
          {source.filename}
        </div>
        
        {/* 関連度 */}
        <div style={{ fontSize: '0.75rem', opacity: 0.8, marginTop: '0.25rem' }}>
          関連度: {(source.score * 100).toFixed(1)}%
        </div>
        
        {/* 出典URL */}
        {source.source_url && (
          <div style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
            出典: {source.source_url}
          </div>
        )}
        
        {/* エビデンス情報（法令名、条文番号、参照文章）*/}
        {hasEvidenceInfo && (
          <div style={{ 
            marginTop: '0.5rem', 
            padding: '0.5rem', 
            backgroundColor: 'rgba(255,255,255,0.1)', 
            borderRadius: '4px',
            border: '1px solid rgba(255,255,255,0.15)'
          }}>
            {/* 法令名と条文番号 */}
            {(source.law_name || source.article_number) && (
              <div style={{ marginBottom: '0.25rem' }}>
                <strong style={{ fontSize: '0.8rem' }}>根拠となる法令:</strong>{' '}
                {source.law_name && <span>{source.law_name}</span>}
                {source.law_name && source.article_number && <span> </span>}
                {source.article_number && <span>第{source.article_number}条</span>}
                {source.section && <span> 第{source.section}号</span>}
              </div>
            )}
            
            {/* 参照した文章の全文 */}
            {source.evidence_text && (
              <div style={{ marginTop: '0.25rem' }}>
                <strong style={{ fontSize: '0.8rem' }}>参照した文章:</strong>
                <div style={{ 
                  marginTop: '0.25rem', 
                  padding: '0.5rem', 
                  backgroundColor: 'rgba(0,0,0,0.2)', 
                  borderRadius: '3px',
                  fontSize: '0.8rem',
                  lineHeight: '1.6',
                  whiteSpace: 'pre-wrap'
                }}>
                  {source.evidence_text}
                </div>
              </div>
            )}
            
            {/* full_text（エビデンスがない場合は代替として表示）*/}
            {!source.evidence_text && source.full_text && (
              <div style={{ marginTop: '0.25rem' }}>
                <strong style={{ fontSize: '0.8rem' }}>参照した文章:</strong>
                <div style={{ 
                  marginTop: '0.25rem', 
                  padding: '0.5rem', 
                  backgroundColor: 'rgba(0,0,0,0.2)', 
                  borderRadius: '3px',
                  fontSize: '0.8rem',
                  lineHeight: '1.6',
                  whiteSpace: 'pre-wrap'
                }}>
                  {source.full_text}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 60px)' }}>
      {/* サイドバー */}
      {showSidebar && (
        <div style={{
          width: '280px',
          backgroundColor: '#f8fafc',
          borderRight: '1px solid #e2e8f0',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid #e2e8f0' }}>
            <button
              className="btn btn-primary"
              onClick={handleNewChat}
              style={{ width: '100%' }}
            >
              + 新しいチャット
            </button>
          </div>
          
          <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
            <h3 style={{ fontSize: '0.75rem', color: '#64748b', padding: '0.5rem' }}>
              会話履歴
            </h3>
            {conversations.length === 0 ? (
              <p style={{ fontSize: '0.875rem', color: '#64748b', padding: '0.5rem' }}>
                会話がまだありません
              </p>
            ) : (
              <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {conversations.map((conv) => (
                  <li key={conv.id}>
                    <div
                      className={`conversation-item ${conversationId === conv.id ? 'active' : ''}`}
                      onClick={() => loadConversation(conv.id)}
                      style={{
                        padding: '0.75rem',
                        cursor: 'pointer',
                        borderRadius: '6px',
                        marginBottom: '0.25rem',
                        backgroundColor: conversationId === conv.id ? '#eff6ff' : 'transparent',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                          {conv.title}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                          {conv.message_count || 0} メッセージ
                        </div>
                      </div>
                      <button
                        onClick={(e) => handleDeleteConversation(conv.id, e)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#94a3b8',
                          cursor: 'pointer',
                          padding: '0.25rem',
                          fontSize: '1rem',
                        }}
                        title="削除"
                      >
                        ×
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* メインチャットエリア */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* ヘッダー */}
        <div style={{
          padding: '0.75rem 1rem',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'white',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              style={{
                background: 'none',
                border: '1px solid #e2e8f0',
                borderRadius: '4px',
                padding: '0.25rem 0.5rem',
                cursor: 'pointer',
              }}
            >
              {showSidebar ? '←' : '→'}
            </button>
            <h2 style={{ margin: 0, fontSize: '1rem' }}>
              {isCreatingNew ? '新しいチャット' : (activeConversation?.title || 'チャット')}
            </h2>
          </div>
        </div>

        {/* メッセージ一覧 */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
          {messages.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '3rem',
              color: '#64748b',
            }}>
              <h2 style={{ marginBottom: '1rem', color: '#2563eb' }}>
                不動産法律AIシステム
              </h2>
              <p>宅建関連の質問をお気軽にどうぞ</p>
              <div style={{
                marginTop: '2rem',
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '1rem',
                maxWidth: '500px',
                margin: '2rem auto 0',
              }}>
                {[
                  '重要事項説明について教えてください',
                  '媒介契約の効力は？',
                  '手付金返還のルールは？',
                  '9つの事項とは？',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    className="btn"
                    onClick={() => setInput(suggestion)}
                    style={{ textAlign: 'left' }}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`message ${message.role}`}
                  style={{
                    display: 'flex',
                    justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  <div style={{
                    maxWidth: '80%',
                    padding: '1rem',
                    borderRadius: '12px',
                    backgroundColor: message.role === 'user' ? '#2563eb' : '#f1f5f9',
                    color: message.role === 'user' ? 'white' : 'inherit',
                  }}>
                    <MarkdownRenderer content={message.content} />
                    {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                      <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem' }}>
                          📚 参照元（エビデンス）
                        </h4>
                        {message.sources.map((source, index) => renderSourceInfo(source))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 入力エリア */}
        <div style={{
          padding: '1rem',
          borderTop: '1px solid #e2e8f0',
          backgroundColor: 'white',
        }}>
          <div style={{
            display: 'flex',
            gap: '0.5rem',
            maxWidth: '800px',
            margin: '0 auto',
          }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="質問を入力してください..."
              rows={1}
              disabled={isLoading}
              style={{
                flex: 1,
                padding: '0.75rem',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '1rem',
                resize: 'none',
                outline: 'none',
              }}
            />
            <button
              className="send-button"
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: isLoading || !input.trim() ? 'not-allowed' : 'pointer',
                fontWeight: 500,
              }}
            >
              {isLoading ? '処理中...' : '送信'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
