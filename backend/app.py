from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "backend is running"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)