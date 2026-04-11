from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)
CORS(app)

ASSETS = [
    {'symbol': 'BTC-USD', 'type': 'crypto'},
    {'symbol': 'ETH-USD', 'type': 'crypto'},
    {'symbol': 'NVDA', 'type': 'stock'},
    {'symbol': 'ASTS', 'type': 'stock'},
    {'symbol': 'GC=F', 'type': 'commodity'},
    {'symbol': 'CL=F', 'type': 'commodity'},
    {'symbol': 'PLUG', 'type': 'stock'},
    {'symbol': 'INVZ', 'type': 'stock'},
    {'symbol': 'SOFI', 'type': 'stock'},
]

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/scan/<path:symbol>')
def scan(symbol):
    return jsonify({'symbol': symbol})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)