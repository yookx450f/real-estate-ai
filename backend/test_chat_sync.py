#!/usr/bin/env python3
"""チャットAPIテストスクリプト - gemma4:12b-mlx 動作確認用（同期版）"""

import httpx
import sys
import time

# 設定
API_BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{API_BASE_URL}/api/chat/"
LOGIN_ENDPOINT = f"{API_BASE_URL}/api/auth/login"

# 認証情報（デフォルトユーザー）
TEST_EMAIL = "admin@example.com"
TEST_PASSWORD = "admin123"

# テスト質問（不動産法律関連）
TEST_QUERIES = [
    "借地契約を更新しない場合、借地権者はどのような補償を受けられますか？",
    "賃貸物件の敷金の返還について教えてください。",
]


def test_api_health():
    """APIヘルスチェック"""
    print("=" * 60)
    print("gemma4:12b-mlx モデル チャットAPI テスト")
    print("=" * 60)
    print("\n[1] APIヘルスチェック...")
    
    try:
        client = httpx.Client()
        response = client.get(f"{API_BASE_URL}/docs", timeout=10)
        client.close()
        
        if response.status_code == 200:
            print("   ✓ APIサーバーは正常に動作しています")
            return True
        else:
            print(f"   ✗ APIサーバーエラー: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ APIサーバーに接続できません: {e}")
        return False


def test_ollama():
    """Ollama接続確認"""
    print("\n[2] Ollama接続確認...")
    
    try:
        client = httpx.Client()
        response = client.get(
            "http://host.docker.internal:11434/api/tags",
            timeout=10
        )
        client.close()
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            print(f"   ✓ Ollamaは正常に動作しています")
            print(f"   インストールされているモデル: {', '.join(model_names)}")
            
            if "gemma4:12b-mlx" in model_names:
                print("   ✓ gemma4:12b-mlx モデルが見つかりました")
                return True
            else:
                print("   ⚠ gemma4:12b-mlx モデルが見つかりません")
                return False
        else:
            print(f"   ✗ Ollamaエラー: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Ollamaに接続できません: {e}")
        return False


def get_auth_token():
    """認証トークンを取得"""
    print("\n[3] 認証トークンの取得...")
    
    try:
        client = httpx.Client()
        response = client.post(
            LOGIN_ENDPOINT,
            data={
                "username": TEST_EMAIL,
                "password": TEST_PASSWORD,
            }
        )
        client.close()
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"   ✓ 認証成功: トークンを取得しました")
            return token
        else:
            print(f"   ✗ 認証エラー: {response.status_code}")
            print(f"   応答: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"   ✗ エラーが発生しました: {e}")
        return None


def test_chat_api(token):
    """チャットAPIテスト"""
    print("\n[4] チャットAPIテスト...")
    print("-" * 60)

    headers = {"Authorization": f"Bearer {token}"}

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n--- テスト {i}/{len(TEST_QUERIES)} ---")
        print(f"質問: {query}")
        
        try:
            client = httpx.Client()
            payload = {
                "message": query,
                "conversation_id": "test"
            }
            
            start_time = time.time()
            response = client.post(
                API_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=120  # LLM応答用の長いタイムアウト
            )
            elapsed_time = time.time() - start_time
            client.close()
            
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
                print(f"   応答: {response.text[:500]}")
                
        except httpx.TimeoutException:
            print("   ✗ タイムアウトしました。LLMサーバーが応答していません。")
        except Exception as e:
            print(f"   ✗ エラーが発生しました: {e}")

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)
    return True


if __name__ == "__main__":
    health_ok = test_api_health()
    if not health_ok:
        sys.exit(1)
    
    ollama_ok = test_ollama()
    if not ollama_ok:
        sys.exit(1)
    
    token = get_auth_token()
    if not token:
        sys.exit(1)
    
    test_chat_api(token)
