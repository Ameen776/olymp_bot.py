import os
import time
import requests
import threading
import numpy as np
from flask import Flask

# =======================
# Environment Variables
# =======================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))  # مهم لــ Render

# =======================
# Web Server (عشان Render)
# =======================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running ✅"

def run_web():
    app.run(host="0.0.0.0", port=PORT)

# =======================
# أزواج Olymp Trade
# =======================
PAIRS = {
    "Bitcoin OTC": "BTCUSDT",
    "Ethereum OTC": "ETHUSDT",
    "Litecoin OTC": "LTCUSDT",
    "Ripple OTC": "XRPUSDT",
    "Solana OTC": "SOLUSDT",
    "EUR/GBP OTC": "EURGBP",
    "EUR/CHF OTC": "EURCHF",
    "AUD/JPY OTC": "AUDJPY",
    "USD/CHF OTC": "USDCHF",
    "CAD/JPY OTC": "CADJPY"
}

selected_pair = None
running = False

# =======================
# Telegram
# =======================
def send_message(text, keyboard=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "reply_markup": keyboard
    }
    requests.post(url, json=payload)

def send_pairs_buttons():
    keyboard = {
        "inline_keyboard": [
            [{"text": pair, "callback_data": pair}]
            for pair in PAIRS.keys()
        ]
    }
    send_message("📊 اختر الزوج:", keyboard)

# =======================
# Market Data
# =======================
def get_klines(symbol, interval="1m", limit=50):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    return requests.get(url, params=params).json()

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
# Signal Loop
# =======================
def signal_loop():
    global running
    while running:
        try:
            symbol = PAIRS[selected_pair]
            klines = get_klines(symbol)
            closes = np.array([float(k[4]) for k in klines])
            r = rsi(closes)

            if r < 30:
                send_message(f"📈 BUY\n{selected_pair}\nRSI: {round(r,2)}")
            elif r > 70:
                send_message(f"📉 SELL\n{selected_pair}\nRSI: {round(r,2)}")

        except Exception as e:
            print("Error:", e)

        time.sleep(60)

# =======================
# Telegram Listener
# =======================
def listen_updates():
    global selected_pair, running
    offset = 0

    send_pairs_buttons()

    while True:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        r = requests.get(url, params={"offset": offset}).json()

        for update in r.get("result", []):
            offset = update["update_id"] + 1

            if "callback_query" in update:
                selected_pair = update["callback_query"]["data"]
                running = True
                send_message(f"✅ تم اختيار {selected_pair}")
                threading.Thread(target=signal_loop, daemon=True).start()

        time.sleep(2)

# =======================
# Start Everything
# =======================
threading.Thread(target=listen_updates, daemon=True).start()
run_web()
