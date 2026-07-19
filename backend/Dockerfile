FROM python:3.12-slim

WORKDIR /app

# システム依存関係のインストール（PyTorch用）
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 依存関係のインストール
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# アプリケーションコピー
COPY . .

# 埋め込みモデルの事前ダウンロード（初回起動時間短縮）
RUN python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='stabilityai/japanese-stable-embed-multilingual-v3')"

# 起動コマンド
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
