import os
import sys
import eventlet

# [최종 안정화: gevent 대신 윈도우에서 가장 검증된 eventlet 조합 유지]
eventlet.monkey_patch()

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    # 포트 5000번 (안정적인 분석 환경 보장)
    port = int(os.environ.get("PORT", 5000))
    
    print(f"--- [PPE Guard] 실시간 AI 분석 서버 가동 중 (Port: {port}) ---", flush=True)
    

    # app.run(host="0.0.0.0", port=port, debug=True)
    socketio.run(
        app, 
        host="127.0.0.1", 
        port=port, 
        debug=False,
        log_output=False # 이제 안정적이므로 상세 로그는 끕니다.
    )