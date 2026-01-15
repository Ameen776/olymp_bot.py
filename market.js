// market.js - مزود بيانات السوق المعدل للعمل على Render
const axios = require('axios');
const crypto = require('crypto');

class MarketFetcher {
    constructor() {
        this.dataSources = [
            'bybit',    // المصدر الأساسي
            'coingecko', // المصدر الاحتياطي 1
            'coinpaprika', // المصدر الاحتياطي 2
            'twelvedata' // المصدر الاحتياطي 3
        ];
        this.currentSource = 0;
        this.requestCount = 0;
        this.lastRequestTime = Date.now();
        
        // تهيئة API Keys (اختيارية)
        this.twelveDataKey = process.env.TWELVE_DATA_KEY || 'demo';
        this.alphaVantageKey = process.env.ALPHA_VANTAGE_KEY || 'demo';
    }

    async fetchPairData(pair, timeframe = '5m') {
        this.requestCount++;
        const now = Date.now();
        
        // Rate limiting: تأخير إذا كانت الطلبات كثيرة
        if (this.requestCount > 5 && (now - this.lastRequestTime) < 1000) {
            await this.delay(1000);
        }
        
        this.lastRequestTime = now;
        
        // محاولة جميع مصادر البيانات بالترتيب
        for (let i = 0; i < this.dataSources.length; i++) {
            try {
                const source = this.dataSources[(this.currentSource + i) % this.dataSources.length];
                console.log(`🔄 محاولة جلب بيانات ${pair} من ${source}`);
                
                const data = await this.fetchFromSource(source, pair, timeframe);
                
                if (data && data.currentPrice > 0) {
                    console.log(`✅ تم جلب بيانات ${pair} من ${source}`);
                    this.currentSource = (this.currentSource + i + 1) % this.dataSources.length;
                    return data;
                }
            } catch (error) {
                console.log(`❌ فشل المصدر ${this.dataSources[(this.currentSource + i) % this.dataSources.length]}: ${error.message}`);
                // الاستمرار في المحاولة مع المصدر التالي
            }
        }
        
        // إذا فشلت جميع المصادر، إرجاع بيانات تجريبية
        console.log(`⚠️ استخدام بيانات تجريبية لـ ${pair}`);
        return this.getMockData(pair, timeframe);
    }

    async fetchFromSource(source, pair, timeframe) {
        switch(source) {
            case 'bybit':
                return await this.fetchFromBybit(pair, timeframe);
            case 'coingecko':
                return await this.fetchFromCoinGecko(pair, timeframe);
            case 'coinpaprika':
                return await this.fetchFromCoinPaprika(pair, timeframe);
            case 'twelvedata':
                return await this.fetchFromTwelveData(pair, timeframe);
            default:
                return await this.fetchFromBybit(pair, timeframe);
        }
    }

    async fetchFromBybit(pair, timeframe) {
        try {
            const symbol = this.convertSymbolForBybit(pair);
            const url = 'https://api.bybit.com/v5/market/kline';
            
            const params = {
                category: 'spot',
                symbol: symbol,
                interval: this.convertTimeframe(timeframe),
                limit: 100
            };

            console.log(`📡 Bybit Request: ${url}?${new URLSearchParams(params)}`);
            
            const response = await axios.get(url, { 
                params,
                timeout: 5000
            });
            
            if (response.data.retCode !== 0) {
                throw new Error(`Bybit API Error: ${response.data.retMsg}`);
            }

            if (!response.data.result || !response.data.result.list) {
                throw new Error('No data returned from Bybit');
            }

            const klines = response.data.result.list;
            
            if (klines.length === 0) {
                throw new Error('Empty klines data');
            }

            // تحويل البيانات إلى صيغة قابلة للاستخدام
            const formattedKlines = klines.map(k => [
                parseFloat(k[0]), // timestamp
                parseFloat(k[1]), // open
                parseFloat(k[2]), // high
                parseFloat(k[3]), // low
                parseFloat(k[4]), // close
                parseFloat(k[5])  // volume
            ]);

            const indicators = this.calculateIndicators(formattedKlines);
            const latest = formattedKlines[formattedKlines.length - 1];

            return {
                pair: pair,
                timeframe: timeframe,
                currentPrice: latest[4],
                indicators: indicators,
                ohlcData: {
                    open: latest[1],
                    high: latest[2],
                    low: latest[3],
                    close: latest[4],
                    volume: latest[5]
                },
                timestamp: new Date().toISOString(),
                source: 'bybit'
            };
            
        } catch (error) {
            console.error(`Bybit error for ${pair}:`, error.message);
            throw error;
        }
    }

