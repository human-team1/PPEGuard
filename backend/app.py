import os
import sys

# Ensure backend root is in PYTHONPATH if app.py is invoked directly
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

if __name__ == "__main__":
    # 앱 시작 시 데이터베이스 테이블 자동 생성
    from app.infrastructure.service_db.init_db import create_db_tables
    create_db_tables()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)