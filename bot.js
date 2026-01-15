// ========== البوت البسيط مع تحكم كامل ==========

// المفاتيح من Render
const TOKEN = process.env.TOKEN;
const CHAT_ID = process.env.CHAT_ID;

// حالة البوت
let bot = {
    active: false,           // البوت متوقف في البداية
    pair: "BTCOTC",          // الزوج الافتراضي
    interval: 30000,         // 30 ثانية افتراضياً
    signals: 0              // عدد الإشارات
};

// الأزواج المتاحة
const PAIRS = {
    "BTCOTC": "₿ Bitcoin",
    "XRPOTC": "🌀 Ripple", 
    "SOLOTC": "⚡ Solana",
    "AUDCADOTC": "💵 AUD/CAD"
};

// ========== إرسال رسالة ==========
async function send(msg, keyboard = null) {
    if (!TOKEN || !CHAT_ID) {
        console.log("❌ أضف TOKEN و CHAT_ID في Render");
        return false;
    }

    try {
        const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
        const body = {
            chat_id: CHAT_ID,
            text: msg,
            parse_mode: 'HTML'
        };
        
        if (keyboard) body.reply_markup = keyboard;
        
        const res = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        
        return res.ok;
    } catch (e) {
        console.log("⚠️ خطأ:", e.message);
        return false;
    }
}

// ========== لوحة التحكم ==========
function getKeyboard() {
    return {
        inline_keyboard: [
            [
                { text: '₿ BTC', callback_data: 'BTCOTC' },
                { text: '🌀 XRP', callback_data: 'XRPOTC' },
                { text: '⚡ SOL', callback_data: 'SOLOTC' }
            ],
            [
                { text: '💵 AUD/CAD', callback_data: 'AUDCADOTC' }
            ],
            [
                { text: bot.active ? '⏸️ إيقاف' : '▶️ تشغيل', 
                  callback_data: bot.active ? 'stop' : 'start' }
            ],
            [
                { text: '⚙️ الإعدادات', callback_data: 'settings' }
            ]
        ]
    };
}

// ========== معالجة الأوامر ==========
async function handleCommand(cmd) {
    console.log("📝 أمر:", cmd);
    
    if (PAIRS[cmd]) {
        // تغيير الزوج
        bot.pair = cmd;
        await send(`✅ <b>تم اختيار ${PAIRS[cmd]}</b>\nالزوج النشط الآن: ${cmd}`, getKeyboard());
    }
    else if (cmd === 'start') {
        // تشغيل البوت
        bot.active = true;
        await send(`▶️ <b>تم تشغيل البوت</b>\n📊 يراقب: ${bot.pair}\n⏱️ كل: ${bot.interval/1000}ث`, getKeyboard());
    }
    else if (cmd === 'stop') {
        // إيقاف البوت
        bot.active = false;
        await send(`⏸️ <b>تم إيقاف البوت</b>`, getKeyboard());
    }
    else if (cmd === 'settings') {
        // عرض الإعدادات
        const settings = `
⚙️ <b>الإعدادات الحالية</b>
──────────────
<b>🔄 الحالة:</b> ${bot.active ? '▶️ تشغيل' : '⏸️ إيقاف'}
<b>📊 الزوج:</b> ${bot.pair} (${PAIRS[bot.pair]})
<b>⏱️ الفاصل:</b> ${bot.interval/1000} ثانية
<b>📈 الإشارات:</b> ${bot.signals}
──────────────
<i>انقر على الأزرار للتحكم</i>
`;
        await send(settings, getKeyboard());
    }
}

// ========== توليد إشارة قصيرة ==========
async function generateSignal() {
    if (!bot.active) return;
    
    bot.signals++;
    
    const actions = ["BUY", "SELL"];
    const action = actions[Math.floor(Math.random() * actions.length)];
    const duration = [30, 60, 120, 180][Math.floor(Math.random() * 4)];
    
    // رسالة قصيرة جداً
    const signal = `
${action === "BUY" ? "🟢" : "🔴"} <b>${bot.pair}</b>
${action === "BUY" ? "شراء" : "بيع"} | ⏱️${duration}ث
${new Date().toLocaleTimeString('ar-SA').slice(0,5)}
`;
    
    await send(signal, getKeyboard());
    console.log(`✅ إشارة ${bot.signals}: ${action} ${bot.pair} ${duration}ث`);
}

// ========== التحقق من الأوامر ==========
async function checkCommands() {
    try {
        const url = `https://api.telegram.org/bot${TOKEN}/getUpdates`;
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.ok && data.result.length > 0) {
            for (const update of data.result) {
                if (update.callback_query) {
                    await handleCommand(update.callback_query.data);
                }
            }
        }
    } catch (e) {
        console.log("⚠️ خطأ في الأوامر:", e.message);
    }
}

// ========== البداية ==========
async function start() {
    console.log("🚀 بدأ البوت...");
    console.log("TOKEN:", TOKEN ? "✅" : "❌");
    console.log("CHAT_ID:", CHAT_ID ? "✅" : "❌");
    
    if (!TOKEN || !CHAT_ID) {
        console.log("\n❌ أضف في Render:");
        console.log("TOKEN: توكن البوت");
        console.log("CHAT_ID: رقم المحادثة");
        return;
    }
    
    // رسالة البداية
    await send(`
🎯 <b>بوت التداول البسيط</b>

<b>📊 الزوج:</b> ${bot.pair}
<b>🔄 الحالة:</b> ${bot.active ? '▶️ تشغيل' : '⏸️ إيقاف'}

<i>استخدم الأزرار للتحكم 👇</i>
`, getKeyboard());
    
    console.log("✅ البوت جاهز. انتظر الأوامر...");
    
    // الحلقة الرئيسية
    while (true) {
        try {
            // 1. تحقق من الأوامر كل ثانية
            await checkCommands();
            
            // 2. إذا البوت شغال، أرسل إشارة كل فترة
            if (bot.active) {
                const now = Date.now();
                if (!bot.lastSignal || (now - bot.lastSignal) >= bot.interval) {
                    await generateSignal();
                    bot.lastSignal = now;
                }
            }
            
            // 3. انتظر ثانية قبل التكرار
            await new Promise(r => setTimeout(r, 1000));
            
        } catch (error) {
            console.log("⚠️ خطأ:", error.message);
            await new Promise(r => setTimeout(r, 5000));
        }
    }
}

// ========== التشغيل ==========
start();
