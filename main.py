from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import threading
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

TELEGRAM_TOKEN = '7874946726:AAFmRTpLAsza2AI4oPw-9s4Crha4DJl_-BQ'
CHAT_ID = '565025973'

ASSETS = [
    {'symbol': 'BTC-USD', 'type': 'crypto', 'name': 'Bitcoin'},
    {'symbol': 'ETH-USD', 'type': 'crypto', 'name': '??\'????'},
    {'symbol': 'NVDA', 'type': 'stock', 'name': 'Nvidia'},
    {'symbol': 'ASTS', 'type': 'stock', 'name': 'AST SpaceMobile'},
    {'symbol': 'GC=F', 'type': 'commodity', 'name': 'Gold'},
    {'symbol': 'CL=F', 'type': 'commodity', 'name': 'Oil'},
    {'symbol': 'PLUG', 'type': 'stock', 'name': 'Plug Power'},
    {'symbol': 'INVZ', 'type': 'stock', 'name': 'Innoviz'},
    {'symbol': 'SOFI', 'type': 'stock', 'name': 'SoFi'},
]

def send_telegram(msg):
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'},
            timeout=10
        )
    except:
        pass

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

def calc_macd(series):
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
        rsi_1d = rsi(d1['Close'])
        result = {
            'symbol': symbol,
            'price': price,
            'change_pct': round((price-prev)/prev*100, 2),
            'high_1d': round(float(d1['High'].iloc[-1]), 2),
            'low_1d': round(float(d1['Low'].iloc[-1]), 2),
            'high_52w': round(float(dw['High'].max()), 2) if not dw.empty else None,
            'low_52w': round(float(dw['Low'].min()), 2) if not dw.empty else None,
            'rsi_1h': rsi(dh['Close']) if not dh.empty else None,
            'rsi_1d': rsi_1d,
            'rsi_1w': rsi(dw['Close']) if not dw.empty else None,
            'bb': bb(d1['Close']),
            'macd': calc_macd(d1['Close']),
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

def score_asset(data):
    score = 5
    rsi_1d = data.get('rsi_1d')
    if rsi_1d:
        if rsi_1d < 30: score += 2
        elif rsi_1d > 70: score -= 2
    bb_data = data.get('bb')
    if bb_data:
        if bb_data['signal'] == 'near_lower': score += 1
        elif bb_data['signal'] == 'near_upper': score -= 1
    if data.get('macd') == 'up': score += 1
    if data.get('trend') == 'up': score += 1
    if data.get('volume_signal') == 'high': score += 1
    return max(1, min(10, score))

def get_recommendation(score):
    if score >= 7: return 'BUY'
    if score <= 4: return 'SELL'
    return 'HOLD'

def get_direction(score):
    if score >= 7: return 'LONG'
    if score <= 4: return 'SHORT'
    return 'HOLD'

def get_hot_movers():
    hot = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Yahoo Finance Day Gainers and Losers
        urls = [
            'https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=day_gainers&count=25',
            'https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=day_losers&count=25',
        ]
        symbols_data = []
        for url in urls:
            try:
                r = requests.get(url, timeout=10, headers=headers)
                if r.ok:
                    quotes = r.json().get('finance', {}).get('result', [{}])[0].get('quotes', [])
                    for q in quotes:
                        sym = q.get('symbol', '')
                        chg = q.get('regularMarketChangePercent', 0)
                        price = q.get('regularMarketPrice', 0)
                        mkt_cap = q.get('marketCap', 0)
                        name = q.get('shortName', sym)
                        exchange = q.get('exchange', '')
                        # Filter: 10%+ move, price > $5, market cap > $500M, major exchange
                        if abs(chg) >= 10 and price >= 5 and mkt_cap >= 500000000 and exchange in ['NMS', 'NYQ', 'NGM', 'NCM']:
                            hot.append({
                                'symbol': sym,
                                'name': name,
                                'price': round(price, 2),
                                'change_pct': round(chg, 2),
                                'market_cap': mkt_cap,
                            })
            except:
                continue
    except:
        pass
    # Remove duplicates and sort by absolute change
    seen = set()
    unique = []
    for m in hot:
        if m['symbol'] not in seen:
            seen.add(m['symbol'])
            unique.append(m)
    return sorted(unique, key=lambda x: abs(x['change_pct']), reverse=True)[:8]


def build_telegram_message(session_name):
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    msg = f'<b>[SCAN] Market Scan - {session_name}</b>\n'
    msg += f'<i>{now}</i>\n\n'

    for asset in ASSETS:
        data = get_data(asset['symbol'], asset['type'])
        if not data or data.get('error'):
            msg += f"[!] {asset['name']} - Error\n\n"
            continue

        score = score_asset(data)
        rec = get_recommendation(score)
        direction = get_direction(score)
        dot = '[G]' if rec == 'BUY' else '[R]' if rec == 'SELL' else '[Y]'

        rsi_1d = data.get('rsi_1d', 'N/A')
        rsi_warn = ' [!]' if rsi_1d and (rsi_1d > 70 or rsi_1d < 30) else ''

        msg += f"{dot} <b>{asset['name']} ({asset['symbol']})</b>\n"
        msg += f"Price: ${data['price']} ({'+' if data['change_pct'] > 0 else ''}{data['change_pct']}%)\n"
        msg += f"Score: {score}/10 | {rec} | {direction}\n"
        msg += f"RSI: {rsi_1d}{rsi_warn} | MACD: {'UP' if data.get('macd') == 'up' else 'DOWN'}\n"
        msg += f"Sup: {data.get('support_1d')} | Res: {data.get('resistance_1d')}\n"

        if data.get('earnings_date'):
            msg += f"Earnings: {data['earnings_date']}\n"

        if data.get('fear_greed'):
            fg = data['fear_greed']
            msg += f"F&G: {fg['score']} ({fg['label']})\n"

        msg += '\n'

    msg += '<b>--- HOT MOVERS (+/-10%) ---</b>\n'
    hot = get_hot_movers()
    if hot:
        for m in hot:
            arrow = 'UP' if m['change_pct'] > 0 else 'DOWN'
            msg += f"{arrow} <b>{m['symbol']}</b> {m['name']}\n"
            msg += f"   ${m['price']} | {'+' if m['change_pct'] > 0 else ''}{m['change_pct']}%\n"
    else:
        msg += 'No big movers found\n'

    return msg


def run_scheduled_scan(session_name):
    try:
        msg = build_telegram_message(session_name)
        send_telegram(msg)
    except Exception as e:
        send_telegram(f'Error scan: {str(e)}')

def keep_alive():
    while True:
        try:
            requests.get('https://market-scanner-1-aswt.onrender.com/health', timeout=10)
        except:
            pass
        time.sleep(600)

def scheduler():
    while True:
        now = datetime.utcnow()
        hour = now.hour
        minute = now.minute
        # 12:30 UTC = 15:30 Israel = 1hr before NYSE Open
        if hour == 12 and minute == 30:
            threading.Thread(target=run_scheduled_scan, args=('Before NYSE Open',)).start()
            time.sleep(61)
        # 19:00 UTC = 22:00 Israel = 1hr before NYSE Close
        elif hour == 19 and minute == 0:
            threading.Thread(target=run_scheduled_scan, args=('Before NYSE Close',)).start()
            time.sleep(61)
        else:
            time.sleep(30)

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/scan/<path:symbol>')
def scan(symbol):
    asset = next((a for a in ASSETS if a['symbol'] == symbol), None)
    if not asset:
        return jsonify({'error': 'not found'}), 404
    return jsonify(get_data(symbol, asset['type']))

@app.route('/scan-all')
def scan_all():
    results = {}
    for asset in ASSETS:
        results[asset['symbol']] = get_data(asset['symbol'], asset['type'])
    return jsonify(results)

@app.route('/hot-movers')
def hot_movers():
    return jsonify(get_hot_movers())

@app.route('/test-telegram')
def test_telegram():
    send_telegram('[OK] Bot connected! You will receive 2 scans per day.')
    return jsonify({'status': 'sent'})

@app.route('/scan-now')
def scan_now():
    threading.Thread(target=run_scheduled_scan, args=('Manual Scan',)).start()
    return jsonify({'status': 'scanning'})

scheduler_thread = threading.Thread(target=scheduler, daemon=True)
scheduler_thread.start()

keepalive_thread = threading.Thread(target=keep_alive, daemon=True)
keepalive_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
