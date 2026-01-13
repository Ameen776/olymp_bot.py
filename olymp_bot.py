import os
import requests
import threading
import numpy as np
from flask import Flask, request
from websocket import create_connection
import json
import time

# =======================
# Environment Variables
# =======================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))

# =======================
# Flask Web Server
# =======================
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running ✅"

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    """Webhook مباشر لتلقي تحديثات Telegram فورًا"""
    update = request.get_json()
    if "callback_query" in update:
        pair = update["callback_query"]["data"]
        threading.Thread(target=start_signal_loop, args=(pair,), daemon=True).start()
        send_message(f"✅ تم اختيار:\n{pair}")
    return {"ok": True}

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
    "Bitcoin OTC": "btcusdt",
    "Ethereum OTC": "ethusdt",
    "Litecoin OTC": "ltcusdt",
    "Ripple OTC": "xrpusdt",
    "Solana OTC": "solusdt",
    "NZD/USD OTC": "nzdusdt",
    "USD/CHF OTC": "usdchf",
    "AUD/CAD OTC": "audcad",
    "AUD/CHF OTC": "audchf",
    "AUD/JPY OTC": "audjpy",
    "AUD/NZD OTC": "audnzd",
    "CAD/CHF OTC": "cadchf",
    "CAD/JPY OTC": "cadjpy",
    "CHF/JPY OTC": "chfjpy",
    "EUR/AUD OTC": "euraud",
    "EUR/CAD OTC": "eurcad",
    "EUR/CHF OTC": "eurchf",
    "EUR/GBP OTC": "eurgbp"
}

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
# RSI calculation
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
# Signal Loop سريع جدًا باستخدام WebSocket
# =======================
def start_signal_loop(selected_pair):
    last_signal = None
    symbol = PAIR_MAP[selected_pair]
    ws_url = f"wss://stream.binance.com:9443/ws/{symbol}@kline_1m"

    try:
        ws = create_connection(ws_url)
        while True:
            result = ws.recv()
            data = json.loads(result)
            kline = data['k']
            close_price = float(kline['c'])
            # نحتفظ آخر 50 سعر (يمكن تطويره لاحقًا ببيانات حقيقية)
            closes = [close_price]*50
            r = rsi(np.array(closes))

            if r < 30 and last_signal != "BUY":
                send_message(f"📈 BUY\n{selected_pair}\nRSI: {round(r,2)}\nافتح صفقة شراء الآن")
                last_signal = "BUY"
            elif r > 70 and last_signal != "SELL":
                send_message(f"📉 SELL\n{selected_pair}\nRSI: {round(r,2)}\nافتح صفقة بيع الآن")
                last_signal = "SELL"
    except Exception as e:
        print("WebSocket error:", e)
        time.sleep(1)

# =======================
# Start Web
# =======================
send_pairs_buttons()
run_web()
