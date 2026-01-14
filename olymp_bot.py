import os
import time
import requests
import numpy as np
from telegram import Bot
from datetime import datetime

# ================= Telegram =================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TOKEN)

# ================= Settings =================
SYMBOL = "BTCUSDT"
INTERVAL_SECONDS = 30       # وقت الصفقة (30 ثانية)
RSI_PERIOD = 14
CHECK_DELAY = 30            # كل 30 ثانية

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

# ================= Get Price =================
def get_price():
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": SYMBOL}
    r = requests.get(url, params=params, timeout=10)
    return float(r.json()["price"])

# ================= Main Loop =================
def run_bot():
    global last_signal

    bot.send_message(
        chat_id=CHAT_ID,
        text="🚀 Bot Started\nالأصل: Bitcoin OTC\nالمصدر: Binance BTCUSDT\nالفريم: 30 ثانية"
    )

    while True:
        try:
            price = get_price()
            prices.append(price)

            rsi = calculate_rsi(prices, RSI_PERIOD)
            if rsi is None:
                time.sleep(CHECK_DELAY)
                continue

            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            # BUY
            if rsi <= 30 and last_signal != "BUY":
                bot.send_message(
                    chat_id=CHAT_ID,
                    text=(
                        "🟢 إشارة شراء (BUY)\n"
                        "الأصل: Bitcoin OTC\n"
                        "المصدر: Binance BTCUSDT\n"
                        f"السعر: {price}\n"
                        f"RSI: {rsi:.2f}\n"
                        f"الوقت: {now}\n"
                        "⏱ مدة الصفقة: 30 ثانية\n"
                        "📌 تنفيذ يدوي على Olymp Trade"
                    )
                )
                last_signal = "BUY"

            # SELL
            elif rsi >= 70 and last_signal != "SELL":
                bot.send_message(
                    chat_id=CHAT_ID,
                    text=(
                        "🔴 إشارة بيع (SELL)\n"
                        "الأصل: Bitcoin OTC\n"
                        "المصدر: Binance BTCUSDT\n"
                        f"السعر: {price}\n"
                        f"RSI: {rsi:.2f}\n"
                        f"الوقت: {now}\n"
                        "⏱ مدة الصفقة: 30 ثانية\n"
                        "📌 تنفيذ يدوي على Olymp Trade"
                    )
                )
                last_signal = "SELL"

        except Exception as e:
            print("Error:", e)

        time.sleep(CHECK_DELAY)

# ================= Start =================
if __name__ == "__main__":
    run_bot()
