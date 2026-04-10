from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(**name**)
CORS(app)

ASSETS = [
{“symbol”: “BTC-USD”, “type”: “crypto”},
{“symbol”: “ETH-USD”, “type”: “crypto”},
{“symbol”: “NVDA”, “type”: “stock”},
{“symbol”: “ASTS”, “type”: “stock”},
{“symbol”: “GC=F”, “type”: “commodity”},
{“symbol”: “CL=F”, “type”: “commodity”},
{“symbol”: “PLUG”, “type”: “stock”},
{“symbol”: “INVZ”, “type”: “stock”},
{“symbol”: “SOFI”, “type”: “stock”},
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
signal = “near_upper”
elif price <= lower * 1.02:
signal = “near_lower”
else:
signal = “middle”
return {“upper”: round(upper, 2), “lower”: round(lower, 2), “signal”: signal}
except:
return None

def calc_macd(series):
try:
macd = series.ewm(span=12).mean() - series.ewm(span=26).mean()
signal = macd.ewm(span=9).mean()
diff = macd.iloc[-1] - signal.iloc[-1]
if diff > 0:
return “up”
elif diff < 0:
return “down”
return “neutral”
except:
return None

def calc_support_resistance(df, n=20):
try:
sup = round(float(df[‘Low’].rolling(n).min().iloc[-1]), 2)
res = round(float(df[‘High’].rolling(n).max().iloc[-1]), 2)
return sup, res
except:
return None, None

def calc_fib(df, period=60):
try:
high = float(df[‘High’].tail(period).max())
low = float(df[‘Low’].tail(period).min())
diff = high - low
return {
“0.236”: round(high - 0.236 * diff, 2),
“0.382”: round(high - 0.382 * diff, 2),
“0.5”: round(high - 0.5 * diff, 2),
“0.618”: round(high - 0.618 * diff, 2),
}
except:
return {}

def get_fear_greed():
try:
r = requests.get(“https://api.alternative.me/fng/?limit=1”, timeout=5)
d = r.json()
return {“score”: int(d[‘data’][0][‘value’]), “label”: d[‘data’][0][‘value_classification’]}
except:
return {“score”: 50, “label”: “Neutral”}

def get_asset_data(symbol, asset_type):
try:
ticker = yf.Ticker(symbol)
df_1d = ticker.history(period=“3mo”, interval=“1d”)
df_1w = ticker.history(period=“1y”, interval=“1wk”)
df_1h = ticker.history(period=“5d”, interval=“1h”)

```
    if df_1d.empty:
        return {"error": "no_data", "symbol": symbol}

    price = round(float(df_1d['Close'].iloc[-1]), 2)
    prev = round(float(df_1d['Close'].iloc[-2]), 2)
    change_pct = round((price - prev) / prev * 100, 2)

    ma20 = round(float(df_1d['Close'].rolling(20).mean().iloc[-1]), 2)
    ma50 = round(float(df_1d['Close'].rolling(50).mean().iloc[-1]), 2)
    ma200 = round(float(df_1d['Close'].rolling(200).mean().iloc[-1]), 2) if len(df_1d) >= 200 else None

    sup_1d, res_1d = calc_support_resistance(df_1d, 20)
    sup_1w, res_1w = calc_support_resistance(df_1w, 10) if not df_1w.empty else (None, None)
    sup_1h, res_1h = calc_support_resistance(df_1h, 10) if not df_1h.empty else (None, None)

    vol_cur = int(df_1d['Volume'].iloc[-1])
    vol_avg = int(df_1d['Volume'].rolling(20).mean().iloc[-1])
    if vol_cur > vol_avg * 1.5:
        vol_signal = "high"
    elif vol_cur < vol_avg * 0.7:
        vol_signal = "low"
    else:
        vol_signal = "average"

    if price > ma50:
        trend = "up"
    else:
        trend = "down"

    result = {
        "symbol": symbol,
        "price": price,
        "change_pct": change_pct,
        "high_1d": round(float(df_1d['High'].iloc[-1]), 2),
        "low_1d": round(float(df_1d['Low'].iloc[-1]), 2),
        "high_52w": round(float(df_1w['High'].max()), 2) if not df_1w.empty else None,
        "low_52w": round(float(df_1w['Low'].min()), 2) if not df_1w.empty else None,
        "rsi_1h": calc_rsi(df_1h['Close']) if not df_1h.empty else None,
        "rsi_1d": calc_rsi(df_1d['Close']),
        "rsi_1w": calc_rsi(df_1w['Close']) if not df_1w.empty else None,
        "bb": calc_bb(df_1d['Close']),
        "macd": calc_macd(df_1d['Close']),
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "support_1h": sup_1h,
        "resistance_1h": res_1h,
        "support_1d": sup_1d,
        "resistance_1d": res_1d,
        "support_1w": sup_1w,
        "resistance_1w": res_1w,
        "fib": calc_fib(df_1w) if not df_1w.empty else {},
        "volume_today": vol_cur,
        "volume_avg": vol_avg,
        "volume_signal": vol_signal,
        "trend": trend,
    }

    if asset_type == "stock":
        try:
            info = ticker.info
            result["analyst_target"] = info.get("targetMeanPrice")
            result["analyst_rec"] = info.get("recommendationKey", "")
            result["eps_forward"] = info.get("epsForward")
            result["eps_trailing"] = info.get("trailingEps")
            cal = ticker.calendar
            if cal is not None and "Earnings Date" in cal:
                result["earnings_date"] = str(cal["Earnings Date"][0])
            news = ticker.news or []
            result["news"] = [{"title": n.get("title", ""), "link": n.get("link", "")} for n in news[:3]]
        except:
            pass

    if asset_type == "crypto":
        result["fear_greed"] = get_fear_greed()

    return result

except Exception as e:
    return {"error": str(e), "symbol": symbol}
```

@app.route(”/health”)
def health():
return jsonify({“status”: “ok”})

@app.route(”/scan/<path:symbol>”)
def scan_one(symbol):
asset = next((a for a in ASSETS if a[“symbol”] == symbol), None)
if not asset:
return jsonify({“error”: “not found”}), 404
return jsonify(get_asset_data(symbol, asset[“type”]))

if **name** == “**main**”:
app.run(host=“0.0.0.0”, port=10000)
