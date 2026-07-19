"""LLMサービス - ローカルLLMとの連携"""

from openai import AsyncOpenAI

from app.config import settings


class LLMService:
    """ローカルLLMとの連携サービス"""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key="ollama",  # OllamaのOpenAI互換API用
        )
        self.model = settings.llm_model
        self.embedding_model_name = settings.embedding_model_name
        
        # 埋め込みモデルの初期化を試みる（失敗してもフォールバックあり）
        self.embedding_model = EmbeddingModel()
        self._embedding_fallback = self.embedding_model._init_error is not None

    async def generate(self, prompt: str, temperature: float = 0.1) -> str:
        """テキスト生成"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=4096,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise Exception(f"LLM生成エラー: {str(e)}")

    async def stream_generate(self, prompt: str) -> str:
        """ストリーミングテキスト生成（プレースホルダー）"""
        # 本実装では非ストリーミングと同じ処理を行う
        return await self.generate(prompt)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """テキストの埋め込み生成 - HuggingFaceまたはOpenAI互換APIを使用"""
        if not self._embedding_fallback:
            try:
                return self.embedding_model.embed_texts(texts)
            except (ImportError, Exception):
                self._embedding_fallback = True  # フールバックに切り替え
        
        # OpenAI互換APIを使用した埋め込み生成（フォールバック）
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model_name,
                input=texts,
            )
            return [d.embedding for d in response.data]
        except Exception as e:
            raise Exception(f"埋め込み生成エラー（フォールバック失敗）: {str(e)}")

    async def embed_query(self, query: str) -> list[float]:
        """クエリの埋め込み生成 - HuggingFaceまたはOpenAI互換APIを使用"""
        if not self._embedding_fallback:
            try:
                return self.embedding_model.embed_query(query)
            except (ImportError, Exception):
                self._embedding_fallback = True  # フールバックに切り替え
        
        # OpenAI互換APIを使用した埋め込み生成（フォールバック）
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model_name,
                input=[query],
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"クエリ埋め込み生成エラー（フォールバック失敗）: {str(e)}")

    @property
    def embedding_dimension(self) -> int:
        """埋め込みベクトルの次元数"""
        return self.embedding_model.dimension


# 埋め込みモデルクラス
class EmbeddingModel:
    """埋め込みモデル（HuggingFaceフォールバック用）"""

    def __init__(self):
        self._hf_embeddings = None
        self._initialized = False
        self._init_error = None
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            self._hf_embeddings = HuggingFaceEmbeddings(model_name=settings.llm_model)
            self._initialized = True
        except ImportError as e:
            self._init_error = f"langchain-huggingface がインストールされていません: {str(e)}"
        except Exception as e:
            self._init_error = f"埋め込みモデルの初期化に失敗しました: {str(e)}"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """テキストの埋め込み生成"""
        if not self._initialized or self._hf_embeddings is None:
            raise ImportError(self._init_error or "langchain-huggingface がインストールされていません。")
        return self._hf_embeddings.embed_documents(texts)

    def embed_query(self, query: str) -> list[float]:
        """クエリの埋め込み生成"""
        if not self._initialized or self._hf_embeddings is None:
            raise ImportError(self._init_error or "langchain-huggingface がインストールされていません。")
        return self._hf_embeddings.embed_query(query)

    @property
    def dimension(self) -> int:
        """埋め込みベクトルの次元数"""
        return 768  # デフォルト値


llm_service = LLMService()
