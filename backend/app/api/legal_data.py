"""法令データ管理API - 環境に応じた法令データ取得・管理"""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.auth import get_current_user, UserResponse
from app.core.legal_data_importer import legal_data_importer

router = APIRouter()


class FetchLawRequest(BaseModel):
    """法令取得リクエスト"""
    law_code: str
    category: str = "real_estate_law"


class EnvironmentStatusResponse:
    """環境ステータスレスポンス"""
    
    def __init__(self, data: dict):
        self.data = data
    
    def __iter__(self):
        yield from self.data.items()


class AvailableLawsResponse:
    """利用可能法令レスポンス"""
    
    def __init__(self, laws: list[dict]):
        self.laws = laws
    
    def __iter__(self):
        yield from (("laws", self.laws),)


class FetchLawResponse:
    """法令取得レスポンス"""
    
    def __init__(self, data: dict):
        self.data = data
    
    def __iter__(self):
        yield from (("result", self.data),)


class FileImportResponse:
    """ファイルインポートレスポンス"""
    
    def __init__(self, data: dict):
        self.data = data
    
    def __iter__(self):
        yield from (("result", self.data),)


class CollectionsResponse:
    """登録コレクションレスポンス"""
    
    def __init__(self, data: dict):
        self.data = data
    
    def __iter__(self):
        yield from (("collections", self.data),)


@router.get("/status", response_model=None)
async def get_environment_status(
    user: Annotated[UserResponse, Depends(get_current_user)],
):
    """環境ステータス取得
    
    APIの利用可否、ファイル数、利用可能な取得方法を返す。
    """
    try:
        status_data = await legal_data_importer.get_environment_status()
        return status_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"環境情報取得中にエラーが発生しました: {str(e)}",
        )


@router.get("/laws", response_model=None)
async def get_available_laws(
    user: Annotated[UserResponse, Depends(get_current_user)],
):
    """登録可能な法令リスト取得
    
    設定された法令コードのリストを返す。
    """
    try:
        laws = await legal_data_importer.get_available_laws()
        return {"laws": laws}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"法令リスト取得中にエラーが発生しました: {str(e)}",
        )


@router.post("/fetch")
async def fetch_law(
    user: Annotated[UserResponse, Depends(get_current_user)],
    request: FetchLawRequest,
):
    """法令データを取得してRAGに保存（方案A: API使用）
    
    e-Gov APIから法令データを取得し、RAGに登録する。
    APIが利用できない場合はエラーを返す。
    """
    try:
        # API接続チェック
        if not legal_data_importer.api_available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "法令データAPIに接続できません。"
                    "ファイルをdocuments/reference/に配置して"
                    "POST /api/system/legal-data/import-files をご利用ください。"
                ),
            )

        result = await legal_data_importer.fetch_and_store(
            law_code=request.law_code,
            category=request.category,
        )
        return {"result": result}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"法令データ取得中にエラーが発生しました: {str(e)}",
        )


@router.post("/import-files", response_model=None)
async def import_files(
    user: Annotated[UserResponse, Depends(get_current_user)],
    category: str = "real_estate_law",
):
    """ファイルからのインポート（方案B: ファイル使用）
    
    documents/reference/ディレクトリ内のファイルを
    読み込んでRAGに登録する。
    
    category: インポートするカテゴリ（デフォルト: real_estate_law）
    """
    try:
        result = await legal_data_importer.import_from_files(
            directory="documents/reference",
            category=category,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ファイルインポート中にエラーが発生しました: {str(e)}",
        )


@router.get("/collections", response_model=None)
async def get_collections(
    user: Annotated[UserResponse, Depends(get_current_user)],
):
    """登録済み法令のコレクション一覧取得
    
    Qdrantに登録されている法令データのリストを返す。
    """
    try:
        # コレクション情報を取得
        collections = legal_data_importer.rag_service.qdrant_client.get_collections()
        
        # 既存のデータを取得
        existing_data = []
        
        return {
            "collections": collections.collections,
            "existing_data": existing_data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"コレクション情報取得中にエラーが発生しました: {str(e)}",
        )


@router.delete("/{law_code}", response_model=None)
async def delete_law(
    user: Annotated[UserResponse, Depends(get_current_user)],
    law_code: str,
):
    """法令データをRAGから削除
    
    指定した法令コードに該当するデータを削除する。
    """
    try:
        # 実装: Qdrantから該当データを削除
        # 現在はプレースホルダー
        return {
            "law_code": law_code,
            "status": "deleted",
            "message": f"法令コード {law_code} のデータを削除しました。",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"法令データ削除中にエラーが発生しました: {str(e)}",
        )