    async fetchFromCoinGecko(pair, timeframe) {
        try {
            const [base, quote] = pair.split('/');
            const coinId = this.getCoinGeckoId(base);
            const vsCurrency = quote.toLowerCase().replace('usdt', 'usd');
            
            // سعر حالي
            const priceUrl = 'https://api.coingecko.com/api/v3/simple/price';
            const priceParams = {
                ids: coinId,
                vs_currencies: vsCurrency,
                include_market_cap: false,
                include_24hr_vol: true,
                include_24hr_change: true,
                include_last_updated_at: true
            };

            const priceRes = await axios.get(priceUrl, { 
                params: priceParams,
                timeout: 5000
            });
            
            if (!priceRes.data[coinId]) {
                throw new Error('Coin not found in CoinGecko');
            }

            // بيانات تاريخية
            const ohlcUrl = `https://api.coingecko.com/api/v3/coins/${coinId}/ohlc`;
            const days = this.getDaysForTimeframe(timeframe);
            
            const ohlcRes = await axios.get(ohlcUrl, {
                params: {
                    vs_currency: vsCurrency,
                    days: days
                },
                timeout: 5000
            });

            if (!ohlcRes.data || ohlcRes.data.length === 0) {
                throw new Error('No historical data from CoinGecko');
            }

            const indicators = this.calculateIndicatorsFromOHLC(ohlcRes.data);
            const latest = ohlcRes.data[ohlcRes.data.length - 1];

            return {
                pair: pair,
                timeframe: timeframe,
                currentPrice: priceRes.data[coinId][vsCurrency],
                indicators: indicators,
                ohlcData: {
                    open: latest[1],
                    high: latest[2],
                    low: latest[3],
                    close: latest[4],
                    volume: 0
                },
                timestamp: new Date(priceRes.data[coinId].last_updated_at * 1000).toISOString(),
                source: 'coingecko'
            };
            
        } catch (error) {
            console.error(`CoinGecko error for ${pair}:`, error.message);
            throw error;
        }
    }

    async fetchFromCoinPaprika(pair, timeframe) {
        try {
            const symbol = this.convertSymbolForCoinPaprika(pair);
            
            // سعر حالي
            const tickerUrl = `https://api.coinpaprika.com/v1/tickers/${symbol}`;
            const response = await axios.get(tickerUrl, { timeout: 5000 });
            
            if (response.data.error) {
                throw new Error(response.data.error);
            }

            const data = response.data;
            
            // بيانات تاريخية مبسطة (لا تحتاج لحساب مؤشرات معقدة)
            const priceChange24h = data.quotes.USD.percent_change_24h || 0;
            const volatility = Math.abs(priceChange24h);
            
            return {
                pair: pair,
                timeframe: timeframe,
                currentPrice: data.quotes.USD.price,
                indicators: {
                    ma_short: data.quotes.USD.price,
                    ma_long: data.quotes.USD.price * 0.99,
                    trend: priceChange24h > 0 ? 'UP' : priceChange24h < 0 ? 'DOWN' : 'NEUTRAL',
                    trend_strength: Math.abs(priceChange24h),
                    rsi: priceChange24h > 5 ? 70 : priceChange24h < -5 ? 30 : 50,
                    momentum: priceChange24h,
                    volatility: volatility,
                    volatility_level: volatility > 10 ? 'HIGH' : volatility > 5 ? 'MEDIUM' : 'LOW'
                },
                ohlcData: {
                    open: data.quotes.USD.open_24h,
                    high: data.quotes.USD.high_24h,
                    low: data.quotes.USD.low_24h,
                    close: data.quotes.USD.price,
                    volume: data.quotes.USD.volume_24h
                },
                timestamp: new Date().toISOString(),
                source: 'coinpaprika'
            };
            
        } catch (error) {
            console.error(`CoinPaprika error for ${pair}:`, error.message);
            throw error;
        }
    }

