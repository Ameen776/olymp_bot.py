import asyncio
import json
import logging
from typing import Dict, Optional
import requests
import pandas as pd

logger = logging.getLogger(__name__)

class MarketDataFetcher:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        
    async def fetch_pair_data(self, pair: str, timeframe: str = '5m') -> Optional[Dict]:
        """جلب بيانات الزوج من Binance"""
        try:
            # تحويل الزوج إلى تنسيق Binance
            symbol = pair.replace('/', '').replace('OTC', '')
            
            # جلب بيانات OHLCV
            klines_url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': timeframe,
                'limit': 100
            }
            
            response = requests.get(klines_url, params=params)
            response.raise_for_status()
            
            klines = response.json()
            
            if not klines:
                return None
            
            # تحويل إلى DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
            ])
            
            # تحويل الأنواع
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # حساب المؤشرات
            indicators = self.calculate_indicators(df)
            
            # تجهيز البيانات
            market_data = {
                'pair': pair,
                'timeframe': timeframe,
                'current_price': float(df['close'].iloc[-1]),
                'indicators': indicators,
                'ohlc_data': {
                    'open': float(df['open'].iloc[-1]),
                    'high': float(df['high'].iloc[-1]),
                    'low': float(df['low'].iloc[-1]),
                    'close': float(df['close'].iloc[-1]),
                    'volume': float(df['volume'].iloc[-1])
                },
                'timestamp': datetime.now().isoformat()
            }
            
            return market_data
            
        except Exception as e:
            logger.error(f"خطأ في جلب بيانات {pair}: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """حساب المؤشرات الفنية"""
        try:
            closes = df['close'].astype(float)
            
            # المتوسطات المتحركة
            ma_short = closes.rolling(window=9).mean().iloc[-1]
            ma_long = closes.rolling(window=21).mean().iloc[-1]
            
            # الاتجاه
            trend = "UP" if ma_short > ma_long else "DOWN"
            trend_strength = abs((ma_short - ma_long) / ma_long * 100)
            
            # RSI (مبسط)
            delta = closes.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 0
            rsi = 100 - (100 / (1 + rs))
            
            # الزخم
            momentum = closes.iloc[-1] - closes.iloc[-5]  # تغير آخر 5 فترات
            
            # التذبذب (ATR مبسط)
            high_low = df['high'].astype(float) - df['low'].astype(float)
            atr = high_low.rolling(window=14).mean().iloc[-1]
            volatility = (atr / closes.iloc[-1]) * 100
            
            return {
                'ma_short': float(ma_short),
                'ma_long': float(ma_long),
                'trend': trend,
                'trend_strength': float(trend_strength),
                'rsi': float(rsi),
                'momentum': float(momentum),
                'volatility': float(volatility),
                'volatility_level': "HIGH" if volatility > 2 else "LOW"
            }
            
        except Exception as e:
            logger.error(f"خطأ في حساب المؤشرات: {e}")
            return {}
