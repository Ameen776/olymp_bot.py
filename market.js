const axios = require('axios');
const ccxt = require('ccxt');

class MarketFetcher {
    constructor() {
        this.binance = new ccxt.binance();
        this.binance.enableRateLimit = true;
    }
    
    async fetchPairData(pair, timeframe = '5m') {
        try {
            // تحويل تنسيق الزوج
            const symbol = pair.replace('/', '').replace('OTC', '');
            
            // جلب بيانات OHLCV
            const ohlcv = await this.binance.fetchOHLCV(symbol, timeframe, undefined, 100);
            
            if (!ohlcv || ohlcv.length === 0) {
                return null;
            }
            
            // حساب المؤشرات
            const indicators = this.calculateIndicators(ohlcv);
            
            // البيانات الحالية
            const currentCandle = ohlcv[ohlcv.length - 1];
            
            const marketData = {
                pair: pair,
                timeframe: timeframe,
                currentPrice: currentCandle[4], // سعر الإغلاق
                indicators: indicators,
                ohlcData: {
                    open: currentCandle[1],
                    high: currentCandle[2],
                    low: currentCandle[3],
                    close: currentCandle[4],
                    volume: currentCandle[5]
                },
                timestamp: new Date().toISOString()
            };
            
            return marketData;
            
        } catch (error) {
            console.error(`خطأ في جلب بيانات ${pair}:`, error.message);
            return null;
        }
    }
    
    calculateIndicators(ohlcv) {
        try {
            const closes = ohlcv.map(candle => candle[4]);
            const highs = ohlcv.map(candle => candle[2]);
            const lows = ohlcv.map(candle => candle[3]);
            
            // المتوسطات المتحركة البسيطة
            const maShort = this.sma(closes, 9);
            const maLong = this.sma(closes, 21);
            
            // الاتجاه
            const trend = maShort > maLong ? 'UP' : 'DOWN';
            const trendStrength = Math.abs((maShort - maLong) / maLong * 100);
            
            // RSI مبسط
            const rsi = this.calculateRSI(closes, 14);
            
            // الزخم
            const momentum = closes[closes.length - 1] - closes[closes.length - 5];
            
            // التذبذب (ATR مبسط)
            const atr = this.calculateATR(highs, lows, closes, 14);
            const volatility = (atr / closes[closes.length - 1]) * 100;
            
            return {
                ma_short: maShort,
                ma_long: maLong,
                trend: trend,
                trend_strength: trendStrength,
                rsi: rsi,
                momentum: momentum,
                volatility: volatility,
                volatility_level: volatility > 2 ? 'HIGH' : 'LOW'
            };
            
        } catch (error) {
            console.error('خطأ في حساب المؤشرات:', error);
            return {};
        }
    }
    
    sma(data, period) {
        if (data.length < period) return 0;
        const sum = data.slice(-period).reduce((a, b) => a + b, 0);
        return sum / period;
    }
    
    calculateRSI(closes, period = 14) {
        if (closes.length <= period) return 50;
        
        let gains = 0;
        let losses = 0;
        
        for (let i = 1; i <= period; i++) {
            const difference = closes[i] - closes[i - 1];
            if (difference >= 0) {
                gains += difference;
            } else {
                losses -= difference;
            }
        }
        
        const avgGain = gains / period;
        const avgLoss = losses / period;
        
        if (avgLoss === 0) return 100;
        
        const rs = avgGain / avgLoss;
        return 100 - (100 / (1 + rs));
    }
    
    calculateATR(highs, lows, closes, period) {
        const trValues = [];
        
        for (let i = 1; i < closes.length; i++) {
            const hl = highs[i] - lows[i];
            const hc = Math.abs(highs[i] - closes[i - 1]);
            const lc = Math.abs(lows[i] - closes[i - 1]);
            trValues.push(Math.max(hl, hc, lc));
        }
        
        if (trValues.length < period) return 0;
        
        const sum = trValues.slice(-period).reduce((a, b) => a + b, 0);
        return sum / period;
    }
}

module.exports = MarketFetcher;
