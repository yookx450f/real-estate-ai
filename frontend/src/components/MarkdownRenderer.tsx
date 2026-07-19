'use client'

import React from 'react'

interface MarkdownRendererProps {
  content: string
}

/**
 * 簡易Markdownレンダラー
 * H3 (#), H4 (##), lists, bold, paragraphs をサポート
 */
export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const lines = content.split('\n')
  const elements: React.ReactNode[] = []
  let listItems: string[] = []

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} style={{ marginLeft: '1rem', marginBottom: '0.5rem', paddingLeft: '1rem' }}>
          {listItems.map((item, idx) => (
            <li key={idx} style={{ marginBottom: '0.25rem' }}>
              {renderInlineMarkdown(item)}
            </li>
          ))}
        </ul>
      )
      listItems = []
    }
  }

  const renderInlineMarkdown = (text: string): React.ReactNode => {
    // **text** を太字に変換
    const parts: React.ReactNode[] = []
    const regex = /\*\*(.+?)\*\*/g
    let lastIndex = 0
    let match
    
    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(<span key={`text-${lastIndex}`}>{text.slice(lastIndex, match.index)}</span>)
      }
      parts.push(<strong key={`bold-${match.index}`}>{match[1]}</strong>)
      lastIndex = match.index + match[0].length
    }
    
    if (lastIndex < text.length) {
      parts.push(<span key={`text-${lastIndex}`}>{text.slice(lastIndex)}</span>)
    }
    
    return parts.length > 0 ? <>{parts}</> : <>{text}</>
  }

  let keyCounter = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    
    // 空行
    if (line.trim() === '') {
      flushList()
      elements.push(<div key={keyCounter++} style={{ height: '0.5rem' }} />)
      continue
    }
    
    // H3 (###)
    if (line.startsWith('### ')) {
      flushList()
      elements.push(
        <h3 key={keyCounter++} style={{ marginTop: '1rem', marginBottom: '0.5rem', fontSize: '1.1rem', fontWeight: 600 }}>
          {renderInlineMarkdown(line.slice(4))}
        </h3>
      )
      continue
    }
    
    // H4 (####)
    if (line.startsWith('#### ')) {
      flushList()
      elements.push(
        <h4 key={keyCounter++} style={{ marginTop: '0.75rem', marginBottom: '0.5rem', fontSize: '1rem', fontWeight: 600 }}>
          {renderInlineMarkdown(line.slice(5))}
        </h4>
      )
      continue
    }
    
    // リスト項目 (* **text***)
    const listMatch = line.match(/^\*\s\*\*(.+?)\*\*:?\s*(.*)$/)
    if (listMatch) {
      listItems.push(`${listMatch[1]}: ${listMatch[2]}`.trim())
      continue
    }
    
    // 通常段落
    flushList()
    elements.push(
      <p key={keyCounter++} style={{ margin: '0.25rem 0', lineHeight: 1.6 }}>
        {renderInlineMarkdown(line)}
      </p>
    )
  }
  
  flushList()

  return <>{elements}</>
}
