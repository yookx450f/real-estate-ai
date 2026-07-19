"""ドキュメントAPI"""

from typing import Annotated, Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.api.auth import get_current_user, UserResponse

router = APIRouter()


class DocumentResponse(BaseModel):
    """ドキュメントレスポンス"""

    id: str
    filename: str
    uploaded_at: str
    status: str  # processing, completed, error
    chunk_count: int = 0


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
