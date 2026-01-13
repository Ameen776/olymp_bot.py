import os, json, time, threading
import numpy as np
import requests
from websocket import WebSocketApp
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ========= ENV =========
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

# نستخدم Binance كمؤشر حركة فقط
BINANCE_SYMBOL = "BTCUSDT"  # مرجع الحركة لــ Bitcoin OTC

# ========= STATE =========
state = {
    "duration": None,     # 15/30/45/60
    "prices": [],         # آخر ticks
    "last_signal": None,
    "ws": None,
    "last_sent_ts": 0
}

# ========= HELPERS =========
def send_msg(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text},
            timeout=5
        )
    except:
        pass

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    deltas = np.diff(np.array(prices))
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = gains[-period:].mean()
    avg_loss = losses[-period:].mean()
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def momentum(prices, lookback=5):
    if len(prices) < lookback + 1:
        return None
    return prices[-1] - prices[-1 - lookback]

# ========= BINANCE WS =========
def on_message(ws, message):
    data = json.loads(message)
    price = float(data["p"])
    state["prices"].append(price)
    if len(state["prices"]) > 60:
        state["prices"] = state["prices"][-60:]
    check_signal()

def on_error(ws, err):
    print("WS ERROR:", err)

def start_ws():
    if state["ws"]:
        try: state["ws"].close()
        except: pass
    url = f"wss://stream.binance.com:9443/ws/{BINANCE_SYMBOL.lower()}@trade"
    ws = WebSocketApp(url, on_message=on_message, on_error=on_error)
    state["ws"] = ws
    threading.Thread(target=ws.run_forever, daemon=True).start()

# ========= SIGNAL LOGIC =========
def check_signal():
    if state["duration"] is None:
        return

    prices = state["prices"]
    r = rsi(prices)
    m = momentum(prices)

    if r is None or m is None:
        return

    # فلترة سبام: لا نرسل إشارتين خلال 10 ثواني
    now = time.time()
    if now - state["last_sent_ts"] < 10:
        return

    # شروط قوية مناسبة للـ OTC السريع
    if r < 30 and m > 0 and state["last_signal"] != "BUY":
        send_msg(
            f"🟢 BUY\n"
            f"Olymp Trade: Bitcoin OTC\n"
            f"المدة: {state['duration']} ثانية\n"
            f"RSI: {r:.2f} | Momentum: {m:.2f}\n"
            f"⏱ ادخل فورًا"
        )
        state["last_signal"] = "BUY"
        state["last_sent_ts"] = now

    elif r > 70 and m < 0 and state["last_signal"] != "SELL":
        send_msg(
            f"🔴 SELL\n"
            f"Olymp Trade: Bitcoin OTC\n"
            f"المدة: {state['duration']} ثانية\n"
            f"RSI: {r:.2f} | Momentum: {m:.2f}\n"
            f"⏱ ادخل فورًا"
        )
        state["last_signal"] = "SELL"
        state["last_sent_ts"] = now

# ========= TELEGRAM =========
def start(update: Update, context: CallbackContext):
    kb = [["15 ثانية", "30 ثانية"], ["45 ثانية", "60 ثانية"]]
    update.message.reply_text(
        "اختر مدة الصفقة لــ Bitcoin OTC:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    # نبدأ WebSocket فورًا
    start_ws()

def handle_text(update: Update, context: CallbackContext):
    text = update.message.text
    if "ثانية" in text:
        state["duration"] = int(text.split()[0])
        state["last_signal"] = None
        update.message.reply_text(
            f"✅ تم الضبط\n"
            f"Olymp Trade: Bitcoin OTC\n"
            f"المدة: {state['duration']} ثانية\n"
            f"📡 مراقبة لحظية بدأت"
        )

# ========= MAIN =========
updater = Updater(BOT_TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
updater.start_polling()
updater.idle()