    async fetchFromTwelveData(pair, timeframe) {
        try {
            const symbol = pair.replace('/', '').replace('OTC', '');
            const url = 'https://api.twelvedata.com/time_series';
            
            const params = {
                symbol: symbol,
                interval: timeframe,
                apikey: this.twelveDataKey,
                outputsize: 100,
                dp: 8
            };

            const response = await axios.get(url, { 
                params,
                timeout: 5000
            });

            if (response.data.status === 'error') {
                throw new Error(`TwelveData API Error: ${response.data.message}`);
            }

            if (!response.data.values || response.data.values.length === 0) {
                throw new Error('No data from TwelveData');
            }

            const values = response.data.values;
            const latest = values[0];
            const closes = values.map(v => parseFloat(v.close)).reverse();
            const highs = values.map(v => parseFloat(v.high)).reverse();
            const lows = values.map(v => parseFloat(v.low)).reverse();

            const indicators = this.calculateIndicatorsFromArrays(closes, highs, lows);

            return {
                pair: pair,
                timeframe: timeframe,
                currentPrice: parseFloat(latest.close),
                indicators: indicators,
                ohlcData: {
                    open: parseFloat(latest.open),
                    high: parseFloat(latest.high),
                    low: parseFloat(latest.low),
                    close: parseFloat(latest.close),
                    volume: parseFloat(latest.volume) || 0
                },
                timestamp: latest.datetime,
                source: 'twelvedata'
            };
            
        } catch (error) {
            console.error(`TwelveData error for ${pair}:`, error.message);
            throw error;
        }
    }

    // دالة الاحتياطي: بيانات تجريبية إذا فشلت جميع المصادر
    getMockData(pair, timeframe) {
        const basePrice = this.getBasePriceForPair(pair);
        const fluctuation = (Math.random() * 0.02 - 0.01); // ±1%
        const currentPrice = basePrice * (1 + fluctuation);
        
        return {
            pair: pair,
            timeframe: timeframe,
            currentPrice: currentPrice,
            indicators: {
                ma_short: currentPrice * 1.001,
                ma_long: currentPrice * 0.999,
                trend: Math.random() > 0.5 ? 'UP' : 'DOWN',
                trend_strength: Math.random() * 10,
                rsi: 50 + (Math.random() * 20 - 10),
                momentum: currentPrice * 0.001,
                volatility: Math.random() * 3,
                volatility_level: Math.random() > 0.7 ? 'HIGH' : Math.random() > 0.4 ? 'MEDIUM' : 'LOW'
            },
            ohlcData: {
                open: currentPrice * 0.998,
                high: currentPrice * 1.002,
                low: currentPrice * 0.998,
                close: currentPrice,
                volume: 1000000 * (1 + Math.random())
            },
            timestamp: new Date().toISOString(),
            source: 'mock',
            isMock: true
        };
    }

    getBasePriceForPair(pair) {
        const prices = {
            'BTC/USDT': 45000,
            'ETH/USDT': 2500,
            'SOL/USDT': 100,
            'XRP/USDT': 0.60,
            'ADA/USDT': 0.50,
            'EUR/USD': 1.08,
            'GBP/USD': 1.26,
            'USD/JPY': 150,
            'XAU/USD': 1950
        };
        return prices[pair] || 100;
    }

