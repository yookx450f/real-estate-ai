"""ドキュメントをRAGに登録するスクリプト（修正版）"""

import asyncio
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.importer import import_documents, import_single_document
from app.core.rag import rag_service
from app.core.llm import llm_service


async def clear_collection():
    """コレクションの全データを削除"""
    client = rag_service.qdrant_client
    collection_name = rag_service.collection_name
    
    try:
        # コレクション内の全ポイントを取得
        offset = 0
        batch_size = 100
        all_ids = []
        
        while True:
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )
            points = scroll_result[0]
            if not points:
                break
            
            for point in points:
                all_ids.append(point.id)
            
            if len(points) < batch_size:
                break
            offset += batch_size
        
        # 全ポイントを削除
        if all_ids:
            # バッチ分けして削除（100件ずつ）
            for i in range(0, len(all_ids), 100):
                batch_ids = all_ids[i:i+100]
                client.delete(
                    collection_name=collection_name,
                    points_selector=batch_ids,
                )
            print(f"  既存の{len(all_ids)}件のデータを削除しました")
        
    except Exception as e:
        print(f"  削除中にエラーが発生しました: {str(e)}")


async def register_file(filepath: str) -> dict:
    """単一ファイルをRAGに登録"""
    filename = os.path.basename(filepath)
    
    try:
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
        
        if not text:
            return {"filename": filename, "chunks": 0, "status": "error", "reason": "ファイルが空です"}
        
        # テキストをチャンクに分割して登録
        result = await import_single_document(
            filename=filename,
            text=text,
            category="taikoken",
        )
        
        return {
            "filename": filename,
            "chunks": result.get("chunk_count", 0),
            "status": "success",
        }
    except Exception as e:
        return {
            "filename": filename,
            "chunks": 0,
            "status": "error",
            "reason": str(e),
        }


async def main():
    """ドキュメントをRAGに登録"""
    print("=== ドキュメントをRAGに登録（修正版）===")
    
    # 埋め込みモデルの状態を確認
    print("\n--- 埋め込みモデルの状態 ---")
    print(f"  埋め込み次元数: {llm_service.embedding_dimension}")
    print(f"  フォールバック状態: {llm_service._embedding_fallback}")
    print(f"  埋め込みモデル初期化エラー: {llm_service.embedding_model._init_error}")
    
    # 登録するディレクトリ
    directory = "documents/reference"
    category = "taikoken"
    
    # 既存のデータをクリア
    print("\n--- 既存データのクリア ---")
    await clear_collection()
    
    # ディレクトリ内の全ファイルを取得
    import glob
    
    patterns = [
        os.path.join(directory, "**", "*.md"),
        os.path.join(directory, "**", "*.txt"),
        os.path.join(directory, "**", "*.pdf"),
    ]
    
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern, recursive=True))
    
    print(f"\n--- 登録対象ファイル ({len(files)}件) ---")
    for f in files:
        print(f"  {os.path.basename(f)}")
    
    # 各ファイルを登録
    print("\n--- 各ファイルを登録中 ---")
    results = []
    for filepath in files:
        print(f"\n  処理中: {os.path.basename(filepath)}")
        try:
            result = await register_file(filepath)
            results.append(result)
            status_icon = "✓" if result['status'] == 'success' else "✗"
            print(f"    {status_icon} {result['filename']}: {result.get('chunks', 'N/A')}チャンク")
            if result.get('reason'):
                print(f"    エラー: {result['reason']}")
        except Exception as e:
            print(f"    ✗ {os.path.basename(filepath)}: エラー - {str(e)}")
            results.append({
                "filename": os.path.basename(filepath),
                "chunks": 0,
                "status": "error",
                "reason": str(e),
            })
    
    # 登録結果のサマリー
    imported_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = sum(1 for r in results if r['status'] != 'success')
    
    print(f"\n--- 登録結果 ---")
    print(f"登録数: {imported_count}")
    print(f"失敗数: {failed_count}")
    
    for result in results:
        status_icon = "✓" if result['status'] == 'success' else "✗"
        print(f"  {status_icon} {result['filename']}: {result.get('chunks', 'N/A')}チャンク")
    
    # 登録後の状態を確認
    print("\n--- 登録後のRAG状態 ---")
    try:
        client = rag_service.qdrant_client
        collection_name = rag_service.collection_name
        
        collection_info = client.get_collection(collection_name)
        total_points = collection_info.points_count
        print(f"総チャンク数: {total_points}")
        
        # 登録されているドキュメントのメタデータ取得
        documents = {}
        offset = 0
        batch_size = 100
        
        while True:
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points = scroll_result[0]
            if not points:
                break
            
            for point in points:
                payload = point.payload
                filename = payload.get("filename", "unknown")
                if filename not in documents:
                    documents[filename] = {
                        "filename": filename,
                        "category": payload.get("category", ""),
                        "chunk_count": 0,
                        "source_url": payload.get("source_url", ""),
                    }
                documents[filename]["chunk_count"] += 1
            
            if len(points) < batch_size:
                break
            offset += batch_size
        
        print("\n--- ドキュメント一覧 ---")
        for doc in sorted(documents.values(), key=lambda x: x['filename']):
            print(f"  {doc['filename']}: {doc['chunk_count']}チャンク (カテゴリ: {doc['category']})")
        
    except Exception as e:
        print(f"RAG状態の取得中にエラーが発生しました: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
