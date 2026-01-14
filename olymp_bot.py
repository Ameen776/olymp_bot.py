import os
import time
import requests
import numpy as np
from telegram import Bot
from datetime import datetime
from flask import Flask
import threading

# ================= Flask (فتح بورت لـ Render) =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= Telegram =================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TOKEN)

# ================= Settings =================
SYMBOL = "BTCUSDT"
INTERVAL_SECONDS = 30
RSI_PERIOD = 14
CHECK_DELAY = 30

prices = []
last_signal = None

# ================= RSI =================
def calculate_rsi(data, period=14):
    if len(data) < period + 1:
        return None

    deltas = np.diff(data)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ================= Price =================
def get_price():
    r = requests.get(
        "https://api.binance.com/api/v3/ticker/price",
        params={"symbol": SYMBOL},
        timeout=10
    )
    return float(r.json()["price"])

# ================= Bot Loop =================
def run_bot():
    global last_signal

    bot.send_message(
        chat_id=CHAT_ID,
        text="🚀 Bot Started\nBitcoin OTC\nSource: Binance BTCUSDT\nTF: 30s"
    )

    while True:
        try:
            price = get_price()
            prices.append(price)

            rsi = calculate_rsi(prices)
            if rsi is None:
                time.sleep(CHECK_DELAY)
                continue

            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            if rsi <= 30 and last_signal != "BUY":
                bot.send_message(
                    chat_id=CHAT_ID,
                    text=(
                        "🟢 BUY SIGNAL\n"
                        "Bitcoin OTC\n"
                        f"Price: {price}\n"
                        f"RSI: {rsi:.2f}\n"
                        f"Time: {now}\n"
                        "⏱ 30 Seconds"
                    )
                )
                last_signal = "BUY"

            elif rsi >= 70 and last_signal != "SELL":
                bot.send_message(
                    chat_id=CHAT_ID,
                    text=(
                        "🔴 SELL SIGNAL\n"
                        "Bitcoin OTC\n"
                        f"Price: {price}\n"
                        f"RSI: {rsi:.2f}\n"
                        f"Time: {now}\n"
                        "⏱ 30 Seconds"
                    )
                )
                last_signal = "SELL"

        except Exception as e:
            print("Error:", e)

        time.sleep(CHECK_DELAY)

# ================= Start =================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    threading.Thread(target=run_bot).start()