    // ===== دوال مساعدة =====
    
    convertSymbolForBybit(pair) {
        // تحويل BTC/USDT إلى BTCUSDT
        let symbol = pair.replace('/', '').replace('OTC', '');
        
        // إذا كان زوج فوركس، تحويله
        if (pair.includes('/') && !pair.includes('USDT')) {
            const [base, quote] = pair.split('/');
            symbol = base + quote;
        }
        
        return symbol;
    }

    convertSymbolForCoinPaprika(pair) {
        // تحويل BTC/USDT إلى btc-bitcoin
        const [base, quote] = pair.split('/');
        
        const coinMapping = {
            'BTC': 'btc-bitcoin',
            'ETH': 'eth-ethereum',
            'SOL': 'sol-solana',
            'XRP': 'xrp-xrp',
            'ADA': 'ada-cardano',
            'DOT': 'dot-polkadot',
            'DOGE': 'doge-dogecoin',
            'LTC': 'ltc-litecoin',
            'BNB': 'bnb-binance-coin'
        };
        
        return coinMapping[base] || `${base.toLowerCase()}-${base.toLowerCase()}`;
    }

    getCoinGeckoId(base) {
        const mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'DOT': 'polkadot',
            'DOGE': 'dogecoin',
            'LTC': 'litecoin',
            'BNB': 'binancecoin',
            'MATIC': 'matic-network',
            'AVAX': 'avalanche-2',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'ATOM': 'cosmos',
            'ALGO': 'algorand',
            'VET': 'vechain',
            'XTZ': 'tezos',
            'FIL': 'filecoin',
            'THETA': 'theta-token',
            'EOS': 'eos',
            'AAVE': 'aave',
            'COMP': 'compound-governance-token',
            'MKR': 'maker',
            'YFI': 'yearn-finance'
        };
        return mapping[base] || base.toLowerCase();
    }

    convertTimeframe(tf) {
        const mapping = {
            '1m': '1',
            '3m': '3',
            '5m': '5',
            '15m': '15',
            '30m': '30',
            '1h': '60',
            '2h': '120',
            '4h': '240',
            '6h': '360',
            '12h': '720',
            '1d': 'D',
            '1w': 'W',
            '1M': 'M'
        };
        return mapping[tf] || '5';
    }

    getDaysForTimeframe(tf) {
        const mapping = {
            '1m': 1,
            '5m': 1,
            '15m': 1,
            '30m': 2,
            '1h': 7,
            '4h': 14,
            '1d': 30,
            '1w': 90
        };
        return mapping[tf] || 7;
    }

    calculateIndicators(klines) {
        try {
            if (!klines || klines.length < 20) {
                return this.getDefaultIndicators();
            }

            const closes = klines.map(k => k[4]);
            const highs = klines.map(k => k[2]);
            const lows = klines.map(k => k[3]);

            // المتوسطات المتحركة
            const maShort = this.calculateSMA(closes, 9);
            const maLong = this.calculateSMA(closes, 21);

            // الاتجاه
            const trend = maShort > maLong ? 'UP' : 'DOWN';
            const trendStrength = Math.abs((maShort - maLong) / maLong * 100);

            // RSI
            const rsi = this.calculateRSI(closes, 14);

            // الزخم
            const momentum = closes[closes.length - 1] - closes[Math.max(0, closes.length - 5)];

            // التذبذب (ATR مبسط)
            const atr = this.calculateATR(highs, lows, closes, 14);
            const volatility = atr > 0 ? (atr / closes[closes.length - 1]) * 100 : 1;

            return {
                ma_short: maShort,
                ma_long: maLong,
                trend: trend,
                trend_strength: trendStrength,
                rsi: rsi,
                momentum: momentum,
                volatility: volatility,
                volatility_level: volatility > 2 ? 'HIGH' : volatility > 1 ? 'MEDIUM' : 'LOW',
                price: closes[closes.length - 1]
            };
            
        } catch (error) {
            console.error('Error calculating indicators:', error);
            return this.getDefaultIndicators();
        }
    }

    calculateIndicatorsFromOHLC(ohlcData) {
        try {
            if (!ohlcData || ohlcData.length < 10) {
                return this.getDefaultIndicators();
            }

            const closes = ohlcData.map(d => d[4]);
            const highs = ohlcData.map(d => d[2]);
            const lows = ohlcData.map(d => d[3]);

            return this.calculateIndicatorsFromArrays(closes, highs, lows);
            
        } catch (error) {
            console.error('Error calculating indicators from OHLC:', error);
            return this.getDefaultIndicators();
        }
    }

    calculateIndicatorsFromArrays(closes, highs, lows) {
        try {
            if (!closes || closes.length < 10) {
                return this.getDefaultIndicators();
            }

            const maShort = this.calculateSMA(closes, 5);
            const maLong = this.calculateSMA(closes, 10);
            
            const trend = maShort > maLong ? 'UP' : 'DOWN';
            const trendStrength = Math.abs((maShort - maLong) / maLong * 100);
            
            const momentum = closes[closes.length - 1] - closes[0];
            const priceRange = Math.max(...closes) - Math.min(...closes);
            const volatility = priceRange > 0 ? (priceRange / Math.min(...closes)) * 100 : 1;
            
            return {
                ma_short: maShort,
                ma_long: maLong,
                trend: trend,
                trend_strength: trendStrength,
                rsi: 50,
                momentum: momentum,
                volatility: volatility,
                volatility_level: volatility > 10 ? 'HIGH' : volatility > 5 ? 'MEDIUM' : 'LOW',
                price: closes[closes.length - 1]
            };
            
        } catch (error) {
            console.error('Error calculating indicators from arrays:', error);
            return this.getDefaultIndicators();
        }
    }

    getDefaultIndicators() {
        return {
            ma_short: 0,
            ma_long: 0,
            trend: 'NEUTRAL',
            trend_strength: 0,
            rsi: 50,
            momentum: 0,
            volatility: 1,
            volatility_level: 'LOW',
            price: 0
        };
    }

    calculateSMA(data, period) {
        if (data.length < period) {
            return data.length > 0 ? data[data.length - 1] : 0;
        }
        const slice = data.slice(-period);
        const sum = slice.reduce((a, b) => a + b, 0);
        return sum / period;
    }

    calculateRSI(closes, period = 14) {
        if (closes.length <= period) {
            return 50;
        }
        
        let gains = 0;
        let losses = 0;
        
        for (let i = 1; i <= period; i++) {
            const diff = closes[closes.length - i] - closes[closes.length - i - 1];
            if (diff >= 0) {
                gains += diff;
            } else {
                losses -= diff;
            }
        }
        
        const avgGain = gains / period;
        const avgLoss = losses / period;
        
        if (avgLoss === 0) {
            return 100;
        }
        
        const rs = avgGain / avgLoss;
        return 100 - (100 / (1 + rs));
    }

    calculateATR(highs, lows, closes, period) {
        const trValues = [];
        
        for (let i = 1; i < Math.min(closes.length, 20); i++) {
            const hl = highs[i] - lows[i];
            const hc = Math.abs(highs[i] - closes[i - 1]);
            const lc = Math.abs(lows[i] - closes[i - 1]);
            trValues.push(Math.max(hl, hc, lc));
        }
        
        if (trValues.length < period) {
            return trValues.length > 0 ? trValues.reduce((a, b) => a + b, 0) / trValues.length : 0;
        }
        
        const sum = trValues.slice(-period).reduce((a, b) => a + b, 0);
        return sum / period;
    }

    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

module.exports = MarketFetcher;
