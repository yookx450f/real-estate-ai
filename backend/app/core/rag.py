"""RAGサービス - Retrieval Augmented Generation"""

import json
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_qdrant import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.config import settings
from app.core.llm import llm_service


class RAGService:
    """RAGサービス"""

    def __init__(self):
        self.qdrant_client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.qdrant_collection_name
        self.embedding_dimension = llm_service.embedding_dimension
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", "、", " "],
        )

    def _init_collection(self):
        """Qdrantのコレクション初期化"""
        try:
            # コレクションが存在しない場合は作成
            # 埋め込み次元数はモデルによって調整（japanese-stable-embed-multilingual-v3: 1024）
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.embedding_dimension, distance=Distance.COSINE),
            )
        except Exception as e:
            # 既に存在する場合は無視
            print(f"コレクション初期化エラー（無視）: {e}")

    def _chunk_text(self, text: str, metadata: dict | None = None) -> list[dict]:
        """テキストをチャンクに分割"""
        # テキストをチャンクに分割
        chunks = self.text_splitter.split_text(text)

        # メタデータを付けて返却
        result = []
        for i, chunk in enumerate(chunks):
            chunk_meta = metadata.copy() if metadata else {}
            chunk_meta["chunk_index"] = i
            chunk_meta["chunk_count"] = len(chunks)
            result.append({
                "text": chunk,
                "metadata": chunk_meta,
            })
        return result

    async def store_document(
        self,
        filename: str,
        text: str,
        category: str = "taikoken",
        source_url: str | None = None,
    ) -> dict:
        """ドキュメントを保存（チャンキング + ベクトル埋め込み）"""
        self._init_collection()

        # テキストをチャンクに分割
        chunks = self._chunk_text(
            text,
            {
                "filename": filename,
                "category": category,
                "source_url": source_url,
            },
        )

        print(f"[store_document] {filename}: {len(chunks)}チャンクに分割")

        # 各チャンクをベクトル埋め込みしてQdrantに保存
        embedded_points = []
        
        # バッチで埋め込みを生成（効率化）
        chunk_texts = [chunk["text"] for chunk in chunks]
        try:
            print(f"[store_document] 埋め込み生成開始...")
            embeddings = await llm_service.embed_texts(chunk_texts)
            print(f"[store_document] 埋め込み生成完了: {len(embeddings)}件, 次元数: {len(embeddings[0]) if embeddings else 'N/A'}")
        except Exception as e:
            print(f"[store_document] 埋め込み生成エラー: {str(e)}")
            raise Exception(f"埋め込み生成エラー: {str(e)}")

        # ポイントIDをユニークにする（filename + chunk_indexの組み合わせ）
        import uuid
        for i, chunk in enumerate(chunks):
            # ユニークIDを生成（ファイル名とチャンクインデックスを使用）
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{filename}_{i}"))
            point = PointStruct(
                id=point_id,
                vector=embeddings[i],
                payload={
                    "text": chunk["text"],
                    "filename": filename,
                    "category": category,
                    "source_url": source_url,
                    "chunk_index": i,
                },
            )
            embedded_points.append(point)

        # Qdrantにアップロード
        if embedded_points:
            print(f"[store_document] Qdrantにアップロード開始: {len(embedded_points)}ポイント")
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=embedded_points,
            )
            print(f"[store_document] Qdrantにアップロード完了")

        return {
            "filename": filename,
            "chunk_count": len(chunks),
            "status": "completed",
        }

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """類似ドキュメントを検索"""
        self._init_collection()

        # クエリの埋め込みを生成
        try:
            query_embedding = await llm_service.embed_query(query)
        except Exception as e:
            raise Exception(f"クエリ埋め込み生成エラー: {str(e)}")

        # 類似ドキュメントを検索
        search_results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
        )

        # 結果を形式に変換
        sources = []
        for hit in search_results.points:
            sources.append({
                "filename": hit.payload.get("filename", ""),
                "text": hit.payload.get("text", ""),
                "category": hit.payload.get("category", ""),
                "source_url": hit.payload.get("source_url", ""),
                "score": hit.score,
            })

        return sources

    async def search_and_generate(self, query: str, top_k: int = 5) -> dict:
        """検索 + 生成（RAG）"""
        # 1. 類似ドキュメントを検索
        sources = await self.search(query, top_k)

        # 2. コンテキストを構築
        context_parts = []
        for i, source in enumerate(sources):
            context_parts.append(f"[参照{i + 1}] {source['text']}")

        context = "\n\n".join(context_parts)

        # 3. プロンプトを構築
        system_prompt = """あなたは不動産法律に詳しいAIアシスタントです。
以下の参照情報に基づいて、正確な回答を行ってください。
回答後には、使用した参照元のドキュメント名を明記してください。

回答のルール:
1. 専門用語は適切に説明する
2. 根拠となる法令条を明記する
3. 不明な点は明確に「不明」とする
4. 推測で回答しない"""

        user_prompt = """以下の質問に回答してください。

参照情報:
{context}

質問: {query}"""

        # 4. LLMに生成を依頼
        answer = await llm_service.generate(
            f"{system_prompt}\n\n{user_prompt.format(context=context, query=query)}"
        )

        return {
            "answer": answer,
            "sources": sources,
        }

    async def stream_generate(self, query: str, top_k: int = 5):
        """ストリーミング生成（プレースホルダー）"""
        result = await self.search_and_generate(query, top_k)
        # 実際にはストリーミングでチャンクを返す
        yield json.dumps({
            "answer": result["answer"],
            "sources": result["sources"],
        })


rag_service = RAGService()
