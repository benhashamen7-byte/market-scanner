from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import requests

app = Flask(__name__)
CORS(app)

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return round(float(100 - (100 / (1 + rs.iloc[-1]))), 1)

def calc_bb(series, period=20):
    ma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    price = series.iloc[-1]
    if price >= upper.iloc[-1] * 0.98:
        signal = "מחיר ליד גבול עליון"
    elif price <= lower.iloc[-1] * 1.02:
        signal = "מחיר ליד גבול תחתון"
    else:
        signal = "במרכז"
    return {"upper": round(upper.iloc[-1],2), "lower": round(lower.iloc[-1],2), "signal": signal}

def calc_macd(series):
    macd = series.ewm(span=12).mean() - series.ewm(span=26).mean()
    signal = macd.ewm(span=9).mean()
    return "עולה" if macd.iloc[-1] > signal.iloc[-1] else "יורד" if macd.iloc[-1] < signal.iloc[-1] else "ניטרלי"

def calc_support_resistance(df, n=20):
    return round(float(df['Low'].rolling(n).min().iloc[-1]),2), round(float(df['High'].rolling(n).max().iloc[-1]),2)

def calc_fib(df, period=60):
    high = df['High'].tail(period).max()
    low = df['Low'].tail(period).min()
    diff = high - low
    return {"0.236": round(high-0.236*diff,2), "0.382": round(high-0.382*diff,2), "0.5": round(high-0.5*diff,2), "0.618": round(high-0.618*diff,2)}

def get_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        d = r.json()
        return {"score": int(d['data'][0]['value']), "label": d['data'][0]['value_classification']}
    except:​​​​​​​​​​​​​​​​
