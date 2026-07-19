"""テストスクリプト - 修正確認用"""

import asyncio
import sys
import os

# Add backend path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.llm import llm_service
from app.core.rag import rag_service


async def test_fix():
    """修正の確認"""
    print("=" * 50)
    print("[テスト] 埋め込み次元数の確認")
    print(f"  预期次元数: {llm_service.embedding_dimension}")
    
    # コレクションの初期化を試みる
    print("\n[テスト] コレクションの初期化")
    rag_service._init_collection()
    
    # 検索テスト
    print("\n[テスト] 検索テスト")
    try:
        sources = await rag_service.search("媒介契約の効力について", top_k=5)
        print(f"  検索結果: {len(sources)}件")
        for i, source in enumerate(sources):
            print(f"  [{i+1}] ファイル: {source.get('filename', 'N/A')}")
            print(f"      関連度: {source.get('score', 'N/A')}")
            print(f"      内容: {source.get('text', 'N/A')[:100]}...")
    except Exception as e:
        print(f"  エラー: {e}")
    
    # 完全なRAGテスト
    print("\n[テスト] 完全なRAGテスト")
    try:
        result = await rag_service.search_and_generate("媒介契約の効力について教えてください", top_k=5)
        print(f"  回答: {result['answer'][:200]}...")
        print(f"  参照元: {len(result['sources'])}件")
    except Exception as e:
        print(f"  エラー: {e}")


if __name__ == "__main__":
    asyncio.run(test_fix())
