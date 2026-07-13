import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime

class MarketData:
    def __init__(self, broker):
        self.broker = broker
    
    def get_candles(self, symbol="EURUSD", timeframe=mt5.TIMEFRAME_H1, count=100):
        """Ambil data candle dari MT5"""
        if not self.broker.connected:
            return None
        
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        
        if rates is None or len(rates) == 0:
            print(f"❌ Tidak ada data untuk {symbol}")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.rename(columns={'tick_volume': 'volume', 'spread': 'spread'}, inplace=True)
        
        return df
    
    def calculate_rsi(self, prices, period=14):
        """Hitung RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices)
        gain = deltas[deltas > 0].sum() / period if len(deltas[deltas > 0]) > 0 else 0
        loss = -deltas[deltas < 0].sum() / period if len(deltas[deltas < 0]) > 0 else 0
        
        if loss == 0:
            return 100
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_sma(self, prices, period):
        """Hitung Simple Moving Average"""
        if len(prices) < period:
            return prices[-1]
        return np.mean(prices[-period:])
    
    def calculate_ema(self, prices, period):
        """Hitung Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1]
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Hitung MACD"""
        if len(prices) < slow + signal:
            return 0, 0, 0
        
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        
        # Hitung signal line sederhana
        macd_values = []
        for i in range(slow, len(prices)):
            ema_f = self.calculate_ema(prices[:i+1], fast)
            ema_s = self.calculate_ema(prices[:i+1], slow)
            macd_values.append(ema_f - ema_s)
        
        if len(macd_values) >= signal:
            signal_line = np.mean(macd_values[-signal:])
        else:
            signal_line = macd_line
        
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """Hitung Bollinger Bands"""
        if len(prices) < period:
            sma = np.mean(prices)
            return sma, sma, sma
        
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return upper, sma, lower
    
    def calculate_atr(self, df, period=14):
        """Hitung Average True Range"""
        if len(df) < period:
            return 0
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        tr_list = []
        for i in range(1, len(df)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
            tr_list.append(tr)
        
        if len(tr_list) >= period:
            return np.mean(tr_list[-period:])
        return np.mean(tr_list) if tr_list else 0
    
    def calculate_stochastic(self, df, k_period=14, d_period=3):
        """Hitung Stochastic Oscillator"""
        if len(df) < k_period:
            return 50, 50
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Hitung %K
        highest = np.max(high[-k_period:])
        lowest = np.min(low[-k_period:])
        
        if highest == lowest:
            k = 50
        else:
            k = ((close[-1] - lowest) / (highest - lowest)) * 100
        
        # Hitung %D (SMA dari %K)
        k_values = []
        for i in range(k_period, len(df)):
            h = np.max(high[i-k_period:i])
            l = np.min(low[i-k_period:i])
            if h == l:
                k_values.append(50)
            else:
                k_values.append(((close[i] - l) / (h - l)) * 100)
        
        if len(k_values) >= d_period:
            d = np.mean(k_values[-d_period:])
        else:
            d = k
        
        return k, d
    
    def detect_trend_strength(self, prices, period=50):
        """Deteksi kekuatan tren berdasarkan slope SMA"""
        if len(prices) < period:
            return "WEAK", 0
        
        sma = np.array([np.mean(prices[max(0, i-period):i+1]) for i in range(len(prices))])
        
        if len(sma) < 10:
            return "WEAK", 0
        
        # Hitung slope (10 candle terakhir)
        x = np.arange(10)
        y = sma[-10:]
        slope = np.polyfit(x, y, 1)[0]
        
        # Normalize slope
        avg_price = np.mean(prices[-period:])
        slope_pct = (slope / avg_price) * 100
        
        if slope_pct > 0.05:
            strength = "STRONG_UP"
        elif slope_pct > 0.02:
            strength = "WEAK_UP"
        elif slope_pct < -0.05:
            strength = "STRONG_DOWN"
        elif slope_pct < -0.02:
            strength = "WEAK_DOWN"
        else:
            strength = "SIDEWAYS"
        
        return strength, slope_pct
    
    def get_market_state(self, symbol="EURUSD", timeframe=None):
        """
        Ambil snapshot lengkap kondisi market
        timeframe: mt5.TIMEFRAME_H1 (default), mt5.TIMEFRAME_M15, dll
        """
        if timeframe is None:
            timeframe = mt5.TIMEFRAME_H1  # default H1
        
        # Ambil data candle
        df = self.get_candles(symbol, timeframe, 100)
        
        if df is None:
            return None
        
        # Ambil harga real-time
        price = self.broker.get_price(symbol)
        if price is None:
            return None
        
        close_prices = df['close'].values
        open_prices = df['open'].values
        high_prices = df['high'].values
        low_prices = df['low'].values
        
        # === INDIKATOR TEKNIKAL ===
        
        # RSI
        rsi = self.calculate_rsi(close_prices, 14)
        
        # Moving Averages
        sma_20 = self.calculate_sma(close_prices, 20)
        sma_50 = self.calculate_sma(close_prices, 50)
        sma_100 = self.calculate_sma(close_prices, 100) if len(close_prices) >= 100 else sma_50
        ema_20 = self.calculate_ema(close_prices, 20)
        
        # MACD
        macd_line, signal_line, macd_hist = self.calculate_macd(close_prices)
        
        # Bollinger Bands
        bb_upper, bb_mid, bb_lower = self.calculate_bollinger_bands(close_prices, 20, 2)
        
        # ATR
        atr = self.calculate_atr(df, 14)
        
        # Stochastic
        stoch_k, stoch_d = self.calculate_stochastic(df)
        
        # Trend Strength
        trend_strength, trend_slope = self.detect_trend_strength(close_prices)
        
        # === VOLUME ===
        avg_volume = np.mean(df['volume'].values[-20:])
        current_volume = df['volume'].values[-1]
        volume_ratio = round(current_volume / avg_volume, 2) if avg_volume > 0 else 1.0
        
        # === CANDLE ANALYSIS ===
        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        candle_body = abs(last_candle['close'] - last_candle['open'])
        candle_range = last_candle['high'] - last_candle['low']
        candle_size = round(candle_body / candle_range, 2) if candle_range > 0 else 0
        
        # Candle direction
        if last_candle['close'] > last_candle['open']:
            candle_direction = "BULLISH"
        elif last_candle['close'] < last_candle['open']:
            candle_direction = "BEARISH"
        else:
            candle_direction = "DOJI"
        
        # Candle pattern sederhana
        if candle_size < 0.2 and candle_range > 0:
            candle_pattern = "DOJI"
        elif candle_size > 0.7:
            candle_pattern = "MARUBOZU"
        elif last_candle['close'] > prev_candle['close'] and prev_candle['close'] < prev_candle['open']:
            candle_pattern = "BULLISH_ENGULFING"
        elif last_candle['close'] < prev_candle['close'] and prev_candle['close'] > prev_candle['open']:
            candle_pattern = "BEARISH_ENGULFING"
        else:
            candle_pattern = "NORMAL"
        
        # === SUPPORT / RESISTANCE SEDERHANA ===
        recent_high = np.max(high_prices[-20:])
        recent_low = np.min(low_prices[-20:])
        current_price = close_prices[-1]
        
        # Jarak ke support/resistance dalam persen
        distance_to_resistance = round(((recent_high - current_price) / current_price) * 100, 4) if current_price > 0 else 0
        distance_to_support = round(((current_price - recent_low) / current_price) * 100, 4) if current_price > 0 else 0
        
        # === TREND ===
        if sma_20 > sma_50:
            trend = "UP"
        elif sma_20 < sma_50:
            trend = "DOWN"
        else:
            trend = "SIDEWAYS"
        
        # === SINYAL ===
        signals = []
        
        # RSI signals
        if rsi < 30:
            signals.append("RSI_OVERSOLD")
        elif rsi > 70:
            signals.append("RSI_OVERBOUGHT")
        
        # MACD signals
        if macd_line > signal_line and macd_hist > 0:
            signals.append("MACD_BULLISH")
        elif macd_line < signal_line and macd_hist < 0:
            signals.append("MACD_BEARISH")
        
        # MA crossover
        if sma_20 > sma_50 and sma_20 > ema_20:
            signals.append("MA_BULLISH")
        elif sma_20 < sma_50 and sma_20 < ema_20:
            signals.append("MA_BEARISH")
        
        # Bollinger Band position
        if current_price >= bb_upper:
            signals.append("BB_OVERBOUGHT")
        elif current_price <= bb_lower:
            signals.append("BB_OVERSOLD")
        
        # === RETURN SEMUA DATA ===
        return {
            'symbol': symbol,
            'timeframe': str(timeframe),
            'bid': price['bid'],
            'ask': price['ask'],
            'spread': price['spread'],
            
            # Indikator
            'rsi': round(rsi, 2),
            'sma_20': round(sma_20, 5),
            'sma_50': round(sma_50, 5),
            'sma_100': round(sma_100, 5),
            'ema_20': round(ema_20, 5),
            'macd_line': round(macd_line, 6),
            'macd_signal': round(signal_line, 6),
            'macd_histogram': round(macd_hist, 6),
            'bb_upper': round(bb_upper, 5),
            'bb_mid': round(bb_mid, 5),
            'bb_lower': round(bb_lower, 5),
            'atr': round(atr, 5),
            'stoch_k': round(stoch_k, 2),
            'stoch_d': round(stoch_d, 2),
            
            # Trend
            'trend': trend,
            'trend_strength': trend_strength,
            'trend_slope': round(trend_slope, 6),
            
            # Volume
            'volume_ratio': volume_ratio,
            'current_volume': int(current_volume),
            'avg_volume': round(avg_volume, 0),
            
            # Candle
            'candle_direction': candle_direction,
            'candle_size': candle_size,
            'candle_pattern': candle_pattern,
            
            # Support/Resistance
            'recent_high': round(recent_high, 5),
            'recent_low': round(recent_low, 5),
            'distance_to_resistance': distance_to_resistance,
            'distance_to_support': distance_to_support,
            
            # Sinyal
            'signals': signals,
            
            # Metadata
            'timestamp': datetime.now().isoformat()
        }


# ============================================
# TEST DATA FETCHER
# ============================================
if __name__ == "__main__":
    from broker_exness import ExnessBroker
    
    print("=" * 60)
    print("🧪 TEST DATA MARKET - FULL INDICATORS")
    print("=" * 60)
    
    broker = ExnessBroker(
        login=12345678,
        password="password_lo",
        server="Exness-Demo"
    )
    
    if broker.connect():
        data = MarketData(broker)
        
        # Test EURUSDm H1 (Trend Following)
        print("\n" + "─" * 60)
        print("📈 EURUSDm - H1 (Trend Following)")
        print("─" * 60)
        
        state = data.get_market_state("EURUSDm", mt5.TIMEFRAME_H1)
        if state:
            print(f"   Harga: {state['bid']:.5f}/{state['ask']:.5f}")
            print(f"   Spread: {state['spread']} points")
            print(f"   RSI: {state['rsi']:.2f}")
            print(f"   Trend: {state['trend']} ({state['trend_strength']})")
            print(f"   SMA20: {state['sma_20']:.5f} | SMA50: {state['sma_50']:.5f}")
            print(f"   MACD: {state['macd_line']:.6f} | Signal: {state['macd_signal']:.6f}")
            print(f"   Candle: {state['candle_direction']} ({state['candle_pattern']})")
            print(f"   Sinyal: {', '.join(state['signals']) if state['signals'] else 'Tidak ada'}")
        
        # Test XAUUSDm M15 (Scalping)
        print("\n" + "─" * 60)
        print("⚡ XAUUSDm - M15 (Scalping)")
        print("─" * 60)
        
        state = data.get_market_state("XAUUSDm", mt5.TIMEFRAME_M15)
        if state:
            print(f"   Harga: {state['bid']:.2f}/{state['ask']:.2f}")
            print(f"   Spread: {state['spread']} points")
            print(f"   RSI: {state['rsi']:.2f}")
            print(f"   Stochastic: K={state['stoch_k']:.2f} D={state['stoch_d']:.2f}")
            print(f"   Trend: {state['trend']} ({state['trend_strength']})")
            print(f"   ATR: {state['atr']:.5f}")
            print(f"   BB: {state['bb_upper']:.2f} / {state['bb_lower']:.2f}")
            print(f"   Support: {state['recent_low']:.2f} | Resistance: {state['recent_high']:.2f}")
            print(f"   Sinyal: {', '.join(state['signals']) if state['signals'] else 'Tidak ada'}")
        
        broker.disconnect()