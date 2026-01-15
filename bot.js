// ========== البوت النهائي - بسيط ونظيف ==========

// المفاتيح من Render
const TOKEN = process.env.TOKEN;
const CHAT_ID = process.env.CHAT_ID;

// حالة البوت
let bot = {
    active: false,      // البوت متوقف في البداية
    pair: null,         // لا زوج محدد
    signals: 0          // عداد الإشارات
};

// ========== إرسال رسالة ==========
async function send(msg) {
    if (!TOKEN || !CHAT_ID) {
        console.log("❌ أضف TOKEN و CHAT_ID في Render");
        return false;
    }

    try {
        const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
        const res = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                chat_id: CHAT_ID,
                text: msg,
                parse_mode: 'HTML'
            })
        });
        
        return res.ok;
    } catch (e) {
        console.log("⚠️ خطأ:", e.message);
        return false;
    }
}

// ========== لوحة الأوامر البسيطة ==========
async function sendMainMenu() {
    const keyboard = {
        keyboard: [
            ["🚀 BTC", "🌀 XRP"],
            ["⚡ SOL", "💵 AUD/CAD"],
            ["▶️ تشغيل البوت", "⏸️ إيقاف البوت"],
            ["📊 حالة البوت"]
        ],
        resize_keyboard: true,
        one_time_keyboard: false
    };

    const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
    await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            chat_id: CHAT_ID,
            text: "🎯 <b>اختر الزوج ثم شغل البوت</b>",
            parse_mode: 'HTML',
            reply_markup: keyboard
        })
    });
}

// ========== معالجة الأوامر ==========
async function handleCommand(cmd) {
    console.log("📝 أمر:", cmd);
    
    // اختيار الزوج
    if (cmd === "🚀 BTC") {
        bot.pair = "BTC";
        await send("✅ <b>تم اختيار Bitcoin</b>\nالآن اضغط '▶️ تشغيل البوت'");
    }
    else if (cmd === "🌀 XRP") {
        bot.pair = "XRP";
        await send("✅ <b>تم اختيار Ripple</b>\nالآن اضغط '▶️ تشغيل البوت'");
    }
    else if (cmd === "⚡ SOL") {
        bot.pair = "SOL";
        await send("✅ <b>تم اختيار Solana</b>\nالآن اضغط '▶️ تشغيل البوت'");
    }
    else if (cmd === "💵 AUD/CAD") {
        bot.pair = "AUDCAD";
        await send("✅ <b>تم اختيار AUD/CAD</b>\nالآن اضغط '▶️ تشغيل البوت'");
    }
    
    // تشغيل البوت
    else if (cmd === "▶️ تشغيل البوت") {
        if (!bot.pair) {
            await send("⚠️ <b>اختر زوج أولاً</b>\nاضغط على BTC, XRP, SOL أو AUD/CAD");
            return;
        }
        
        bot.active = true;
        await send(`▶️ <b>تم تشغيل البوت</b>\n📊 يراقب: ${bot.pair}\n⏱️ الإشارات كل 30-60 ثانية`);
    }
    
    // إيقاف البوت
    else if (cmd === "⏸️ إيقاف البوت") {
        bot.active = false;
        await send("⏸️ <b>تم إيقاف البوت</b>");
    }
    
    // حالة البوت
    else if (cmd === "📊 حالة البوت") {
        const status = bot.active ? "▶️ مشغل" : "⏸️ متوقف";
        const pair = bot.pair ? bot.pair : "لم يتم الاختيار";
        
        await send(`
📊 <b>حالة البوت</b>
──────────────
<b>🔄 الحالة:</b> ${status}
<b>📊 الزوج:</b> ${pair}
<b>📈 الإشارات:</b> ${bot.signals}
──────────────
`);
    }
}

// ========== توليد إشارة قصيرة ==========
async function sendSignal() {
    if (!bot.active || !bot.pair) return;
    
    bot.signals++;
    
    // إشارة شراء أو بيع عشوائية
    const isBuy = Math.random() > 0.5;
    const duration = [30, 45, 60, 90][Math.floor(Math.random() * 4)];
    const time = new Date().toLocaleTimeString('ar-SA').slice(0, 5);
    
    // رسالة مختصرة جداً
    const signal = isBuy 
        ? `🟢 ${bot.pair}\nشراء ${duration}ث\n${time}`
        : `🔴 ${bot.pair}\nبيع ${duration}ث\n${time}`;
    
    await send(signal);
    console.log(`✅ ${bot.signals}: ${isBuy ? 'شراء' : 'بيع'} ${bot.pair} ${duration}ث`);
}

// ========== التحقق من الأوامر ==========
async function checkCommands() {
    try {
        const url = `https://api.telegram.org/bot${TOKEN}/getUpdates`;
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.ok && data.result.length > 0) {
            for (const update of data.result) {
                if (update.message && update.message.text) {
                    await handleCommand(update.message.text);
                }
            }
        }
    } catch (e) {
        // تجاهل الخطأ
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
    
    // إرسال لوحة الأوامر
    await sendMainMenu();
    console.log("✅ تم إرسال لوحة الأوامر");
    
    // الحلقة الرئيسية
    let lastSignal = 0;
    
    while (true) {
        try {
            // 1. تحقق من الأوامر
            await checkCommands();
            
            // 2. إذا البوت شغال وزوج محدد، أرسل إشارة
            if (bot.active && bot.pair) {
                const now = Date.now();
                const interval = 30000 + Math.random() * 30000; // 30-60 ثانية
                
                if (now - lastSignal >= interval) {
                    await sendSignal();
                    lastSignal = now;
                }
            }
            
            // 3. انتظر 1 ثانية
            await new Promise(r => setTimeout(r, 1000));
            
        } catch (error) {
            console.log("⚠️ خطأ:", error.message);
            await new Promise(r => setTimeout(r, 5000));
        }
    }
}

// ========== التشغيل ==========
start();
