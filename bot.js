// ========== البوت البديل - لا يحتاج اتصالات خارجية ==========
const axios = require('axios');

// ========== المفاتيح من Render ==========
const TELEGRAM_TOKEN = process.env.TELEGRAM_TOKEN || '';
const CHAT_ID = process.env.CHAT_ID || '';

// إعدادات البوت
let botActive = true;
let signalsSent = 0;

// ========== دوال Telegram ==========
async function sendTelegram(msg) {
    if (!TELEGRAM_TOKEN || !CHAT_ID) {
        console.log('⚠️ مفاتيح Telegram مفقودة');
        return false;
    }

    try {
        const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;
        const data = {
            chat_id: CHAT_ID,
            text: msg,
            parse_mode: 'HTML'
        };

        const response = await axios.post(url, data, { timeout: 10000 });
        return response.status === 200;
    } catch (error) {
        console.log('❌ خطأ في Telegram:', error.message);
        return false;
    }
}

// ========== محاكاة بيانات السوق ==========
function generateMarketData() {
    const pairs = ['BTCOTC', 'XRPOTC', 'SOLOTC', 'AUDCADOTC'];
    const pair = pairs[Math.floor(Math.random() * pairs.length)];
    
    // توليد سعر عشوائي واقعي
    const basePrice = {
        'BTCOTC': 42000 + Math.random() * 2000,
        'XRPOTC': 0.5 + Math.random() * 0.2,
        'SOLOTC': 100 + Math.random() * 50,
        'AUDCADOTC': 0.88 + Math.random() * 0.04
    }[pair];
    
    const currentPrice = basePrice + (Math.random() - 0.5) * basePrice * 0.01;
    const change24h = (Math.random() - 0.5) * 4; // -2% إلى +2%
    
    // تحديد الإشارة بناء على التغير
    let signalType = 'NEUTRAL';
    let signalStrength = 'LOW';
    
    if (change24h > 1.5) {
        signalType = 'BUY';
        signalStrength = 'STRONG';
    } else if (change24h > 0.5) {
        signalType = 'BUY';
        signalStrength = 'MODERATE';
    } else if (change24h < -1.5) {
        signalType = 'SELL';
        signalStrength = 'STRONG';
    } else if (change24h < -0.5) {
        signalType = 'SELL';
        signalStrength = 'MODERATE';
    }
    
    return {
        pair: pair,
        symbol: pair.replace('OTC', ''),
        price: currentPrice,
        change24h: change24h,
        signalType: signalType,
        signalStrength: signalStrength,
        volume: 1000000 + Math.random() * 5000000,
        timestamp: new Date().toISOString()
    };
}

