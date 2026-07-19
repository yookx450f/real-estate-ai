'use client'

import { useState, useEffect } from 'react'
import ChatInterface from '@/components/ChatInterface'

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [accessToken, setAccessToken] = useState<string | null>(null)

  // ローカルストレージからトークンを取得
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      setAccessToken(token)
      setIsAuthenticated(true)
    }
  }, [])

  const handleLogin = (token: string) => {
    localStorage.setItem('access_token', token)
    setAccessToken(token)
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    setAccessToken(null)
    setIsAuthenticated(false)
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* ヘッダー */}
      <header style={{
        padding: '0.75rem 1.5rem',
        borderBottom: '1px solid #e2e8f0',
        backgroundColor: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <h1 style={{ margin: 0, fontSize: '1.25rem', color: '#2563eb' }}>
          不動産法律AI
        </h1>
        <button
          className="btn"
          onClick={handleLogout}
          style={{ fontSize: '0.875rem' }}
        >
          ログアウト
        </button>
      </header>

      {/* メインコンテンツ */}
      <main style={{ flex: 1, overflow: 'hidden' }}>
        <ChatInterface accessToken={accessToken!} onLogout={handleLogout} />
      </main>
    </div>
  )
}

// ログインページ
function LoginPage({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const formData = new FormData()
      formData.append('username', email)
      formData.append('password', password)

      const response = await fetch('/api/auth/login', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('認証に失敗しました')
      }

      const data = await response.json()
      onLogin(data.access_token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <form onSubmit={handleLogin} style={{
        background: 'white',
        padding: '2rem',
        borderRadius: '12px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        width: '100%',
        maxWidth: '400px',
      }}>
        <h1 style={{ textAlign: 'center', marginBottom: '1.5rem', color: '#2563eb' }}>
          不動産法律AI
        </h1>
        {error && (
          <div style={{
            color: '#ef4444',
            backgroundColor: '#fef2f2',
            padding: '0.75rem',
            borderRadius: '6px',
            marginBottom: '1rem',
            fontSize: '0.875rem',
          }}>
            {error}
          </div>
        )}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
            メールアドレス
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              fontSize: '1rem',
            }}
          />
        </div>
        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
            パスワード
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              fontSize: '1rem',
            }}
          />
        </div>
        <button
          type="submit"
          disabled={isLoading}
          style={{
            width: '100%',
            padding: '0.75rem',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '1rem',
            fontWeight: 500,
            cursor: isLoading ? 'not-allowed' : 'pointer',
          }}
        >
          {isLoading ? '認証中...' : 'ログイン'}
        </button>
        <p style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.75rem', color: '#64748b' }}>
          初期アカウント: admin@example.com / admin123
        </p>
      </form>
    </div>
  )
}
