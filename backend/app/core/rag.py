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
        """Qdrantのコレクション初期化 - 次元数が一致しない場合は再作成"""
        try:
            # 既存コレクションの詳細を取得
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            existing_vectors = collection_info.config.params.vectors.size
            
            # 次元数が一致する場合は何もしない
            if existing_vectors == self.embedding_dimension:
                return
            
            # 次元数が一致しない場合は、コレクションを削除して再作成
            print(f"[RAG] 次元数不一致: 既存={existing_vectors}, 预期={self.embedding_dimension}。コレクションを再作成します。")
            self.qdrant_client.delete_collection(self.collection_name)
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.embedding_dimension, distance=Distance.COSINE),
            )
            print(f"[RAG] コレクションを再作成しました: {self.collection_name}")
            
        except Exception as e:
            # コレクションが存在しない場合は作成
            try:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.embedding_dimension, distance=Distance.COSINE),
                )
                print(f"[RAG] コレクションを作成しました: {self.collection_name}")
            except Exception as create_e:
                print(f"[RAG] コレクション初期化エラー: {create_e}")

    async def reset_collection(self):
        """コレクションを完全に削除（管理者用）"""
        try:
            self.qdrant_client.delete_collection(self.collection_name)
            print(f"[RAG] コレクションを削除しました: {self.collection_name}")
        except Exception as e:
            print(f"[RAG] コレクション削除エラー（無視）: {e}")
        finally:
            self._init_collection()

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
        evidence_info: dict | None = None,
    ) -> dict:
        """ドキュメントを保存（チャンキング + ベクトル埋め込み）"""
        self._init_collection()

        # エビデンス情報のデフォルト値
        if evidence_info is None:
            evidence_info = {}

        # テキストをチャンクに分割
        chunks = self._chunk_text(
            text,
            {
                "filename": filename,
                "category": category,
                "source_url": source_url,
                # エビデンス情報をメタデータに追加
                "law_name": evidence_info.get("law_name", ""),
                "article_number": evidence_info.get("article_number", ""),
                "section": evidence_info.get("section", ""),
                "document_title": evidence_info.get("document_title", filename),
                "evidence_text": evidence_info.get("evidence_text", ""),
            },
        )

        print(f"[store_document] {filename}: {len(chunks)}チャンクに分割")
        print(f"  エビデンス情報: 法令={evidence_info.get('law_name', 'N/A')}, 条文={evidence_info.get('article_number', 'N/A')}")

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
            
            # メタデータを取得
            chunk_meta = chunk.get("metadata", {})
            
            point = PointStruct(
                id=point_id,
                vector=embeddings[i],
                payload={
                    "text": chunk["text"],
                    "filename": filename,
                    "category": category,
                    "source_url": source_url,
                    "chunk_index": i,
                    # エビデンス情報（法令名、条文番号など）
                    "law_name": chunk_meta.get("law_name", ""),
                    "article_number": chunk_meta.get("article_number", ""),
                    "section": chunk_meta.get("section", ""),
                    "document_title": chunk_meta.get("document_title", filename),
                    "evidence_text": chunk_meta.get("evidence_text", ""),
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

        # 結果を形式に変換（エビデンス情報を強化）
        sources = []
        for hit in search_results.points:
            payload = hit.payload
            source_entry = {
                "filename": payload.get("filename", ""),
                "text": payload.get("text", ""),
                "category": payload.get("category", ""),
                "source_url": payload.get("source_url", ""),
                "score": hit.score,
                # エビデンス情報（完全な参照情報）
                "full_text": payload.get("text", ""),  # 参照した全文チャンク
                "law_name": payload.get("law_name", ""),  # 法令名
                "article_number": payload.get("article_number", ""),  # 条文番号
                "section": payload.get("section", ""),  # 項・号
                "document_title": payload.get("document_title", ""),  # ドキュメントタイトル
                "evidence_text": payload.get("evidence_text", ""),  # 根拠となる文章
            }
            sources.append(source_entry)

        return sources

    async def search_and_generate(self, query: str, top_k: int = 5) -> dict:
        """検索 + 生成（RAG）"""
        # 1. 類似ドキュメントを検索
        sources = await self.search(query, top_k)

        # 2. コンテキストを構築（エビデンス情報を強化）
        context_parts = []
        for i, source in enumerate(sources):
            # エビデンス情報が存在する場合は、法令名と条文番号を含める
            law_name = source.get("law_name", "")
            article_number = source.get("article_number", "")
            section = source.get("section", "")
            evidence_text = source.get("evidence_text", source.get("text", ""))
            
            # 参照形式の構築
            if law_name and article_number:
                section_info = f" 第{section}号" if section else ""
                reference_info = f"[参照{i + 1}] 法令: {law_name} 第{article_number}条{section_info}\n{evidence_text}"
            else:
                reference_info = f"[参照{i + 1}] {evidence_text}"
            
            context_parts.append(reference_info)

        context = "\n\n".join(context_parts)

        # 3. プロンプトを構築（強化版 - 法令名と条文を明記するよう指示）
        system_prompt = """あなたは不動産法律に詳しいAIアシスタントです。
以下の参照情報に基づいて、正確な回答を行ってください。

回答のルール:
1. 専門用語は適切に説明する
2. 必ず根拠となる「法令名」と「条文番号」を明記する（例：宅地建物取引業法第33条）
3. 不明な点は明確に「不明」とする
4. 推測で回答しない
5. 回答の最後に、使用した参照元のドキュメント名と、参照した文章の全文を明記する
6. 具体的な条文の文章を引用して、根拠を明確に示す"""

        user_prompt = """以下の質問に回答してください。

参照情報:
{context}

質問: {query}

回答形式:
1. 結論を先に伝える
2. 根拠となる法令名と条文番号を明記
3. 条文の内容を引用して説明
4. 参照したドキュメント名と、参照した文章の全文を明記"""

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