// ========== إنشاء إشارة واقعية ==========
function createRealisticSignal(marketData) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ar-SA');
    
    const emoji = marketData.signalType === 'BUY' ? '🟢' : 
                 marketData.signalType === 'SELL' ? '🔴' : '⚪';
    
    const signalName = marketData.signalType === 'BUY' ? 'شراء' : 
                      marketData.signalType === 'SELL' ? 'بيع' : 'مراقبة';
    
    let msg = `
${emoji} <b>إشارة ${signalName} - ${marketData.pair}</b>
━━━━━━━━━━━━━━━━━━━━
<b>⏰ الوقت:</b> ${timeStr}
<b>📊 الزوج:</b> ${marketData.pair}
<b>💰 الرمز:</b> ${marketData.symbol}
<b>🎯 القوة:</b> ${marketData.signalStrength === 'STRONG' ? 'قوية ⚡' : 'متوسطة 📊'}
━━━━━━━━━━━━━━━━━━━━
<b>💵 السعر الحالي:</b> $${marketData.price.toFixed(4)}
<b>🔄 التغير 24h:</b> <code>${marketData.change24h >= 0 ? '+' : ''}${marketData.change24h.toFixed(2)}%</code>
<b>📊 الحجم المقدر:</b> $${marketData.volume.toLocaleString()}
━━━━━━━━━━━━━━━━━━━━
`;
    
    if (marketData.signalType !== 'NEUTRAL') {
        msg += `<b>🎯 التوصية:</b>\n`;
        
        if (marketData.signalType === 'BUY') {
            msg += `• فتح صفقة <b>شراء</b> فوراً\n`;
            msg += `• الهدف: $${(marketData.price * 1.02).toFixed(4)}\n`;
            msg += `• وقف الخسارة: $${(marketData.price * 0.98).toFixed(4)}\n`;
            msg += `• المدة المقترحة: 5-15 دقيقة\n`;
        } else {
            msg += `• فتح صفقة <b>بيع</b> فوراً\n`;
            msg += `• الهدف: $${(marketData.price * 0.98).toFixed(4)}\n`;
            msg += `• وقف الخسارة: $${(marketData.price * 1.02).toFixed(4)}\n`;
            msg += `• المدة المقترحة: 5-15 دقيقة\n`;
        }
        
        msg += `\n<b>📈 التحليل:</b>\n`;
        
        if (marketData.signalStrength === 'STRONG') {
            msg += `• حركة سعرية قوية\n`;
            msg += `• زخم واضح في السوق\n`;
            msg += `• حجم تداول مرتفع\n`;
        } else {
            msg += `• حركة سعرية معتدلة\n`;
            msg += `• فرصة تداول جيدة\n`;
            msg += `• مخاطر متوسطة\n`;
        }
    } else {
        msg += `<b>📭 لا توجد إشارات قوية حالياً</b>\n`;
        msg += `• السوق جانبي\n`;
        msg += `• الانتظار لفرص أفضل\n`;
    }
    
    msg += `
━━━━━━━━━━━━━━━━━━━━
<b>📊 نظام البوت:</b>
• الإشارة: ${signalsSent + 1}
• الحالة: ${botActive ? '🟢 نشط' : '🔴 متوقف'}
• النمط: محاكاة واقعية
━━━━━━━━━━━━━━━━━━━━
<i>⚠️ هذا البوت للتجربة والتعلم فقط</i>
<i>💰 لا تستثمر أموال حقيقية بناء على هذه الإشارات</i>
`;
    
    return msg;
}

// ========== جلب بيانات حقيقية من موقع مجاني ==========
async function getRealData() {
    try {
        // استخدام موقع لا يحظر Render
        const url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true";
        
        const response = await axios.get(url, {
            timeout: 10000,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
        });
        
        if (response.data && response.data.bitcoin) {
            return {
                pair: 'BTCOTC',
                symbol: 'BTC',
                price: response.data.bitcoin.usd,
                change24h: response.data.bitcoin.usd_24h_change,
                isReal: true,
                source: 'CoinGecko'
            };
        }
    } catch (error) {
        console.log('⚠️ CoinGecko غير متاح، استخدام بيانات وهمية');
    }
    
    // إذا فشل الاتصال، استخدم بيانات واقعية وهمية
    return generateMarketData();
}

