"""法令データインポーター - e-Gov APIおよびファイルからの法令データ取得"""

import os
import glob
import json
import xml.etree.ElementTree as ET
from typing import Optional
from datetime import datetime

import httpx

from app.config import settings
from app.core.rag import rag_service


class LegalDataImporter:
    """法令データインポーター
    
    方案A: e-Gov APIから自動取得（API接続可能な場合）
    方案B: ファイルからのインポート（常に利用可能）
    """

    def __init__(self):
        self.api_base_url = settings.legal_data_api_url
        self.file_directory = settings.legal_data_file_directory
        self.rag_service = rag_service
        self._laws_cache: list[dict] = []
        self._api_available: Optional[bool] = None

    def _get_laws_list(self) -> list[dict]:
        """法令リストを取得"""
        laws_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "legal_laws.json"
        )
        if os.path.exists(laws_file):
            with open(laws_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    async def _check_api_connectivity(self) -> bool:
        """API接続可能性を確認"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.api_base_url,
                    params={"law_num": "57AC10000162", "bunrui": "1", "body": "1"},
                )
                return response.status_code == 200
        except Exception:
            return False

    @property
    def api_available(self) -> bool:
        """APIが利用可能か"""
        if self._api_available is None:
            self._api_available = False  # デフォルトは不可（安全側）
            # 環境により接続テストを実行
            # self._api_available = asyncio.run(self._check_api_connectivity())
        return self._api_available

    async def fetch_law(self, law_code: str) -> str:
        """e-Gov APIから法令データを取得
        
        Args:
            law_code: 法令コード（例: 57AC10000162）
            
        Returns:
            法令本文のテキスト
            
        Raises:
            Exception: API接続失敗時
        """
        if not self.api_available:
            raise Exception(
                "法令データAPIに接続できません。"
                "documents/reference/ディレクトリにファイルを配置してインポートしてください。"
            )

        params = {
            "law_num": law_code,
            "bunrui": 1,    # 法令種別
            "body": 1,     # 条文本文
            "al": 1,       # 目次
            "rov": 1,      # 改正履歴
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.api_base_url, params=params)
            response.raise_for_status()
            return response.text

    async def parse_xml(self, xml_content: str) -> dict:
        """XMLデータをパースして構造化データに変換
        
        Args:
            xml_content: XML文字列
            
        Returns:
            構造化データ（法令名、条文リストなど）
        """
        root = ET.fromstring(xml_content)
        
        law_info = {
            "code": "",
            "name": "",
            "enacted_date": "",
            "amendments": [],
            "articles": [],
        }

        # 法令コード
        law_num_elem = root.find("law_num")
        if law_num_elem is not None and law_num_elem.text:
            law_info["code"] = law_num_elem.text

        # 法令名
        title_elem = root.find("title")
        if title_elem is not None and title_elem.text:
            law_info["name"] = title_elem.text

        # 条文を抽出
        body_elem = root.find("body")
        if body_elem is not None:
            for article in body_elem.iter("article"):
                article_num = article.findtext("article_num", "")
                text = article.findtext("text", "")
                if article_num or text:
                    law_info["articles"].append({
                        "number": article_num,
                        "text": text,
                    })

        return law_info

    def _format_text(self, law_info: dict) -> str:
        """構造化データをテキスト形式に変換
        
        Args:
            law_info: 法令情報
            
        Returns:
            整形されたテキスト文字列
        """
        lines = []
        lines.append(f"【{law_info['name']}】（法令コード: {law_info['code']}）")
        lines.append("=" * 60)
        lines.append("")

        for article in law_info["articles"]:
            if article["number"]:
                lines.append(f"【{article['number']}】")
            if article["text"]:
                lines.append(article["text"])
            lines.append("")

        return "\n".join(lines)

    async def store_law(
        self,
        law_code: str,
        law_name: str,
        text: str,
        category: str = "real_estate_law",
    ) -> dict:
        """法令データをRAGに保存
        
        Args:
            law_code: 法令コード
            law_name: 法令名
            text: 法令テキスト
            category: カテゴリ
            
        Returns:
            保存結果
        """
        source_url = f"https://elaws.e-gov.go.jp/law/?law_num={law_code}"
        
        result = await self.rag_service.store_document(
            filename=f"{law_code}_{law_name}.txt",
            text=text,
            category=category,
            source_url=source_url,
        )

        return {
            "law_code": law_code,
            "law_name": law_name,
            "chunk_count": result["chunk_count"],
            "status": "completed",
            "source_url": source_url,
        }

    async def fetch_and_store(
        self,
        law_code: str,
        category: str = "real_estate_law",
    ) -> dict:
        """APIから取得してRAGに保存（方案A）
        
        Args:
            law_code: 法令コード
            category: カテゴリ
            
        Returns:
            保存結果
        """
        # 1. APIからデータ取得
        xml_content = await self.fetch_law(law_code)
        
        # 2. XMLパース
        law_info = await self.parse_xml(xml_content)
        
        # 3. テキスト形式に変換
        text = self._format_text(law_info)
        
        # 4. RAGに保存
        return await self.store_law(
            law_code=law_info["code"] or law_code,
            law_name=law_info["name"] or law_code,
            text=text,
            category=category,
        )

    async def import_from_files(
        self,
        directory: str = "documents/reference",
        category: str = "real_estate_law",
    ) -> dict:
        """ファイルからのインポート（方案B - 常に利用可能）
        
        Args:
            directory: ファイルディレクトリ
            category: カテゴリ
            
        Returns:
            インポート結果
        """
        results = {
            "method": "file",
            "imported": 0,
            "failed": 0,
            "files": [],
        }

        patterns = [
            os.path.join(directory, "**", "*.md"),
            os.path.join(directory, "**", "*.txt"),
            os.path.join(directory, "**", "*.pdf"),
        ]

        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))

        for filepath in files:
            try:
                filename = os.path.basename(filepath)

                # ファイルタイプに応じて読み込み
                text = ""
                if filepath.endswith(".pdf"):
                    from langchain_community.document_loaders import PyPDFLoader
                    loader = PyPDFLoader(filepath)
                    pages = loader.load()
                    text = "\n".join([page.page_content for page in pages])
                else:
                    with open(filepath, "r", encoding="utf-8") as f:
                        text = f.read()

                if text:
                    # ファイルパスから法令コードを推定
                    law_code = os.path.splitext(filename)[0]
                    
                    result = await self.rag_service.store_document(
                        filename=f"{law_code}_{filename}",
                        text=text,
                        category=category,
                        source_url=f"file://{filepath}",
                    )
                    results["imported"] += 1
                    results["files"].append({
                        "law_code": law_code,
                        "filename": filename,
                        "chunks": result["chunk_count"],
                        "status": "success",
                    })
                else:
                    results["failed"] += 1
                    results["files"].append({
                        "filename": filename,
                        "status": "error",
                        "reason": "ファイルが空または読み込めませんでした",
                    })
            except Exception as e:
                results["failed"] += 1
                results["files"].append({
                    "filename": os.path.basename(filepath),
                    "status": "error",
                    "reason": str(e),
                })

        return results

    async def get_environment_status(self) -> dict:
        """環境情報を取得
        
        Returns:
            環境情報（API利用可否、ファイル数など）
        """
        # ファイル数をカウント
        patterns = [
            os.path.join(self.file_directory, "**", "*.md"),
            os.path.join(self.file_directory, "**", "*.txt"),
            os.path.join(self.file_directory, "**", "*.pdf"),
        ]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))

        return {
            "api_available": self.api_available,
            "api_url": self.api_base_url,
            "file_directory": self.file_directory,
            "file_count": len(files),
            "message": (
                "API接続可能。法令データを自動取得できます。"
                if self.api_available
                else "API接続不可。documents/reference/ディレクトリにファイルを配置してインポートしてください。"
            ),
        }

    async def get_available_laws(self) -> list[dict]:
        """登録可能な法令リストを取得
        
        Returns:
            法令リスト
        """
        laws = self._get_laws_list()
        return [
            {
                "code": law["code"],
                "name": law["name"],
                "short_name": law.get("short_name", law["name"]),
                "category": law.get("category", "real_estate_law"),
                "enabled": law.get("enabled", True),
            }
            for law in laws
            if law.get("enabled", True)
        ]


# モジュールインスタンス
legal_data_importer = LegalDataImporter()
