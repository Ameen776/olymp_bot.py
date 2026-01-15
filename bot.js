// ========== البوت الذي تتحكم فيه أنت ==========

// المفاتيح من Render
const TOKEN = process.env.TOKEN;
const CHAT_ID = process.env.CHAT_ID;

// حالة البوت - كل شيء متوقف في البداية
let bot = {
    active: false,      // البوت متوقف
    pair: null,         // لا زوج محدد
    monitoring: false,  // لا مراقبة
    signals: 0
};

// ========== إرسال رسالة فقط ==========
async function send(msg) {
    if (!TOKEN || !CHAT_ID) return false;
    
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
        return false;
    }
}

// ========== عرض لوحة الأوامر ==========
async function showMenu() {
    if (!TOKEN || !CHAT_ID) return;
    
    const keyboard = {
        keyboard: [
            ["🚀 BTC", "🌀 XRP"],
            ["⚡ SOL", "💵 AUD/CAD"]
        ],
        resize_keyboard: true
    };
    
    const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
    await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            chat_id: CHAT_ID,
            text: "🎯 <b>اختر الزوج الذي تريد مراقبته:</b>",
            parse_mode: 'HTML',
            reply_markup: keyboard
        })
    });
}

// ========== عرض لوحة التحكم بعد اختيار الزوج ==========
async function showControlMenu() {
    const keyboard = {
        keyboard: [
            ["▶️ بدء المراقبة"],
            ["⏸️ إيقاف المراقبة"],
            ["📊 عرض حالة"],
            ["🔄 تغيير الزوج"]
        ],
        resize_keyboard: true
    };
    
    const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
    await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            chat_id: CHAT_ID,
            text: "🎮 <b>لوحة التحكم</b>\nاختر الإجراء الذي تريد:",
            parse_mode: 'HTML',
            reply_markup: keyboard
        })
    });
}

// ========== معالجة الأوامر ==========
async function handleCommand(cmd) {
    console.log("📝 أمر:", cmd);
    
    // 1. اختيار الزوج
    if (cmd === "🚀 BTC") {
        bot.pair = "BTC";
        await send("✅ <b>تم اختيار Bitcoin</b>\nالآن استخدم '▶️ بدء المراقبة' لبدء الإشارات");
        await showControlMenu();
    }
    else if (cmd === "🌀 XRP") {
        bot.pair = "XRP";
        await send("✅ <b>تم اختيار Ripple</b>\nالآن استخدم '▶️ بدء المراقبة' لبدء الإشارات");
        await showControlMenu();
    }
    else if (cmd === "⚡ SOL") {
        bot.pair = "SOL";
        await send("✅ <b>تم اختيار Solana</b>\nالآن استخدم '▶️ بدء المراقبة' لبدء الإشارات");
        await showControlMenu();
    }
    else if (cmd === "💵 AUD/CAD") {
        bot.pair = "AUDCAD";
        await send("✅ <b>تم اختيار AUD/CAD</b>\nالآن استخدم '▶️ بدء المراقبة' لبدء الإشارات");
        await showControlMenu();
    }
    
    // 2. بدء المراقبة
    else if (cmd === "▶️ بدء المراقبة") {
        if (!bot.pair) {
            await send("⚠️ <b>اختر زوج أولاً</b>");
            await showMenu();
            return;
        }
        
        bot.active = true;
        bot.monitoring = true;
        await send(`📡 <b>بدأت مراقبة ${bot.pair}</b>\nستصلك الإشارات الآن...`);
    }
    
    // 3. إيقاف المراقبة
    else if (cmd === "⏸️ إيقاف المراقبة") {
        bot.monitoring = false;
        await send("⏸️ <b>توقفت المراقبة</b>\nلا مزيد من الإشارات");
    }
    
    // 4. عرض الحالة
    else if (cmd === "📊 عرض حالة") {
        const status = bot.monitoring ? "▶️ جارية" : "⏸️ متوقفة";
        const pair = bot.pair || "لم يتم الاختيار";
        
        await send(`
📊 <b>حالة النظام</b>
──────────────
<b>📊 الزوج:</b> ${pair}
<b>🔄 المراقبة:</b> ${status}
<b>📈 الإشارات:</b> ${bot.signals}
──────────────
        `);
    }
    
    // 5. تغيير الزوج
    else if (cmd === "🔄 تغيير الزوج") {
        bot.monitoring = false;
        bot.pair = null;
        await send("🔄 <b>اختر زوج جديد:</b>");
        await showMenu();
    }
}

// ========== توليد إشارة قصيرة ==========
async function sendSignal() {
    if (!bot.monitoring || !bot.pair) return;
    
    bot.signals++;
    
    // إشارة شراء أو بيع
    const isBuy = Math.random() > 0.5;
    const duration = [30, 45, 60, 90, 120][Math.floor(Math.random() * 5)];
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
    console.log("🤖 البوت يبدأ...");
    
    if (!TOKEN || !CHAT_ID) {
        console.log("❌ أضف TOKEN و CHAT_ID في Render");
        return;
    }
    
    // فقط عرض قائمة الأزواج
    await showMenu();
    console.log("✅ تم عرض قائمة الأزواج");
    
    let lastSignalTime = 0;
    
    // الحلقة الرئيسية
    while (true) {
        try {
            // 1. تحقق من الأوامر فقط
            await checkCommands();
            
            // 2. إذا المراقبة مفعلة، أرسل إشارة كل 30-60 ثانية
            if (bot.monitoring && bot.pair) {
                const now = Date.now();
                const interval = 30000 + Math.random() * 30000; // 30-60 ثانية
                
                if (now - lastSignalTime >= interval) {
                    await sendSignal();
                    lastSignalTime = now;
                }
            }
            
            // 3. انتظار 1 ثانية
            await new Promise(r => setTimeout(r, 1000));
            
        } catch (error) {
            console.log("⚠️ خطأ:", error.message);
            await new Promise(r => setTimeout(r, 5000));
        }
    }
}

// ========== التشغيل ==========
start();
