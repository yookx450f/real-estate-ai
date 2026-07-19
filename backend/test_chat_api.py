#!/usr/bin/env python3
"""チャットAPIテストスクリプト - gemma4:12b-mlx 動作確認用"""

import asyncio
import json
import sys
import time

import httpx

# 設定
# コンテナ内からはlocalhost:8000を使用
API_BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{API_BASE_URL}/api/chat/"

# テスト質問（不動産法律関連）
TEST_QUERIES = [
    # 借地借家法に関する質問
    "借地契約を更新しない場合、借地権者はどのような補償を受けられますか？",
    # 敷金に関する質問
    "賃貸物件の敷金の返還について教えてください。",
    # 建物に関する質問
    "建物の売買契約で重要な確認事項は何がありますか？",
]


async def test_chat_api():
    """チャットAPIをテスト"""
    print("=" * 60)
    print("gemma4:12b-mlx モデル チャットAPI テスト")
    print("=" * 60)

    # 1. APIヘルスチェック
    print("\n[1] APIヘルスチェック...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/docs", timeout=10)
            if response.status_code == 200:
                print("   ✓ APIサーバーは正常に動作しています")
            else:
                print(f"   ✗ APIサーバーエラー: {response.status_code}")
                return False
    except Exception as e:
        print(f"   ✗ APIサーバーに接続できません: {e}")
        print("   バックエンドサーバーが起動しているか確認してください")
        return False

    # 2. Ollama接続確認
    print("\n[2] Ollama接続確認...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://host.docker.internal:11434/api/tags",
                timeout=10
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                print(f"   ✓ Ollamaは正常に動作しています")
                print(f"   インストールされているモデル: {', '.join(model_names)}")
                
                if "gemma4:12b-mlx" in model_names:
                    print("   ✓ gemma4:12b-mlx モデルが見つかりました")
                else:
                    print("   ⚠ gemma4:12b-mlx モデルが見つかりません")
            else:
                print(f"   ✗ Ollamaエラー: {response.status_code}")
                return False
    except Exception as e:
        print(f"   ✗ Ollamaに接続できません: {e}")
        print("   Ollamaが起動しているか確認してください (http://host.docker.internal:11434)")
        return False

    # 3. チャットAPIテスト
    print("\n[3] チャットAPIテスト...")
    print("-" * 60)

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n--- テスト {i}/{len(TEST_QUERIES)} ---")
        print(f"質問: {query}")
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "message": query,
                    "conversation_id": "test"
                }
                
                start_time = time.time()
                response = await client.post(
                    API_ENDPOINT,
                    json=payload,
                    timeout=120  # LLM応答用の長いタイムアウト
                )
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✓ レスポンスステータス: {response.status_code}")
                    print(f"   応答時間: {elapsed_time:.2f}秒")
                    print(f"\n[AI回答]")
                    print("-" * 40)
                    print(data.get("answer", "回答なし"))
                    print("-" * 40)
                    
                    sources = data.get("sources", [])
                    if sources:
                        print(f"\n[参照元] ({len(sources)}件)")
                        for j, source in enumerate(sources, 1):
                            print(f"  {j}. {source.get('filename', 'N/A')} (スコア: {source.get('score', 0):.4f})")
                            # 最初のソースのテキストを一部表示
                            text = source.get("text", "")
                            if text:
                                print(f"     ...{text[:100]}...")
                    else:
                        print("\n   ⚠ 参照ソースがありません。RAGコレクションを確認してください。")
                else:
                    print(f"   ✗ APIエラー: {response.status_code}")
                    print(f"   応答: {response.text[:200]}")
                    
        except httpx.TimeoutException:
            print("   ✗ タイムアウトしました。LLMサーバーが応答していません。")
        except Exception as e:
            print(f"   ✗ エラーが発生しました: {e}")

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_chat_api())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nテストが中断されました")
        sys.exit(1)
