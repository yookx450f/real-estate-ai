"""不動産法律AIシステム - メインアプリケーション"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, documents, legal_data, system
from app.config import settings

app = FastAPI(
    title="不動産法律AIシステム",
    description="宅地建物取引士試験対応の法律AIチャットシステム",
    version="0.1.0",
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切なオリジンに制限してください
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーティング
app.include_router(auth.router, prefix="/api/auth", tags=["認証"])
app.include_router(chat.router, prefix="/api/chat", tags=["チャット"])
app.include_router(documents.router, prefix="/api/documents", tags=["ドキュメント"])
app.include_router(legal_data.router, prefix="/api/system/legal-data", tags=["法令データ"])
app.include_router(system.router, prefix="/api/system", tags=["システム"])


@app.get("/api/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "service": "real-estate-ai",
    }
