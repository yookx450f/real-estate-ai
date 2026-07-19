"""ドキュメントAPI"""

import os
from typing import Annotated, Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.api.auth import get_current_user, UserResponse
from app.core.rag import rag_service
from app.core.importer import import_documents

router = APIRouter()


class DocumentResponse(BaseModel):
    """ドキュメントレスポンス"""

    id: str
    filename: str
    uploaded_at: str
    status: str  # processing, completed, error
    chunk_count: int = 0


class RAGStatusResponse(BaseModel):
    """RAG状態レスポンス"""

    collection_name: str
    total_points: int
    documents: list[dict]


class ImportResultResponse(BaseModel):
    """インポート結果レスポンス"""

    imported: int
    failed: int
    files: list[dict]


@router.get("/")
async def list_documents(
    user: Annotated[UserResponse, Depends(get_current_user)],
    category: Optional[str] = None,
) -> list[DocumentResponse]:
    """ドキュメント一覧"""
    # 本番環境ではPostgreSQLから取得
    return []


@router.post("/upload")
async def upload_document(
    user: Annotated[UserResponse, Depends(get_current_user)],
    file: UploadFile = File(...),
    category: str = "taikoken",
) -> DocumentResponse:
    """ドキュメントアップロード"""
    # ファイル保存処理
    # チャンキング処理
    # ベクトル埋め込み生成
    # Qdrantへの登録
    return DocumentResponse(
        id="dummy-id",
        filename=file.filename,
        uploaded_at="",
        status="processing",
        chunk_count=0,
    )


@router.delete("/{document_id}")
async def delete_document(
    user: Annotated[UserResponse, Depends(get_current_user)],
    document_id: str,
):
    """ドキュメント削除"""
    # 本番環境ではPostgreSQLとQdrantから削除
    return {"message": "削除されました"}


@router.get("/search")
async def search_documents(
    user: Annotated[UserResponse, Depends(get_current_user)],
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """ベクトル検索"""
    # 本番環境ではQdrantから検索
    return []


@router.get("/rag-status", response_model=RAGStatusResponse)
async def get_rag_status(
    user: Annotated[UserResponse, Depends(get_current_user)],
) -> RAGStatusResponse:
    """RAGの現在の状態を確認（チャンク数含む）"""
    try:
        client = rag_service.qdrant_client
        collection_name = rag_service.collection_name
        
        # コレクションの情報取得
        collection_info = client.get_collection(collection_name)
        total_points = collection_info.points_count
        
        # 登録されているドキュメントのメタデータ取得
        # 登録されているすべてのポイントを取得して、ファイル別にグループ化
        documents = {}
        offset = 0
        batch_size = 100
        
        while True:
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points = scroll_result[0]
            if not points:
                break
            
            for point in points:
                payload = payload = point.payload
                filename = payload.get("filename", "unknown")
                if filename not in documents:
                    documents[filename] = {
                        "filename": filename,
                        "category": payload.get("category", ""),
                        "chunk_count": 0,
                        "source_url": payload.get("source_url", ""),
                    }
                documents[filename]["chunk_count"] += 1
            
            if len(points) < batch_size:
                break
            offset += batch_size
        
        return RAGStatusResponse(
            collection_name=collection_name,
            total_points=total_points,
            documents=list(documents.values()),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG状態の取得中にエラーが発生しました: {str(e)}",
        )


@router.post("/import-documents", response_model=ImportResultResponse)
async def import_all_documents(
    user: Annotated[UserResponse, Depends(get_current_user)],
    directory: str = "documents/reference",
    category: str = "taikoken",
) -> ImportResultResponse:
    """ディレクトリ内の全ドキュメントをRAGに登録"""
    try:
        result = await import_documents(directory=directory, category=category)
        return ImportResultResponse(
            imported=result["imported"],
            failed=result["failed"],
            files=result["files"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ドキュメントインポート中にエラーが発生しました: {str(e)}",
        )
