// ========== البوت المعدل - بدون Binance API مباشر ==========
const axios = require('axios');

// ========== المفاتيح من Render ==========
const TELEGRAM_TOKEN = process.env.TELEGRAM_TOKEN || '';
const CHAT_ID = process.env.CHAT_ID || '';

// إعدادات البوت
let selectedPair = 'BTCUSDT';
let pairName = 'BTCOTC';
let botActive = true;
let lastPrice = 0;

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

        const response = await axios.post(url, data, { timeout: 5000 });
        return response.status === 200;
    } catch (error) {
        console.log('❌ خطأ في Telegram:', error.message);
        return false;
    }
}

// ========== مصادر بديلة للبيانات (بدون Binance API مباشر) ==========
async function getCryptoData(symbol) {
    try {
        // المحاولة 1: CoinGecko API (مجاني ولا يحتاج API Key)
        try {
            const coinId = getCoinGeckoId(symbol);
            if (coinId) {
                const url = `https://api.coingecko.com/api/v3/simple/price?ids=${coinId}&vs_currencies=usd&include_24hr_change=true`;
                const response = await axios.get(url, { timeout: 5000 });
                
                if (response.data && response.data[coinId]) {
                    return {
                        price: response.data[coinId].usd,
                        change24h: response.data[coinId].usd_24h_change,
                        source: 'CoinGecko'
                    };
                }
            }
        } catch (e) {
            console.log('CoinGecko فشل، جرب مصدر آخر...');
        }

        // المحاولة 2: CoinMarketCap API (عام)
        try {
            const url = `https://api.coinmarketcap.com/data-api/v3/cryptocurrency/detail?slug=${getCMCSlug(symbol)}`;
            const response = await axios.get(url, { timeout: 5000 });
            
            if (response.data && response.data.data) {
                const data = response.data.data;
                return {
                    price: data.quote.USD.price,
                    change24h: data.quote.USD.percentChange24h,
                    source: 'CoinMarketCap'
                };
            }
        } catch (e) {
            console.log('CoinMarketCap فشل، جرب مصدر آخر...');
        }

        // المحاولة 3: Binance Public API (بدون مفتاح)
        try {
            const url = `https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`;
            const response = await axios.get(url, { 
                timeout: 5000,
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            });
            
            if (response.data) {
                return {
                    price: parseFloat(response.data.lastPrice),
                    change24h: parseFloat(response.data.priceChangePercent),
                    high24h: parseFloat(response.data.highPrice),
                    low24h: parseFloat(response.data.lowPrice),
                    volume: parseFloat(response.data.volume),
                    source: 'Binance'
                };
            }
        } catch (e) {
            console.log('Binance فشل، جرب مصدر آخر...');
        }

        // المحاولة 4: Bybit Public API
        try {
            const bybitSymbol = symbol.replace('USDT', 'USDT');
            const url = `https://api.bybit.com/v5/market/tickers?category=spot&symbol=${bybitSymbol}`;
            const response = await axios.get(url, { timeout: 5000 });
            
            if (response.data && response.data.result && response.data.result.list[0]) {
                const data = response.data.result.list[0];
                return {
                    price: parseFloat(data.lastPrice),
                    change24h: parseFloat((data.price24hPcnt * 100).toFixed(2)),
                    source: 'Bybit'
                };
            }
        } catch (e) {
            console.log('Bybit فشل...');
        }

        return null;
    } catch (error) {
        console.log('❌ خطأ في جلب البيانات:', error.message);
        return null;
    }
}

// ========== دوال مساعدة للتحويل ==========
function getCoinGeckoId(symbol) {
    const mapping = {
        'BTCUSDT': 'bitcoin',
        'ETHUSDT': 'ethereum',
        'XRPUSDT': 'ripple',
        'SOLUSDT': 'solana',
        'BNBUSDT': 'binancecoin',
        'ADAUSDT': 'cardano',
        'DOGEUSDT': 'dogecoin'
    };
    return mapping[symbol] || null;
}

function getCMCSlug(symbol) {
    const mapping = {
        'BTCUSDT': 'bitcoin',
        'ETHUSDT': 'ethereum',
        'XRPUSDT': 'xrp',
        'SOLUSDT': 'solana',
        'BNBUSDT': 'bnb',
        'ADAUSDT': 'cardano',
        'DOGEUSDT': 'dogecoin'
    };
    return mapping[symbol] || null;
}

