"""测试 Qwen API key 可用模型"""
import json
import os
import urllib.request
import urllib.error

API_KEY = os.getenv("AI_API_KEY", "")
BASE_URL = os.getenv(
    "AI_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def test_list_models():
    """1. 列出可用模型"""
    req = urllib.request.Request(
        f"{BASE_URL}/models",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            models = data.get("data", [])
            print(f"=== 可用模型列表 (共 {len(models)} 个) ===")
            print()
            for m in models:
                mid = m.get("id", "")
                owned = m.get("owned_by", "")
                obj = m.get("object", "")
                print(f"  {mid}")
                print(f"    owned_by: {owned}, object: {obj}")
            return [m.get("id") for m in models]
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(e.read().decode())
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []


def test_simple_chat(model_id: str):
    """2. 测试简单对话"""
    body = json.dumps({
        "model": model_id,
        "messages": [
            {"role": "system", "content": "你是一个面试助手。"},
            {"role": "user", "content": "请用一句话介绍自己。"}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            print(f"  OK 测试通过")
            print(f"     响应: {content[:80]}...")
            print(f"     Token: {usage}")
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"  FAIL 测试失败: {e.code}")
        try:
            err_json = json.loads(err_body)
            print(f"     {err_json.get('message', '')}")
        except Exception:
            print(f"     {err_body[:200]}")
        return False
    except Exception as e:
        print(f"  FAIL 测试失败: {e}")
        return False


def main():
    # Step 1: 列出模型
    model_ids = test_list_models()
    if not model_ids:
        print("\nWARNING: 无法获取模型列表，尝试用已知的 Qwen 模型名直接测试")
        # 备选：直接测试常见模型
        model_ids = [
            "qwen-plus",
            "qwen-turbo",
            "qwen-max",
            "qwen-max-2026-04-30",
            "qwen-long",
            "qwen3-235b-a3b",
            "qwen3-30b-a3b",
            "qwen3-14b-a3b",
        ]

    print("\n=== 逐个测试模型对话能力 ===\n")

    # 筛选出可能适合的模型（排除 embedding 等非对话模型）
    chat_models = [
        m for m in model_ids
        if not any(x in m.lower() for x in [
            "embedding", "text-embedding", "rerank",
            "whisper", "tts", "vlm", "video", "audio", "aigc"
        ])
    ]

    working = []
    failed = []

    for model_id in chat_models:
        print(f"测试: {model_id}")
        ok = test_simple_chat(model_id)
        if ok:
            working.append(model_id)
        else:
            failed.append(model_id)
        print()

    print("=" * 50)
    print("=== 测试结果汇总 ===")
    print(f"可用的对话模型 ({len(working)}):")
    for m in working:
        print(f"  OK {m}")
    print(f"\n不可用 ({len(failed)}):")
    for m in failed:
        print(f"  FAIL {m}")


if __name__ == "__main__":
    main()