import os
import json
import numpy as np
import websocket
import threading
from telegram import Bot

# ================== Telegram ==================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ================== Settings ==================
SYMBOL = "btcusdt"        # مصدر السعر من Binance
INTERVAL = "30s"          # 30 ثانية (ممتاز لـ OTC)
RSI_PERIOD = 14

prices = []
last_signal = None        # لمنع تكرار نفس الإشارة

# ================== RSI ==================
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

# ================== WebSocket ==================
def on_message(ws, message):
    global last_signal

    data = json.loads(message)

    if "k" not in data:
        return

    candle = data["k"]

    # ننتظر إغلاق الشمعة
    if not candle["x"]:
        return

    close_price = float(candle["c"])
    prices.append(close_price)

    rsi = calculate_rsi(prices, RSI_PERIOD)
    if rsi is None:
        return

    # BUY
    if rsi <= 30 and last_signal != "BUY":
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=(
                "🟢 إشارة شراء (BUY)\n"
                "الأصل: Bitcoin OTC\n"
                "المصدر: Binance BTCUSDT\n"
                f"RSI: {rsi:.2f}\n"
                "الفريم: 30 ثانية\n"
                "📌 تنفيذ يدوي على Olymp Trade"
            )
        )
        last_signal = "BUY"

    # SELL
    elif rsi >= 70 and last_signal != "SELL":
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=(
                "🔴 إشارة بيع (SELL)\n"
                "الأصل: Bitcoin OTC\n"
                "المصدر: Binance BTCUSDT\n"
                f"RSI: {rsi:.2f}\n"
                "الفريم: 30 ثانية\n"
                "📌 تنفيذ يدوي على Olymp Trade"
            )
        )
        last_signal = "SELL"

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws):
    print("WebSocket closed")

def on_open(ws):
    print("WebSocket connected")

def start_socket():
    url = f"wss://stream.binance.com:9443/ws/{SYMBOL}@kline_{INTERVAL}"
    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open
    ws.run_forever()

# ================== Start ==================
if __name__ == "__main__":
    print("🚀 Bot started – Binance → Telegram → Olymp Trade")
    threading.Thread(target=start_socket).start()
