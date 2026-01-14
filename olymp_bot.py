import os
import threading
import time
import requests
import numpy as np
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================== ENV ==================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

SYMBOL = "BTCUSDT"
INTERVAL = "1m"  # شمعة دقيقة
RSI_PERIOD = 14

# ================== FLASK SERVER (Render يحتاجه) ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================== BINANCE FUNCTIONS ==================
def get_klines(symbol=SYMBOL, interval=INTERVAL, limit=100):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, timeout=5)
    data = r.json()
    closes = [float(c[4]) for c in data]
    return closes

def calculate_rsi(prices, period=RSI_PERIOD):
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
import asyncio

async def signal_loop(app_telegram):
    last_signal = None
    while True:
        try:
            prices = get_klines()
            rsi = calculate_rsi(prices)

            if rsi <= 30 and last_signal != "BUY":
                msg = (
                    f"🟢 إشارة شراء (تشبع بيعي)\n"
                    f"زوج: BTCUSDT (Binance)\n"
                    f"RSI: {rsi:.2f}\n"
                    "⏱️ إطار زمني: 1 دقيقة\n"
                    "⚠️ افتح الصفقة يدويًا على Olymp Trade"
                )
                await app_telegram.bot.send_message(chat_id=CHAT_ID, text=msg)
                last_signal = "BUY"

            elif rsi >= 70 and last_signal != "SELL":
                msg = (
                    f"🔴 إشارة بيع (تشبع شرائي)\n"
                    f"زوج: BTCUSDT (Binance)\n"
                    f"RSI: {rsi:.2f}\n"
                    "⏱️ إطار زمني: 1 دقيقة\n"
                    "⚠️ افتح الصفقة يدويًا على Olymp Trade"
                )
                await app_telegram.bot.send_message(chat_id=CHAT_ID, text=msg)
                last_signal = "SELL"

        except Exception as e:
            print("Error:", e)

        await asyncio.sleep(5)  # يفحص كل 5 ثواني

# ================== TELEGRAM COMMAND ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ البوت شغال!\n"
        "📡 يراقب BTCUSDT مباشرة من Binance\n"
        "⏱️ إشارات بيع وشراء فورية"
    )

# ================== MAIN ==================
def main():
    app_telegram = ApplicationBuilder().token(TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    loop = asyncio.get_event_loop()
    loop.create_task(signal_loop(app_telegram))
    app_telegram.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    main()
