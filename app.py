import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

# === আপনার টেলিগ্রাম তথ্য এখানে দিন ===
TELEGRAM_TOKEN = "8574965944:AAEMpjfg0Mly532o4rTCF9EqQy3lkFFM2OU"
CHAT_ID = "8323959004"

# Binance Futures API সেটআপ (পাবলিক ডেটার জন্য API Key লাগে না)
exchange = ccxt.binance({'options': {'defaultType': 'future'}})

app = Flask(__name__)

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram error:", e)

def check_rsi_conditions():
    print("Market scan started...")
    try:
        # মার্কেট ডেটা লোড করা
        markets = exchange.load_markets()
        
        # শুধুমাত্র USDT পেয়ার (যেমন: ETH/USDT, SOL/USDT) ফিল্টার করা
        symbols = [s for s in markets if s.endswith('/USDT')]
        
        for symbol in symbols:
            try:
                # 15 মিনিটের টাইমফ্রেমের ডেটা নিচ্ছি (আপনি চাইলে '1h' বা '5m' দিতে পারেন)
                bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
                if not bars:
                    continue
                    
                df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                
                # RSI ক্যালকুলেশন
                df['rsi_4'] = ta.rsi(df['close'], length=4)
                df['rsi_14'] = ta.rsi(df['close'], length=14)
                df['rsi_24'] = ta.rsi(df['close'], length=24)
                
                latest = df.iloc[-1]
                
                # যদি কোনো ভ্যালু ফাঁকা থাকে, তবে স্কিপ করবে
                if pd.isna(latest['rsi_4']) or pd.isna(latest['rsi_14']) or pd.isna(latest['rsi_24']):
                    continue
                
                # কন্ডিশন চেক: তিনটি RSI ই 80 এর সমান বা বেশি হতে হবে
                if latest['rsi_4'] >= 80 and latest['rsi_14'] >= 80 and latest['rsi_24'] >= 80:
                    msg = (
                        f"🚨 <b>RSI OVERBOUGHT ALERT</b> 🚨\n\n"
                        f"<b>Coin:</b> {symbol}\n"
                        f"<b>Timeframe:</b> 15m\n"
                        f"<b>RSI (4):</b> {latest['rsi_4']:.2f}\n"
                        f"<b>RSI (14):</b> {latest['rsi_14']:.2f}\n"
                        f"<b>RSI (24):</b> {latest['rsi_24']:.2f}\n\n"
                        f"⚠️ <i>Check chart before taking a trade.</i>"
                    )
                    send_telegram_message(msg)
                    
            except Exception as e:
                pass
            
            # Binance এর Rate Limit এড়ানোর জন্য প্রতিটি কয়েন চেকের পর সামান্য বিরতি
            time.sleep(0.3) 
            
    except Exception as e:
        print(f"Main Error: {e}")
    print("Market scan finished.")

# === ওয়েব UI ডিজাইন (HTML & CSS) ===
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Binance RSI Bot</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background-color: #161b22; padding: 40px; border-radius: 15px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); text-align: center; border: 1px solid #30363d; width: 350px; }
        h2 { color: #58a6ff; margin-bottom: 5px; }
        p { color: #8b949e; font-size: 14px; margin-bottom: 25px; }
        .status { background-color: #238636; color: white; padding: 10px 20px; border-radius: 50px; font-weight: bold; display: inline-block; font-size: 16px; margin-bottom: 20px; }
        .details { text-align: left; background: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #30363d; }
        .details div { margin-bottom: 8px; font-size: 14px; }
        .highlight { color: #f0883e; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Crypto RSI Bot</h2>
        <p>Binance Futures Market Monitor</p>
        <div class="status">🟢 Bot is Running 24/7</div>
        <div class="details">
            <div><b>Target:</b> USDT Altcoins</div>
            <div><b>Condition:</b> RSI >= <span class="highlight">80</span></div>
            <div><b>Lengths:</b> 4, 14, 24</div>
            <div><b>Scan Interval:</b> Every 15 Mins</div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return HTML_PAGE

if __name__ == '__main__':
    # প্রতি ১৫ মিনিট পরপর মার্কেট স্ক্যান করার জন্য শিডিউলার
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_rsi_conditions, trigger="interval", minutes=15)
    scheduler.start()
    
    # সার্ভার রান করা
    app.run(host='0.0.0.0', port=8080)