// ========== المراقبة الرئيسية ==========
async function monitorMarket() {
    console.log('🚀 بدأ البوت - نظام محاكاة واقعي');
    
    // إرسال رسالة البدء
    const startMsg = `
🤖 <b>بوت إشارات Olymp Trade يعمل الآن!</b>

🎯 <b>مميزات البوت:</b>
• إشارات واقعية للتداول
• تحليل فني مبسط
• توصيات شراء/بيع
• إدارة مخاطر

⚡ <b>أنواع الإشارات:</b>
• 🟢 إشارة شراء قوية
• 🟡 إشارة شراء متوسطة
• 🔴 إشارة بيع قوية
• 🟠 إشارة بيع متوسطة

📊 <b>الأزواج المتاحة:</b>
• BTCOTC - Bitcoin
• XRPOTC - Ripple
• SOLOTC - Solana
• AUDCADOTC - AUD/CAD

⏰ <b>معدل الإشارات:</b> كل 10-60 ثانية

<i>🔔 جاري بدء المراقبة وإرسال الإشارات...</i>
`;
    
    await sendTelegram(startMsg);
    
    let intervalCounter = 0;
    
    while (true) {
        try {
            if (!botActive) {
                console.log('⏸️ البوت متوقف مؤقتاً');
                await sleep(10000);
                continue;
            }
            
            intervalCounter++;
            
            // تحديد الفاصل الزمني للإشارة التالية
            let nextInterval;
            if (intervalCounter % 4 === 0) {
                nextInterval = 15000; // 15 ثانية
            } else if (intervalCounter % 3 === 0) {
                nextInterval = 30000; // 30 ثانية
            } else if (intervalCounter % 2 === 0) {
                nextInterval = 45000; // 45 ثانية
            } else {
                nextInterval = 60000; // 60 ثانية
            }
            
            console.log(`⏱️ الفاصل القادم: ${nextInterval/1000} ثانية...`);
            
            // انتظار الفاصل
            await sleep(nextInterval);
            
            // محاولة جلب بيانات حقيقية
            let marketData;
            try {
                marketData = await getRealData();
            } catch (e) {
                marketData = generateMarketData();
            }
            
            // زيادة فرص الإشارات القوية كل فترة
            if (Math.random() > 0.3) { // 70% فرصة لإشارة
                // تعديل البيانات لجعلها أكثر واقعية
                if (marketData.isReal) {
                    // إذا كانت بيانات حقيقية، أضف تحليلاً
                    marketData.signalType = marketData.change24h > 1 ? 'BUY' : 
                                          marketData.change24h < -1 ? 'SELL' : 'NEUTRAL';
                    marketData.signalStrength = Math.abs(marketData.change24h) > 2 ? 'STRONG' : 'MODERATE';
                }
                
                // إنشاء الإشارة
                const signalMessage = createRealisticSignal(marketData);
                
                // إرسال الإشارة
                const sent = await sendTelegram(signalMessage);
                
                if (sent) {
                    signalsSent++;
                    console.log(`✅ الإشارة ${signalsSent} أرسلت - ${marketData.pair} - ${marketData.signalType}`);
                }
            } else {
                console.log(`📭 لا إشارة هذه المرة (${intervalCounter})`);
            }
            
            // عرض حالة البوت في الكونسول
            console.log(`📊 البوت نشط - الإشارات المرسلة: ${signalsSent}`);
            
        } catch (error) {
            console.log('❌ خطأ في الدورة:', error.message);
            await sleep(5000);
        }
    }
}

// ========== دالة المساعدة ==========
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ========== بدء البوت ==========
async function startBot() {
    console.log('='.repeat(50));
    console.log('🤖 OLYMP TRADE SIGNAL BOT - REALISTIC SIMULATION');
    console.log('='.repeat(50));
    
    console.log('\n✅ البوت جاهز للتشغيل');
    console.log(`📱 Telegram: ${TELEGRAM_TOKEN ? '✅' : '❌'}`);
    console.log(`💬 Chat ID: ${CHAT_ID ? '✅' : '❌'}`);
    
    console.log('\n🚀 بدأ نظام المحاكاة الواقعية...');
    console.log('📊 الإشارات ترسل كل 15-60 ثانية');
    console.log('🎯 نظام عشوائي ذكي للإشارات');
    
    // بدء المراقبة
    monitorMarket().catch(error => {
        console.error('❌ خطأ فادح:', error);
    });
    
    // تحديث الحالة كل دقيقة
    setInterval(() => {
        const now = new Date();
        console.log(`⏰ ${now.toLocaleTimeString('ar-SA')} | الإشارات: ${signalsSent} | الحالة: ${botActive ? 'نشط' : 'متوقف'}`);
    }, 60000);
}

// ========== تشغيل البوت ==========
startBot();
