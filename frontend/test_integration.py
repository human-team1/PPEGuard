import sys
import os
import time

# add frontend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.api_client import ApiClient

def test_integration():
    client = ApiClient("http://127.0.0.1:5000")
    
    print("--- 1. Health Check Test ---")
    try:
        health = client.check_health()
        print("Health OK:", health)
    except Exception as e:
        print("Health FAIL:", e)
        return

    print("\n--- 2. Start Session (Video) Test ---")
    try:
        session = client.start_session("VIDEO_FILE", "test.mp4")
        print("Session OK:", session)
        session_id = session.get('session_id')
    except Exception as e:
        print("Session FAIL:", e)
        return

    print("\n--- 3. Get Results List Test ---")
    time.sleep(2) # 백엔드 더미 비동기 처리 대기
    try:
        results = client.get_results(limit=10)
        print(f"Results OK: {len(results)} items found")
        result_id = None
        if isinstance(results, list) and len(results) > 0:
            result_id = results[0].get('id')
    except Exception as e:
        print("Results FAIL:", e)
        return

    if result_id:
        print(f"\n--- 4. Get Result Detail ({result_id}) Test ---")
        try:
            detail = client.get_result_detail(result_id)
            print("Detail OK. Keys:", list(detail.keys()))
        except Exception as e:
            print("Detail FAIL:", e)
    else:
        print("\n--- 4. Get Result Detail Skipped (No results yet) ---")
    
    print("\n=== All Integration Tests Completed! ===")

if __name__ == "__main__":
    test_integration()
