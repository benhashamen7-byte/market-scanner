from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/scan/<symbol>")
def scan(symbol):
    return jsonify({"symbol": symbol, "status": "coming soon"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
