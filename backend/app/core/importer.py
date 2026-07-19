"""ドキュメントインポーター - ファイルからのドキュメント登録"""

import os
import glob
from typing import Optional

from app.core.rag import rag_service


async def import_documents(
    directory: str = "documents/reference",
    category: str = "taikoken",
) -> dict:
    """ディレクトリ内のドキュメントをRAGに登録"""
    results = {
        "imported": 0,
        "failed": 0,
        "files": [],
    }

    # ディレクトリ内の全ファイルを取得
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
            if filepath.endswith(".md") or filepath.endswith(".txt"):
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
            elif filepath.endswith(".pdf"):
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(filepath)
                pages = loader.load()
                text = "\n".join([page.page_content for page in pages])

            if text:
                result = await rag_service.store_document(
                    filename=filename,
                    text=text,
                    category=category,
                )
                results["imported"] += 1
                results["files"].append({
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


async def import_single_document(
    filename: str,
    text: str,
    category: str = "taikoken",
    source_url: Optional[str] = None,
) -> dict:
    """単一ドキュメントをRAGに登録"""
    return await rag_service.store_document(
        filename=filename,
        text=text,
        category=category,
        source_url=source_url,
    )
