"""システムAPI - 接続確認及初期化"""

import os
import glob
from typing import Annotated

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import get_current_user, UserResponse
from app.core.importer import import_documents
from app.core.llm import llm_service
from app.core.rag import rag_service

router = APIRouter()


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str
    environment: str
    service: str


class LLMStatusResponse(BaseModel):
    """LLM接続状態レスポンス"""
    connected: bool
    model: str
    error: str | None = None


class ImportResponse(BaseModel):
    """ドキュメントインポートレスポンス"""
    imported: int
    failed: int
    files: list[dict]


class ImportStatusResponse(BaseModel):
    """インポート状態レスポンス"""
    has_documents: bool
    document_count: int
    collections: list[str]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """システムヘルスチェック"""
    return {
        "status": "healthy",
        "environment": "development",
        "service": "real-estate-ai",
    }


@router.get("/llm/status", response_model=LLMStatusResponse)
async def check_llm_status():
    """LLM接続状態確認"""
    try:
        # LLMに簡易リクエストを送信
        response = await llm_service.generate("接続確認のため、このメッセージに対して『接続成功』と返信してください。", temperature=0.1)
        return LLMStatusResponse(
            connected=True,
            model=llm_service.model,
        )
    except Exception as e:
        return LLMStatusResponse(
            connected=False,
            model=llm_service.model,
            error=str(e),
        )


@router.post("/documents/import", response_model=ImportResponse)
async def import_reference_documents(
):
    """参照ドキュメントの一括インポート"""
    try:
        results = await import_documents(
            directory="documents/reference",
            category="real_estate_law",
        )
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ドキュメントインポート中にエラーが発生しました: {str(e)}",
        )


@router.get("/documents/status", response_model=ImportStatusResponse)
async def get_document_status(
):
    """ドキュメントインポート状態確認"""
    try:
        # documents/reference ディレクトリ内のファイル数をカウント
        patterns = [
            "documents/reference/**/*.md",
            "documents/reference/**/*.txt",
            "documents/reference/**/*.pdf",
        ]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))
        
        return ImportStatusResponse(
            has_documents=len(files) > 0,
            document_count=len(files),
            collections=[rag_service.collection_name],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ドキュメント状態確認中にエラーが発生しました: {str(e)}",
        )
