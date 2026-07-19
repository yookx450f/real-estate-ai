"""アプリケーション設定"""

import json
from typing import Any

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    model_config = {"extra": "ignore", "env_file": ".env", "case_sensitive": False}

    # LLM設定
    llm_base_url: str = "http://192.168.188.50:1234/v1"
    llm_model: str = "gemma4:e4b-mlx"
    # 埋め込みモデル名（Ollamaのモデル名を指定）
    embedding_model_name: str = "nomic-embed-text:latest"

    # Qdrant設定
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection_name: str = "real_estate_law"

    # PostgreSQL設定
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/real_estate_ai"

    # JWT設定
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24時間（デフォルト60分→1440分に延長）

    # 法令データ設定
    legal_data_api_url: str = "https://api.gov.go.jp/cgi-bin/search/single.cgi"
    legal_data_file_directory: str = "documents/reference"

    # 環境
    environment: str = "development"


settings = Settings()
