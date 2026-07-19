# 不動産法律AIシステム

宅地建物取引士試験対応の法律AIチャットシステム。RAG（Retrieval Augmented Generation）技術を活用し、正確な法令情報に基づいた回答を提供します。

## システム構成

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  クライアント │────▶│   API層     │────▶│   AI層      │
│ (React/Next) │     │ (FastAPI)   │     │ (RAG+LLM)   │
└─────────────┘     └─────────────┘     └─────────────┘
                                       │         │
┌─────────────┐     ┌─────────────┐     └────┬────┘
│  PostgreSQL │◀────│  データ層   │◀──────────┘
│  (メタDB)   │     │  (Qdrant)   │
└─────────────┘     └─────────────┘
```

## 技術スタック

| 層 | 技術 |
|----|------|
| バックエンド | FastAPI (Python 3.12) |
| フロントエンド | Next.js 14 + React 18 |
| ベクトルDB | Qdrant |
| 関係DB | PostgreSQL 16 |
| LLM | gemma-4-26B-A4B-it-MLX-8bit |
| コンテナ | Docker + docker-compose |

## 環境構築

### 1. 環境変数の設定

```bash
cp .env.example .env
```

`.env`ファイルを編集して、LLMのベースURL等を設定してください。

### 2. Docker Composeでの起動

```bash
docker-compose up -d
```

### 3. アクセス

- フロントエンド: http://localhost
- API: http://localhost:8000/api
- Swagger UI: http://localhost:8000/docs
- Qdrant UI: http://localhost:6333

## 初期アカウント

- メールアドレス: `admin@example.com`
- パスワード: `admin123`

## APIドキュメント

Swagger UIでAPIドキュメントを確認できます: http://localhost:8000/docs

### 主要エンドポイント

| API | メソッド | パス | 説明 |
|-----|----------|------|------|
| 認証 | POST | /api/auth/login | ログイン |
| 認証 | POST | /api/auth/register | ユーザー登録 |
| チャット | POST | /api/chat/ | AIへの質問 |
| ドキュメント | POST | /api/documents/upload | ドキュメントアップロード |
| ドキュメント | GET | /api/documents/ | ドキュメント一覧 |

## ドキュメント登録

### 手動登録

`documents/reference/`ディレクトリにMarkdownファイルを配置します。

### API経由登録

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@documents/reference/taikoken_law_overview.md" \
  -F "category=taikoken" \
  -H "Authorization: Bearer <token>"
```

## ディレクトリ構造

```
real-estate-ai/
├── docker-compose.yml
├── .env.example
├── nginx.conf
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── api/
│       │   ├── auth.py
│       │   ├── chat.py
│       │   └── documents.py
│       └── core/
│           ├── llm.py
│           └── rag.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── page.tsx
│       │   ├── layout.tsx
│       │   └── globals.css
│       └── components/
│           └── ChatInterface.tsx
└── documents/
    └── reference/
        ├── taikoken_law_overview.md
        ├── taikoken_contract_types.md
        └── taikoken_exam_study_guide.md
```

## 開発

### バックエンド

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### フロントエンド

```bash
cd frontend
npm install
npm run dev
```

## 今後の計画

- [ ] PostgreSQLとの連携実装
- [ ] 埋め込みモデルの統合（sentence-transformers）
- [ ] 会話履歴の永続化
- [ ] 管理画面の実装
- [ ] 法令データの拡充（借地借家法、民法等）