// ========== تحليل الإشارات ==========
function analyzeSignal(currentPrice, marketData) {
    if (!currentPrice || !marketData) return null;
    
    const signals = [];
    
    // 1. تغير يومي قوي
    if (marketData.change24h > 2.0) {
        signals.push({
            type: 'BUY',
            reason: `📈 صعود قوي: +${marketData.change24h.toFixed(2)}%`,
            strength: 'STRONG'
        });
    } else if (marketData.change24h > 0.5) {
        signals.push({
            type: 'BUY',
            reason: `🟢 صعود معتدل: +${marketData.change24h.toFixed(2)}%`,
            strength: 'MODERATE'
        });
    } else if (marketData.change24h < -2.0) {
        signals.push({
            type: 'SELL',
            reason: `📉 هبوط قوي: ${marketData.change24h.toFixed(2)}%`,
            strength: 'STRONG'
        });
    } else if (marketData.change24h < -0.5) {
        signals.push({
            type: 'SELL',
            reason: `🔴 هبوط معتدل: ${marketData.change24h.toFixed(2)}%`,
            strength: 'MODERATE'
        });
    }
    
    // 2. تغير فوري (إذا كان هناك سعر سابق)
    if (lastPrice > 0) {
        const instantChange = ((currentPrice - lastPrice) / lastPrice) * 100;
        
        if (Math.abs(instantChange) > 0.1) {
            signals.push({
                type: instantChange > 0 ? 'BUY' : 'SELL',
                reason: `⚡ تغير فوري: ${instantChange > 0 ? '+' : ''}${instantChange.toFixed(3)}%`,
                strength: 'INSTANT'
            });
        }
    }
    
    return signals.length > 0 ? signals : null;
}

// ========== إنشاء الإشارة ==========
function createSignalMessage(pairName, symbol, price, marketData, signals) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ar-SA');
    
    // تحديد نوع الإشارة الرئيسية
    let mainType = 'NEUTRAL';
    if (signals.some(s => s.type === 'BUY')) mainType = 'BUY';
    if (signals.some(s => s.type === 'SELL')) mainType = 'SELL';
    
    const emoji = mainType === 'BUY' ? '🟢' : mainType === 'SELL' ? '🔴' : '⚪';
    
    let msg = `
${emoji} <b>${mainType === 'BUY' ? 'إشارة شراء' : mainType === 'SELL' ? 'إشارة بيع' : 'تقرير سوق'}</b>
━━━━━━━━━━━━━━━━━━━━
<b>⏰ الوقت:</b> ${timeStr}
<b>📊 الزوج:</b> ${pairName}
<b>💰 الرمز:</b> ${symbol}
<b>📡 المصدر:</b> ${marketData.source}
━━━━━━━━━━━━━━━━━━━━
<b>💵 السعر الحالي:</b> $${price.toFixed(4)}
`;
    
    if (marketData.high24h && marketData.low24h) {
        msg += `<b>📈 الأعلى 24h:</b> $${marketData.high24h.toFixed(4)}\n`;
        msg += `<b>📉 الأدنى 24h:</b> $${marketData.low24h.toFixed(4)}\n`;
    }
    
    msg += `<b>🔄 التغير 24h:</b> ${marketData.change24h >= 0 ? '+' : ''}${marketData.change24h.toFixed(2)}%\n`;
    
    if (marketData.volume) {
        msg += `<b>📊 الحجم 24h:</b> $${marketData.volume.toLocaleString()}\n`;
    }
    
    msg += `━━━━━━━━━━━━━━━━━━━━\n`;
    
    if (signals && signals.length > 0) {
        msg += `<b>🎯 الإشارات:</b>\n`;
        signals.forEach(signal => {
            const signalEmoji = signal.type === 'BUY' ? '🟢' : '🔴';
            msg += `${signalEmoji} ${signal.reason}\n`;
        });
        
        msg += `\n<b>💡 التوصية:</b>\n`;
        
        if (mainType === 'BUY') {
            msg += `• فتح صفقة <b>شراء</b>\n`;
            msg += `• الهدف: $${(price * 1.01).toFixed(4)}\n`;
            msg += `• وقف الخسارة: $${(price * 0.99).toFixed(4)}\n`;
        } else if (mainType === 'SELL') {
            msg += `• فتح صفقة <b>بيع</b>\n`;
            msg += `• الهدف: $${(price * 0.99).toFixed(4)}\n`;
            msg += `• وقف الخسارة: $${(price * 1.01).toFixed(4)}\n`;
        } else {
            msg += `• <b>الانتظار</b> ومراقبة السوق\n`;
        }
    } else {
        msg += `<b>📭 لا توجد إشارات قوية حالياً</b>\n`;
    }
    
    msg += `
━━━━━━━━━━━━━━━━━━━━
<b>⚡ البوت:</b> ${botActive ? '🟢 نشط' : '🔴 متوقف'}
<b>📊 الزوج:</b> ${pairName}
━━━━━━━━━━━━━━━━━━━━
<i>⚠️ للإطلاع والتعلم فقط</i>
`;
    
    return msg;
}

