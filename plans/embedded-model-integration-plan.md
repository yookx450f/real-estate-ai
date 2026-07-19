# 埋め込みモデル統合計画

## 概要

現在のRAGシステムでは、テキスト埋め込みがダミー値（`[0.1] * 768`）で実装されており、実際のベクトル検索が機能しません。sentence-transformers等の埋め込みモデルを統合し、正確なセマンティック検索を可能にします。

## 現状分析

### 問題点
1. [`llm.py`](backend/app/core/llm.py:36-40) の `embed_texts()` メソッドがダミー値を返す
2. [`rag.py`](backend/app/core/rag.py:83) の `store_document()` がダミー埋め込みベクトルを使用
3. [`rag.py`](backend/app/core/rag.py:116) の `search()` がダミークエリ埋め込みを使用
4. `pyproject.toml` に埋め込みモデル関連の依存関係がない

## 解決策

### 選択肢比較

| モデル | 次元 | メリット | デメリット |
|--------|------|----------|------------|
| **langchain-huggingface** | 768 | ローカル実行可能、日本語対応モデル豊富 | 初期読み込みに時間 |
| **Qdrant内蔵埋め込み** | 768 | サーバーサイドで自動生成 | 外部依存なし |
| **OpenAI embeddings** | 1536 | 高精度 | 外部API依存、コスト |

### 推奨方案: langchain-huggingface 統合

**理由:**
- ローカルLLMと同じ環境で実行可能
- 日本語に強いモデル（`sentence-transformers/japanese-all-v3`等）が存在
- 外部API依存なし、プライバシー保護

## 実装計画

### ステップ1: 依存関係の追加

[`pyproject.toml`](backend/pyproject.toml) に以下を追加:

```toml
"langchain-huggingface>=0.0.1",
"torch>=2.0.0",
"transformers>=4.35.0",
```

### ステップ2: LLMサービスへの埋め込み機能統合

[`llm.py`](backend/app/core/llm.py) の `embed_texts()` メソッドを本実装に置き換え:

```python
from langchain_huggingface import HuggingFaceEmbeddings

class EmbeddingModel:
    """埋め込みモデル"""
    def __init__(self):
        self.model_name = "stabilityai/japanese-stable-embed-multilingual-v3"
        # または "lmstuz/japanese-sentence-embedding-training-luke"
        self.embeddings = HuggingFaceEmbeddings(model_name=self.model_name)
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """テキストの埋め込み生成"""
        return self.embeddings.embed_documents(texts)
    
    def embed_query(self, query: str) -> list[float]:
        """クエリの埋め込み生成"""
        return self.embeddings.embed_query(query)

embedding_model = EmbeddingModel()
```

### ステップ3: RAGサービスの修正

[`rag.py`](backend/app/core/rag.py) のダミー埋め込みを削除:

- `store_document()`: `llm_service.embed_texts()` を使用
- `search()`: `llm_service.embed_query()` を使用

### ステップ4: Dockerfile の修正

[`backend/Dockerfile`](backend/Dockerfile) にPyTorchおよびモデルダウンロード用の依存を追加

### ステップ5: 初期化スクリットの追加

アプリケーション起動時に埋め込みモデルをキャッシュする初期化処理を追加

## 推奨埋め込みモデル

| モデル名 | 次元 | 特徴 |
|----------|------|------|
| `stabilityai/japanese-stable-embed-multilingual-v3` | 1024 | 日本語・多言語対応 |
| `lmstuz/japanese-sentence-embedding-training-luke` | 1024 | LUKEベース、日本語特化 |
| `tom-aaron/stable-embed-multilingual-v3-japan-extra` | 1024 | 多言語 + 日本特化 |

## 法令データ拡充計画

### 追加すべき法令ドキュメント

1. **借地借家法**
   - 借地権の期間・更新・更新料
   - 借家権の保護・契約更新

2. **民法**
   - 契約関連条文（債権・物権）
   - 敷金・礼金に関する規定

3. **宅地建物取引業法**
   - 重要事項説明書
   - 手付金保護

4. **不動産登記法**
   - 登記手続き
   - 権利関係

### ドキュメント形式

- Markdown形式で `documents/reference/` に配置
- PDFは `PyPDFLoader` で読み込み可能

## Qdrantコレクション確認

現在の [`_init_collection()`](backend/app/core/rag.py:28-39) は既に実装済み:
- コレクション存在チェック
- 存在しない場合は自動作成（次元数768、距離COSINE）

**修正が必要:** 埋め込みモデルの次元数に合わせて調整（例: 1024次元）

## スケジュール

1. 依存関係追加（`pyproject.toml`）
2. 埋め込みモデル統合（`llm.py`）
3. RAGサービス修正（`rag.py`）
4. Dockerfile修正
5. テストドキュメント追加
6. 接続確認テスト

## 注意事項

- 埋め込みモデルの初期読み込みに数分かかる可能性あり
- Dockerコンテナ内のメモリ確保（最低4GB推奨）
- モデルサイズによりディスク容量が必要（約2GB）
