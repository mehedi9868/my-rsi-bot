import ccxt
import pandas as pd
import requests
import time
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

# === আপনার তথ্য এখানে দিন ===
TELEGRAM_TOKEN = "8574965944:AAEMpjfg0Mly532o4rTCF9EqQy3lkFFM2OU"
CHAT_ID = "8323959004"

exchange = ccxt.binance({'options': {'defaultType': 'future'}})
app = Flask(__name__)

# RSI বের করার সহজ ফাংশন (কোনো লাইব্রেরি লাগবে না)
def calculate_rsi(prices, period):
    deltas = pd.Series(prices).diff()
    gain = (deltas.where(deltas > 0, 0)).rolling(window=period).mean()
    loss = (-deltas.where(deltas < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs)).iloc[-1]

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try: requests.post(url, data=payload)
    except: print("Telegram error")

def check_rsi_conditions():
    print("Scanning...")
    try:
        markets = exchange.load_markets()
        symbols = [s for s in markets if s.endswith('/USDT')]
        for symbol in symbols:
            try:
                bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
                if not bars: continue
                closes = [b[4] for b in bars]
                
                rsi4 = calculate_rsi(closes, 4)
                rsi14 = calculate_rsi(closes, 14)
                rsi24 = calculate_rsi(closes, 24)
                
                if rsi4 >= 80 and rsi14 >= 80 and rsi24 >= 80:
                    msg = f"🚨 <b>RSI ALERT</b> 🚨\n\n<b>{symbol}</b>\nRSI(4): {rsi4:.2f}\nRSI(14): {rsi14:.2f}\nRSI(24): {rsi24:.2f}"
                    send_telegram_message(msg)
                time.sleep(0.2)
            except: continue
    except: print("Market Error")

@app.route('/')
def home():
    return "<h1>Bot is Running!</h1>"

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_rsi_conditions, trigger="interval", minutes=15)
    scheduler.start()
    app.run(host='0.0.0.0', port=8080)
