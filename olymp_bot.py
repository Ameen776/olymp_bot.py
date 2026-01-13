import os
import requests
import threading
import numpy as np
from flask import Flask
import time
import hmac
import hashlib

# =======================
# Environment Variables
# =======================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY")
PORT = int(os.environ.get("PORT", 10000))

# =======================
# Flask Web Server (Render يحتاج Port)
# =======================
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is running ✅"
def run_web():
    app.run(host="0.0.0.0", port=PORT)

# =======================
# الأزواج
# =======================
PAIRS = [
    "Bitcoin OTC", "Ethereum OTC", "Litecoin OTC",
    "Ripple OTC", "Solana OTC", "NZD/USD OTC", "USD/CHF OTC",
    "AUD/CAD OTC", "AUD/CHF OTC", "AUD/JPY OTC", "AUD/NZD OTC",
    "CAD/CHF OTC", "CAD/JPY OTC", "CHF/JPY OTC",
    "EUR/AUD OTC", "EUR/CAD OTC", "EUR/CHF OTC", "EUR/GBP OTC"
]

PAIR_MAP = {
    "Bitcoin OTC": "BTCUSDT",
    "Ethereum OTC": "ETHUSDT",
    "Litecoin OTC": "LTCUSDT",
    "Ripple OTC": "XRPUSDT",
    "Solana OTC": "SOLUSDT",
    "NZD/USD OTC": "NZDUSDT",
    "USD/CHF OTC": "USDCHF",
    "AUD/CAD OTC": "AUDCAD",
    "AUD/CHF OTC": "AUDCHF",
    "AUD/JPY OTC": "AUDJPY",
    "AUD/NZD OTC": "AUDNZD",
    "CAD/CHF OTC": "CADCHF",
    "CAD/JPY OTC": "CADJPY",
    "CHF/JPY OTC": "CHFJPY",
    "EUR/AUD OTC": "EURAUD",
    "EUR/CAD OTC": "EURCAD",
    "EUR/CHF OTC": "EURCHF",
    "EUR/GBP OTC": "EURGBP"
}

selected_pair = None
running = False

# =======================
# Telegram helpers
# =======================
def send_message(text, keyboard=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    if keyboard:
        payload["reply_markup"] = keyboard
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def send_pairs_buttons():
    keyboard = []
    row = []
    for i, pair in enumerate(PAIRS, 1):
        row.append({"text": pair, "callback_data": pair})
        if i % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    send_message("📊 اختر الزوج (لوحة مفاتيح):", {"inline_keyboard": keyboard})

# =======================
# RSI Calculation
# =======================
def rsi(closes, period=14):
    deltas = np.diff(closes)
    gain = np.maximum(deltas, 0)
    loss = np.abs(np.minimum(deltas, 0))
    avg_gain = np.mean(gain[-period:])
    avg_loss = np.mean(loss[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# =======================
# Binance API call مع مفاتيح
# =======================
def get_klines(symbol, interval="1m", limit=50):
    url = "https://api.binance.com/api/v3/klines"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = requests.get(url, headers=headers, params=params, timeout=5)
    return resp.json()

# =======================
# Signal Loop سريع جدًا
# =======================
def signal_loop():
    global running
    last_signal = None
    while running:
        try:
            symbol = PAIR_MAP[selected_pair]
            klines = get_klines(symbol)
            closes = np.array([float(k[4]) for k in klines])
            r = rsi(closes)

            # إشارات BUY / SELL
            if r < 30 and last_signal != "BUY":
                send_message(f"📈 BUY\n{selected_pair}\nRSI: {round(r,2)}")
                last_signal = "BUY"
            elif r > 70 and last_signal != "SELL":
                send_message(f"📉 SELL\n{selected_pair}\nRSI: {round(r,2)}")
                last_signal = "SELL"

        except Exception as e:
            print("Signal error:", e)

        # 🔹 سريع: تحديث كل 3 ثواني
        time.sleep(3)

# =======================
# Telegram Listener سريع
# =======================
def listen_updates():
    global selected_pair, running
    offset = 0
    send_pairs_buttons()
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 1},
                timeout=5
            ).json()
            for update in r.get("result", []):
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    selected_pair = update["callback_query"]["data"]
                    running = True
                    send_message(f"✅ تم اختيار:\n{selected_pair}")
                    threading.Thread(target=signal_loop, daemon=True).start()
        except Exception as e:
            print("Update error:", e)
        time.sleep(0.3)

# =======================
# Start everything
# =======================
threading.Thread(target=listen_updates, daemon=True).start()
run_web()
