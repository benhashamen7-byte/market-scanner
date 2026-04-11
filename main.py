from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(**name**)
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

def calc_rsi(series, period=14):
try:
delta = series.diff()
gain = delta.clip(lower=0).rolling(window=period).mean()
loss = -delta.clip(upper=0).rolling(window=period).mean()
rs = gain / loss.replace(0, np.nan)
val = 100 - (100 / (1 + rs.iloc[-1]))
return round(float(val), 1)
except:
return None

def calc_bb(series, period=20):
try:
ma = series.rolling(period).mean()
std = series.rolling(period).std()
upper = float((ma + 2 * std).iloc[-1])
lower = float((ma - 2 * std).iloc[-1])
price = float(series.iloc[-1])
if price >= upper * 0.98:
signal = 'near_upper'
elif price <= lower * 1.02:
signal = 'near_lower'
else:
signal = 'middle'
return {'upper': round(upper, 2), 'lower': round(lower, 2), 'signal': signal}
except:
return None

def calc_macd(series):
try:
macd = series.ewm(span=12).mean() - series.ewm(span=26).mean()
signal = macd.ewm(span=9).mean()
diff = macd.iloc[-1] - signal.iloc[-1]
if diff > 0:
return 'up'
elif diff < 0:
return 'down'
return 'neutral'
except:
return None

def calc_sr(df, n=20):
try:
sup = round(float(df['Low'].rolling(n).min().iloc[-1]), 2)
res = round(float(df['High'].rolling(n).max().iloc[-1]), 2)
return sup, res
except:
return None, None

def calc_fib(df, period=60):
try:
high = float(df['High'].tail(period).max())
low = float(df['Low'].tail(period).min())
diff = high - low
return {
'0.236': round(high - 0.236 * diff, 2),
'0.382': round(high - 0.382 * diff, 2),
'0.5': round(high - 0.5 * diff, 2),
'0.618': round(high - 0.618 * diff, 2),
}
except:
return {}

def get_fg():
try:
r = requests.get('https://api.alternative.me/fng/?limit=1', timeout=5)
d = r.json()
return {'score': int(d['data'][0]['value']), 'label': d['data'][0]['value_classification']}
except:
return {'score': 50, 'label': 'Neutral'}

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
s1d, r1d = calc_sr(d1, 20)
s1w, r1w = calc_sr(dw, 10) if not dw.empty else (None, None)
s1h, r1h = calc_sr(dh, 10) if not dh.empty else (None, None)
vc = int(d1['Volume'].iloc[-1])
va = int(d1['Volume'].rolling(20).mean().iloc[-1])
if vc > va * 1.5:
vs = 'high'
elif vc < va * 0.7:
vs = 'low'
else:
vs = 'average'
result = {
'symbol': symbol,
'price': price,
'change_pct': round((price - prev) / prev * 100, 2),
'high_1d': round(float(d1['High'].iloc[-1]), 2),
'low_1d': round(float(d1['Low'].iloc[-1]), 2),
'high_52w': round(float(dw['High'].max()), 2) if not dw.empty else None,
'low_52w': round(float(dw['Low'].min()), 2) if not dw.empty else None,
'rsi_1h': calc_rsi(dh['Close']) if not dh.empty else None,
'rsi_1d': calc_rsi(d1['Close']),
'rsi_1w': calc_rsi(dw['Close']) if not dw.empty else None,
'bb': calc_bb(d1['Close']),
'macd': calc_macd(d1['Close']),
'ma20': ma20,
'ma50': ma50,
'ma200': ma200,
'support_1h': s1h,
'resistance_1h': r1h,
'support_1d': s1d,
'resistance_1d': r1d,
'support_1w': s1w,
'resistance_1w': r1w,
'fib': calc_fib(dw) if not dw.empty else {},
'volume_today': vc,
'volume_avg': va,
'volume_signal': vs,
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
result['fear_greed'] = get_fg()
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

if **name** == '**main**':
app.run(host='0.0.0.0', port=10000)

