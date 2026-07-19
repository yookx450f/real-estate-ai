import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: '不動産法律AIシステム',
  description: '宅地建物取引士試験対応の法律AIチャットシステム',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  )
}
