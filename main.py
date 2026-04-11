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

def rsi(series, period=14):
    try:
        d = series.diff()
        gain = d.clip(lower=0).rolling(period).mean()
        loss = -d.clip(upper=0).rolling(period).mean()
        rs = gain / loss.replace(0, float('nan'))
        return round(float(100 - (100 / (1 + rs.iloc[-1]))), 1)
    except:
        return None

def bb(series, period=20):
    try:
        ma = series.rolling(period).mean()
        std = series.rolling(period).std()
        upper = round(float((ma + 2*std).iloc[-1]), 2)
        lower = round(float((ma - 2*std).iloc[-1]), 2)
        price = float(series.iloc[-1])
        if price >= upper * 0.98:
            signal = 'near_upper'
        elif price <= lower * 1.02:
            signal = 'near_lower'
        else:
            signal = 'middle'
        return {'upper': upper, 'lower': lower, 'signal': signal}
    except:
        return None

def macd(series):
    try:
        m = series.ewm(span=12).mean() - series.ewm(span=26).mean()
        s = m.ewm(span=9).mean()
        return 'up' if m.iloc[-1] > s.iloc[-1] else 'down'
    except:
        return None

def fib(df, period=60):
    try:
        high = float(df['High'].tail(period).max())
        low = float(df['Low'].tail(period).min())
        diff = high - low
        return {
            '0.236': round(high - 0.236*diff, 2),
            '0.382': round(high - 0.382*diff, 2),
            '0.5': round(high - 0.5*diff, 2),
            '0.618': round(high - 0.618*diff, 2),
        }
    except:
        return {}

def sr(df, n=20):
    try:
        sup = round(float(df['Low'].rolling(n).min().iloc[-1]), 2)
        res = round(float(df['High'].rolling(n).max().iloc[-1]), 2)
        return sup, res
    except:
        return None, None

def get_data(symbol, asset_type):
    try:
        t = yf.Ticker(symbol)
        d1 = t.history(period='3mo', interval='1d')
        dw = t.history(period='1y', interval='1wk')
        dh = t.history(period='5d', interval='1h')
        if d1.empty:
            return {'error': 'no_data', 'symbol': symbol}
        price = round(float(d1['Close'].iloc[-1]), 2)
        prev = round(float(d1['Close'].iloc[-2]), 2)
        ma20 = round(float(d1['Close'].rolling(20).mean().iloc[-1]), 2)
        ma50 = round(float(d1['Close'].rolling(50).mean().iloc[-1]), 2)
        ma200 = round(float(d1['Close'].rolling(200).mean().iloc[-1]), 2) if len(d1) >= 200 else None
        sup1d, res1d = sr(d1, 20)
        sup1w, res1w = sr(dw, 10) if not dw.empty else (None, None)
        sup1h, res1h = sr(dh, 10) if not dh.empty else (None, None)
        vc = int(d1['Volume'].iloc[-1])
        va = int(d1['Volume'].rolling(20).mean().iloc[-1])
        vol = 'high' if vc > va*1.5 else 'low' if vc < va*0.7 else 'average'
        result = {
            'symbol': symbol,
            'price': price,
            'change_pct': round((price-prev)/prev*100, 2),
            'high_1d': round(float(d1['High'].iloc[-1]), 2),
            'low_1d': round(float(d1['Low'].iloc[-1]), 2),
            'high_52w': round(float(dw['High'].max()), 2) if not dw.empty else None,
            'low_52w': round(float(dw['Low'].min()), 2) if not dw.empty else None,
            'rsi_1h': rsi(dh['Close']) if not dh.empty else None,
            'rsi_1d': rsi(d1['Close']),
            'rsi_1w': rsi(dw['Close']) if not dw.empty else None,
            'bb': bb(d1['Close']),
            'macd': macd(d1['Close']),
            'ma20': ma20,
            'ma50': ma50,
            'ma200': ma200,
            'support_1h': sup1h,
            'resistance_1h': res1h,
            'support_1d': sup1d,
            'resistance_1d': res1d,
            'support_1w': sup1w,
            'resistance_1w': res1w,
            'fib': fib(dw) if not dw.empty else {},
            'volume_today': vc,
            'volume_avg': va,
            'volume_signal': vol,
            'trend': 'up' if price > ma50 else 'down',
        }
        if asset_type == 'stock':
            try:
                info = t.info
                result['analyst_target'] = info.get('targetMeanPrice')
                result['analyst_rec'] = info.get('recommendationKey', '')
                result['eps_forward'] = info.get('epsForward')
                result['eps_trailing'] = info.get('trailingEps')
                cal = t.calendar
                if cal is not None and 'Earnings Date' in cal:
                    result['earnings_date'] = str(cal['Earnings Date'][0])
                news = t.news or []
                result['news'] = [{'title': n.get('title', ''), 'link': n.get('link', '')} for n in news[:3]]
            except:
                pass
        if asset_type == 'crypto':
            try:
                r = requests.get('https://api.alternative.me/fng/?limit=1', timeout=5).json()
                result['fear_greed'] = {'score': int(r['data'][0]['value']), 'label': r['data'][0]['value_classification']}
            except:
                pass
        return result
    except Exception as e:
        return {'error': str(e), 'symbol': symbol}

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/scan/<path:symbol>')
def scan(symbol):
    asset = next((a for a in ASSETS if a['symbol'] == symbol), None)
    if not asset:
        return jsonify({'error': 'not found'}), 404
    return jsonify(get_data(symbol, asset['type']))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
