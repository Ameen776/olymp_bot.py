// ========== البوت النهائي - إشارات فقط بدون ضجيج ==========

const TOKEN = process.env.TOKEN;
const CHAT_ID = process.env.CHAT_ID;

// حالة البوت
let bot = {
    pair: null,          // الزوج المختار
    monitoring: false,   // هل المراقبة نشطة؟
    signals: 0           // عدد الإشارات المرسلة
};

// فترات الإشارات المطلوبة (بالثواني)
const SIGNAL_INTERVALS = [15, 30, 45, 60, 120, 180, 240, 300, 420, 600];

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

// ========== لوحة الأوامر الأساسية ==========
async function showMenu() {
    const keyboard = {
        keyboard: [
            ["🚀 BTC", "🌀 XRP"],
            ["⚡ SOL", "💵 AUD/CAD"],
            ["▶️ بدء الإشارات", "⏸️ إيقاف الإشارات"]
        ],
        resize_keyboard: true
    };
    
    const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
    await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            chat_id: CHAT_ID,
            text: "🎯 <b>اختر الزوج:</b>",
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
        await send("✅ <b>Bitcoin</b>");
    }
    else if (cmd === "🌀 XRP") {
        bot.pair = "XRP";
        await send("✅ <b>Ripple</b>");
    }
    else if (cmd === "⚡ SOL") {
        bot.pair = "SOL";
        await send("✅ <b>Solana</b>");
    }
    else if (cmd === "💵 AUD/CAD") {
        bot.pair = "AUDCAD";
        await send("✅ <b>AUD/CAD</b>");
    }
    
    // بدء الإشارات
    else if (cmd === "▶️ بدء الإشارات") {
        if (!bot.pair) {
            await send("⚠️ اختر زوج أولاً");
            return;
        }
        
        bot.monitoring = true;
        // لا ترسل رسالة "بدأت المراقبة" - فقط تبدأ الإشارات
        console.log("📡 بدأت الإشارات لـ", bot.pair);
    }
    
    // إيقاف الإشارات
    else if (cmd === "⏸️ إيقاف الإشارات") {
        bot.monitoring = false;
        await send("⏸️");
    }
}

// ========== توليد إشارة قصيرة ==========
async function generateSignal(interval) {
    if (!bot.monitoring || !bot.pair) return;
    
    bot.signals++;
    
    // تحويل الثواني إلى وقت مقروء
    let intervalText;
    if (interval < 60) {
        intervalText = `${interval}ث`;
    } else {
        intervalText = `${Math.floor(interval / 60)}د`;
    }
    
    // 50% شراء، 50% بيع
    const isBuy = Math.random() > 0.5;
    const time = new Date().toLocaleTimeString('ar-SA').slice(0, 5);
    
    // إشارة قصيرة جداً
    const signal = isBuy 
        ? `🟢 ${bot.pair}\nشراء ${intervalText}\n${time}`
        : `🔴 ${bot.pair}\nبيع ${intervalText}\n${time}`;
    
    await send(signal);
    console.log(`✅ ${bot.signals}: ${isBuy ? 'شراء' : 'بيع'} ${bot.pair} ${intervalText}`);
}

// ========== نظام توقيت الإشارات ==========
async function startSignalSystem() {
    let lastSignalTimes = {};
    
    while (true) {
        try {
            // التحقق من الأوامر
            await checkCommands();
            
            // إذا المراقبة نشطة
            if (bot.monitoring && bot.pair) {
                const now = Date.now();
                
                // فحص كل فترات الإشارات
                for (const interval of SIGNAL_INTERVALS) {
                    const lastTime = lastSignalTimes[interval] || 0;
                    
                    // إذا حان وقت هذه الفترة
                    if (now - lastTime >= interval * 1000) {
                        await generateSignal(interval);
                        lastSignalTimes[interval] = now;
                        
                        // تأخير بسيط بين الإشارات المتزامنة
                        await new Promise(r => setTimeout(r, 1000));
                    }
                }
            }
            
            // انتظار قصير
            await new Promise(r => setTimeout(r, 1000));
            
        } catch (error) {
            console.log("⚠️ خطأ:", error.message);
            await new Promise(r => setTimeout(r, 5000));
        }
    }
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
    
    // عرض القائمة فقط
    await showMenu();
    console.log("✅ جاهز للاستخدام");
    
    // بدء نظام الإشارات
    startSignalSystem();
}

// ========== التشغيل ==========
start();
