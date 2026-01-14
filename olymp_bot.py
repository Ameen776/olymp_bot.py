import os
import time
import threading
import requests
import numpy as np
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================== ENV VARIABLES ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

SYMBOL = "BTCUSDT"
INTERVAL = "1m"   # شمعة دقيقة (أسرع استجابة)
RSI_PERIOD = 14

# ================== FLASK (لـ Render) ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ================== BINANCE DATA ==================
def get_klines():
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "limit": 100
    }
    r = requests.get(url, timeout=5)
    data = r.json()
    closes = [float(c[4]) for c in data]
    return closes

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ================== SIGNAL LOOP ==================
async def signal_loop(app_telegram):
    last_signal = None

    while True:
        try:
            prices = get_klines()
            rsi = calculate_rsi(prices)

            if rsi <= 30 and last_signal != "BUY":
                msg = (
                    "🟢 إشارة شراء (تشبع بيعي)\n"
                    f"زوج: BTC (Binance)\n"
                    f"RSI: {rsi:.2f}\n"
                    "⏱️ الإطار: 1 دقيقة\n"
                    "⚠️ استخدمها يدويًا على Olymp Trade"
                )
                await app_telegram.bot.send_message(chat_id=CHAT_ID, text=msg)
                last_signal = "BUY"

            elif rsi >= 70 and last_signal != "SELL":
                msg = (
                    "🔴 إشارة بيع (تشبع شرائي)\n"
                    f"زوج: BTC (Binance)\n"
                    f"RSI: {rsi:.2f}\n"
                    "⏱️ الإطار: 1 دقيقة\n"
                    "⚠️ استخدمها يدويًا على Olymp Trade"
                )
                await app_telegram.bot.send_message(chat_id=CHAT_ID, text=msg)
                last_signal = "SELL"

        except Exception as e:
            print("Error:", e)

        await asyncio.sleep(5)  # فحص كل 5 ثواني (سريع جدًا)

# ================== TELEGRAM ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ البوت شغال\n"
        "📡 يراقب BTC من Binance\n"
        "⏱️ إشارات حقيقية لحظية"
    )

# ================== MAIN ==================
import asyncio

def main():
    app_telegram = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))

    loop = asyncio.get_event_loop()
    loop.create_task(signal_loop(app_telegram))

    app_telegram.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    main()