// ========== المراقبة الرئيسية ==========
async function monitorMarket() {
    console.log('🚀 بدأ البوت - يستخدم مصادر عامة');
    
    let errorCount = 0;
    
    while (true) {
        try {
            if (!botActive) {
                await sleep(5000);
                continue;
            }
            
            // جلب البيانات
            const marketData = await getCryptoData(selectedPair);
            
            if (marketData && marketData.price) {
                const currentPrice = marketData.price;
                
                // تحليل الإشارات
                const signals = analyzeSignal(currentPrice, marketData);
                
                // إرسال الإشارة إذا كانت هناك إشارات
                if (signals) {
                    const message = createSignalMessage(pairName, selectedPair, currentPrice, marketData, signals);
                    await sendTelegram(message);
                    
                    console.log(`✅ أرسلت إشارة ${signals[0].type} - السعر: $${currentPrice}`);
                    
                    // تبريد 3 ثواني بعد الإشارة
                    await sleep(3000);
                }
                
                // تحديث السعر الأخير
                lastPrice = currentPrice;
                errorCount = 0; // إعادة تعيين عداد الأخطاء
                
                // عرض في الكونسول (كل 30 ثانية)
                if (Date.now() % 30000 < 100) {
                    console.log(`📊 ${pairName}: $${currentPrice} | التغير: ${marketData.change24h.toFixed(2)}% | المصدر: ${marketData.source}`);
                }
                
            } else {
                errorCount++;
                console.log(`❌ فشل في جلب البيانات (المحاولة ${errorCount})`);
                
                if (errorCount >= 3) {
                    console.log('🔄 جرب مصدر بيانات مختلف...');
                    // يمكن تغيير الزوج أو المصدر هنا
                }
            }
            
            // انتظار 2 ثانية بين الفحوصات
            await sleep(2000);
            
        } catch (error) {
            console.log('❌ خطأ في المراقبة:', error.message);
            errorCount++;
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
    console.log('🤖 بوت إشارات التداول - مصادر عامة');
    console.log('='.repeat(50));
    
    // لا نحتاج Binance API keys الآن
    console.log('\n✅ البوت يستخدم مصادر عامة (بدون API Keys)');
    console.log(`📊 الزوج: ${pairName} (${selectedPair})`);
    
    // رسالة البدء
    const startMsg = `
🚀 <b>بوت إشارات التداول يعمل الآن!</b>

✅ <b>المميزات:</b>
• يستخدم مصادر بيانات عامة
• لا يحتاج Binance API
• مراقبة مستمرة
• إشارات شراء/بيع

📊 <b>الزوج النشط:</b> ${pairName}
💰 <b>الرمز:</b> ${selectedPair}
⚡ <b>السرعة:</b> فحص كل 2 ثانية

<b>📈 مصادر البيانات:</b>
• CoinGecko API
• CoinMarketCap  
• Binance Public
• Bybit Public

<i>⚡ جاري بدء المراقبة...</i>
`;
    
    await sendTelegram(startMsg);
    console.log('\n✅ تم إرسال رسالة البدء');
    
    // بدء المراقبة
    monitorMarket().catch(error => {
        console.error('❌ خطأ فادح:', error);
    });
}

// ========== تشغيل البوت ==========
startBot();
