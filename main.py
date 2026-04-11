from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)
CORS(app)

ASSETS = [{'symbol':'BTC-USD','type':'crypto'},{'symbol':'ETH-USD','type':'crypto'},{'symbol':'NVDA','type':'stock'},{'symbol':'ASTS','type':'stock'},{'symbol':'GC=F','type':'commodity'},{'symbol':'CL=F','type':'commodity'},{'symbol':'PLUG','type':'stock'},{'symbol':'INVZ','type':'stock'},{'symbol':'SOFI','type':'stock'}]

def get_data(symbol, asset_type):
    try:
        t = yf.Ticker(symbol)
        d1 = t.history(period='3mo', interval='1d')
        dw = t.history(period='1y', interval='1wk')
        dh = t.history(period='5d', interval='1h')
        if d1.empty: return {'error': 'no_data'}
        price = round(float(d1['Close'].iloc[-1]), 2)
        prev = round(float(d1['Close'].iloc[-2]), 2)
        ma20 = round(float(d1['Close'].rolling(20).mean().iloc[-1]), 2)
        ma50 = round(float(d1['Close'].rolling(50).mean().iloc[-1]), 2)
        rsi_d = d1['Close'].diff()
        gain = rsi_d.clip(lower=0).rolling(14).mean()
        loss = -rsi_d.clip(upper=0).rolling(14).mean()
        rs = gain / loss.replace(0, float('nan'))
        rsi_1d = round(float(100 - (100/(1+rs.iloc[-1]))), 1)
        bb_ma = d1['Close'].rolling(20).mean()
        bb_std = d1['Close'].rolling(20).std()
        bb_upper = round(float((bb_ma + 2*bb_std).iloc[-1]), 2)
        bb_lower = round(float((bb_ma - 2*bb_std).iloc[-1]), 2)
        sup_1d = round(float(d1['Low'].rolling(20).min().iloc[-1]), 2)
        res_1d = round(float(d1['High'].rolling(20).max().iloc[-1]), 2)
        vc = int(d1['Volume'].iloc[-1])
        va = int(d1['Volume'].rolling(20).mean().iloc[-1])
        vol = 'high' if vc > va*1.5 else 'low' if vc < va*0.7 else 'average'
        result = {'symbol':symbol,'price':price,'change_pct':round((price-prev)/prev*100,2),'rsi_1d':rsi_1d,'bb_upper':bb_upper,'bb_lower':bb_lower,'ma20':ma20,'ma50':ma50,'support_1d':sup_1d,'resistance_1d':res_1d,'volume_signal':vol,'trend':'up' if price > ma50 else 'down'}
        if asset_type == 'stock':
            info = t.info
            result['analyst_target'] = info.get('targetMeanPrice')
            result['analyst_rec'] = info.get('recommendationKey','')
            result['eps_forward'] = info.get('epsForward')
        if asset_type == 'crypto':
            r = requests.get('https://api.alternative.me/fng/?limit=1', timeout=5).json()
            result['fear_greed'] = {'score':int(r['data'][0]['value']),'label':r['data'][0]['value_classification']}
        return result
    except Exception as e:
        return {'error':str(e),'symbol':symbol}

@app.route('/health')
def health():
    return jsonify({'status':'ok'})

@app.route('/scan/<path:symbol>')
def scan(symbol):
    asset = next((a for a in ASSETS if a['symbol']==symbol),None)
    if not asset: return jsonify({'error':'not found'}),404
    return jsonify(get_data(symbol, asset['type']))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)