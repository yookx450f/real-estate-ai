"""ドキュメントインポーター - ファイルからのドキュメント登録"""

import os
import re
import glob
from typing import Optional

from app.core.rag import rag_service


def extract_evidence_info(text: str, filename: str) -> dict:
    """
    テキストからエビデンス情報（法令名、条文番号、参照文章）を抽出
    
    Args:
        text: ドキュメントのテキスト
        filename: ファイル名
    
    Returns:
        エビデンス情報辞書
    """
    evidence_info = {
        "law_name": "",
        "article_number": "",
        "section": "",
        "document_title": filename.replace(".md", "").replace(".txt", "").replace(".pdf", ""),
        "evidence_text": "",
    }
    
    # ファイル名から法令名を推測（例：taikoken_hourei_shikourei.md -> 宅地建物取引業法施行規則）
    # または、テキスト内の見出しから抽出
    
    # 法令名の抽出（「〇〇法」「〇〇条例」のパターン）
    law_patterns = [
        r'([第号])([^\n]+?)([法条例])',
        r'([^\n]*?[法条例][^\n]*)',
    ]
    
    for pattern in law_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # 最初の法令名を使用
            for match in matches:
                if isinstance(match, tuple):
                    law_name = ''.join(match).strip()
                else:
                    law_name = match.strip()
                
                if len(law_name) > 2 and len(law_name) < 50:
                    evidence_info["law_name"] = law_name
                    break
            if evidence_info["law_name"]:
                break
    
    # 条文番号の抽出（「第〇条」のパターン）
    article_matches = re.findall(r'第([0-9０-９]+)条', text)
    if article_matches:
        # 最初の条文番号を使用
        first_article = article_matches[0]
        # 全角数字を半角に変換
        fullwidth_digits = str.maketrans('０１２３４５６７８９', '0123456789')
        first_article = first_article.translate(fullwidth_digits)
        evidence_info["article_number"] = first_article
    
    # 項・号の抽出（「第〇号」「(〇)」「〇項」のパターン）
    section_matches = re.findall(r'[第号](?:([0-9０-９]+))|[((](?:([0-9０-９]+))[))]', text)
    if section_matches:
        first_section = section_matches[0]
        if isinstance(first_section, tuple):
            for s in first_section:
                if s:
                    evidence_info["section"] = s.translate(fullwidth_digits)
                    break
        elif first_section:
            evidence_info["section"] = first_section.translate(fullwidth_digits)
    
    # 参照文章の抽出（条文の内容や主要な文章）
    # 「第〇条」に続く文章を検索
    article_content_matches = re.findall(r'第[0-9０-９]+条[^\n]*(?:[^\n]*\n){0,5}', text)
    if article_content_matches:
        # 最初の条文の内容を参照文章として使用
        evidence_text = article_content_matches[0].strip()
        # 500 文字に制限
        if len(evidence_text) > 500:
            evidence_text = evidence_text[:500] + "..."
        evidence_info["evidence_text"] = evidence_text
    else:
        # 条文が見つからない場合は、最初の段落を参照文章として使用
        paragraphs = text.split('\n\n')
        if paragraphs:
            evidence_info["evidence_text"] = paragraphs[0][:500]
    
    return evidence_info


async def import_documents(
    directory: str = "documents/reference",
    category: str = "taikoken",
) -> dict:
    """ディレクトリ内のドキュメントを RAG に登録"""
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
                # エビデンス情報を抽出
                evidence_info = extract_evidence_info(text, filename)
                
                result = await rag_service.store_document(
                    filename=filename,
                    text=text,
                    category=category,
                    evidence_info=evidence_info,  # エビデンス情報を追加
                )
                results["imported"] += 1
                results["files"].append({
                    "filename": filename,
                    "chunks": result["chunk_count"],
                    "status": "success",
                    "evidence_info": evidence_info,
                })
                print(f"  登録完了: {filename} - 法令: {evidence_info['law_name']}, 条文: {evidence_info['article_number']}")
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
    evidence_info: Optional[dict] = None,
) -> dict:
    """単一ドキュメントを RAG に登録"""
    # エビデンス情報が指定されていない場合は自動抽出
    if evidence_info is None:
        evidence_info = extract_evidence_info(text, filename)
    
    return await rag_service.store_document(
        filename=filename,
        text=text,
        category=category,
        source_url=source_url,
        evidence_info=evidence_info,
    )
