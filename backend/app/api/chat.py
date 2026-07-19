"""チャットAPI"""

import json
import os
from datetime import datetime
from typing import Annotated, AsyncGenerator

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import get_current_user, UserResponse
from app.core.rag import rag_service

router = APIRouter()

# 会話データを保存するディレクトリ
CONVERSATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "conversations")


class ChatRequest(BaseModel):
    """チャットリクエスト"""

    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    """チャットレスポンス"""

    answer: str
    sources: list[dict] = []
    conversation_id: str


class ConversationResponse(BaseModel):
    """会話レスポンス"""

    id: str
    title: str
    messages: list[dict]
    created_at: str
    updated_at: str


class CreateConversationRequest(BaseModel):
    """会話作成リクエスト"""

    title: str = "新しいチャット"


class CreateConversationResponse(BaseModel):
    """会話作成レスポンス"""

    id: str
    title: str
    created_at: str


class DeleteConversationResponse(BaseModel):
    """会話削除レスポンス"""

    success: bool
    message: str


def _get_user_conversations_dir(email: str) -> str:
    """ユーザー別の会話ディレクトリを取得"""
    user_dir = os.path.join(CONVERSATIONS_DIR, email.replace("@", "_"))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def _get_conversation_file(conversation_id: str, email: str) -> str:
    """会話ファイルのパスを取得"""
    user_dir = _get_user_conversations_dir(email)
    return os.path.join(user_dir, f"{conversation_id}.json")


def _create_new_conversation_id() -> str:
    """新しい会話IDを作成"""
    return datetime.utcnow().strftime("conv_%Y%m%d%H%M%S%f")


def _save_conversation(conversation_id: str, title: str, messages: list[dict], email: str) -> None:
    """会話をファイルに保存"""
    file_path = _get_conversation_file(conversation_id, email)
    data = {
        "id": conversation_id,
        "title": title,
        "messages": messages,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_conversation(conversation_id: str, email: str) -> dict | None:
    """会話ファイルをロード"""
    file_path = _get_conversation_file(conversation_id, email)
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _list_conversations(email: str) -> list[dict]:
    """ユーザーの会話一覧を取得"""
    user_dir = _get_user_conversations_dir(email)
    conversations = []
    if os.path.exists(user_dir):
        for filename in os.listdir(user_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(user_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        conversations.append({
                            "id": data["id"],
                            "title": data["title"],
                            "messages": data.get("messages", []),
                            "created_at": data["created_at"],
                            "updated_at": data["updated_at"],
                        })
                except Exception:
                    continue
    # 更新日でソート（新しい順）
    conversations.sort(key=lambda x: x["updated_at"], reverse=True)
    return conversations


@router.post("/", response_model=ChatResponse)
async def chat(
    user: Annotated[UserResponse, Depends(get_current_user)],
    request: ChatRequest,
):
    """AIへの質問"""
    try:
        result = await rag_service.search_and_generate(request.message)
        
        # 会話IDの処理
        conversation_id = request.conversation_id
        if not conversation_id or conversation_id == "new":
            conversation_id = _create_new_conversation_id()
        
        # 既存の会話をロード
        existing_data = None
        if request.conversation_id and request.conversation_id != "new":
            existing_data = _load_conversation(request.conversation_id, user.email)

        # メッセージの追加
        messages = []
        if existing_data:
            messages = existing_data.get("messages", [])
            title = existing_data.get("title", "新しいチャット")
        else:
            # 最初のメッセージからタイトルを生成（最初の50文字）
            title = request.message[:50]
            if len(request.message) > 50:
                title += "..."

        # ユーザーメッセージとAI応答を追加
        messages.append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.utcnow().isoformat(),
        })
        messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("sources", []),
            "timestamp": datetime.utcnow().isoformat(),
        })

        # 会話を保存
        _save_conversation(
            conversation_id=conversation_id,
            title=title,
            messages=messages,
            email=user.email,
        )

        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            conversation_id=conversation_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"チャット処理中にエラーが発生しました: {str(e)}",
        )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """ストリーミングチャット"""

    async def generate_response():
        async for chunk in rag_service.stream_generate(request.message):
            yield chunk

    return generate_response()


@router.get("/conversations", response_model=list[ConversationResponse])
async def get_conversations(
    user: Annotated[UserResponse, Depends(get_current_user)],
):
    """会話履歴一覧"""
    try:
        conversations = _list_conversations(user.email)
        return conversations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"会話履歴の取得中にエラーが発生しました: {str(e)}",
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    user: Annotated[UserResponse, Depends(get_current_user)],
    conversation_id: str,
):
    """会話詳細"""
    try:
        data = _load_conversation(conversation_id, user.email)
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会話が見つかりません",
            )
        return ConversationResponse(
            id=data["id"],
            title=data["title"],
            messages=data["messages"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"会話の詳細取得中にエラーが発生しました: {str(e)}",
        )


@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    user: Annotated[UserResponse, Depends(get_current_user)],
    request: CreateConversationRequest,
):
    """新しい会話を作成"""
    try:
        conversation_id = _create_new_conversation_id()
        _save_conversation(
            conversation_id=conversation_id,
            title=request.title,
            messages=[],
            email=user.email,
        )
        return CreateConversationResponse(
            id=conversation_id,
            title=request.title,
            created_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"会話の作成中にエラーが発生しました: {str(e)}",
        )


@router.delete("/conversations/{conversation_id}", response_model=DeleteConversationResponse)
async def delete_conversation(
    user: Annotated[UserResponse, Depends(get_current_user)],
    conversation_id: str,
):
    """会話を削除"""
    try:
        file_path = _get_conversation_file(conversation_id, user.email)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会話が見つかりません",
            )
        os.remove(file_path)
        return DeleteConversationResponse(
            success=True,
            message="会話を削除しました",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"会話の削除中にエラーが発生しました: {str(e)}",
        )


@router.get("/conversations/{conversation_id}/messages", response_model=list[dict])
async def get_conversation_messages(
    user: Annotated[UserResponse, Depends(get_current_user)],
    conversation_id: str,
):
    """会話のメッセージ一覧を取得"""
    try:
        data = _load_conversation(conversation_id, user.email)
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会話が見つかりません",
            )
        return data.get("messages", [])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"メッセージの取得中にエラーが発生しました: {str(e)}",
        )
