import threading
import time
import urllib.request
import urllib.error
import json
import sys

from app import create_app
app = create_app()

def run_server():
    app.run(host="0.0.0.0", port=5001, use_reloader=False)

server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

time.sleep(2)

base_url = "http://127.0.0.1:5001"

def request_json(method, path, data=None):
    req = urllib.request.Request(base_url + path, method=method)
    if data is not None:
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(data).encode('utf-8')
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode('utf-8')
            return json.loads(res_data) if res_data else {}
    except urllib.error.HTTPError as e:
        return {"error": e.code, "msg": e.read().decode('utf-8')}

print("--- LOCAL API TEST ---")
print("1. GET /health")
print(request_json("GET", "/health"))

print("\n2. POST /api/v1/sessions")
session_data = request_json("POST", "/api/v1/sessions", {
    "source_type": "WEBCAM",
    "source_name": "Test-Webcam",
    "frame_interval_sec": 3,
    "requested_by": "admin"
})
print(session_data)
session_id = session_data.get("session_id")

if session_id:
    print(f"\n3. GET /api/v1/sessions/{session_id}")
    print(request_json("GET", f"/api/v1/sessions/{session_id}"))
    
    print("\n4. GET /api/v1/results")
    print(request_json("GET", "/api/v1/results"))

    print(f"\n5. POST /api/v1/sessions/{session_id}/stop")
    print(request_json("POST", f"/api/v1/sessions/{session_id}/stop"))
else:
    print("Session creation failed.")
    
sys.exit(0)
