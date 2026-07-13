import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from datetime import datetime

class Backtest786HighConf:
    """Backtest 78.6% Fibonacci + Confidence ≥ 85%"""
    
    def __init__(self, symbol, tf_entry, tf_trend, sl_pips, tp_pips, min_confidence=85):
        self.symbol = symbol
        self.tf_entry = tf_entry
        self.tf_trend = tf_trend
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.min_confidence = min_confidence
        self.lookback = 5
        self.tolerance = 0.20
    
    def get_historical_data(self, symbol, timeframe, start_date, end_date):
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        rates = mt5.copy_rates_range(symbol, timeframe, start, end)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    
    def find_swing_points(self, highs, lows, lookback):
        swing_highs = []
        swing_lows = []
        for i in range(lookback, len(highs) - lookback):
            if highs[i] == max(highs[i-lookback:i+lookback+1]):
                swing_highs.append({'price': highs[i], 'index': i})
            if lows[i] == min(lows[i-lookback:i+lookback+1]):
                swing_lows.append({'price': lows[i], 'index': i})
        return swing_highs, swing_lows
    
    def calculate_fibo_786(self, high, low):
        diff = high - low
        return {'78.6': low + diff * 0.786, '0': low, '100': high}
    
    def check_candle(self, open_p, high_p, low_p, close_p, prev_open, prev_close, direction):
        body = abs(close_p - open_p)
        candle_range = high_p - low_p
        if candle_range == 0:
            return False, "Range 0", 0
        
        lower_wick = min(open_p, close_p) - low_p
        upper_wick = high_p - max(open_p, close_p)
        
        if direction == "BUY":
            if lower_wick > body * 2:
                return True, "Pinbar", 25
            if (close_p > open_p and prev_close < prev_open and
                close_p > prev_open and open_p < prev_close):
                return True, "Engulfing", 30
            if body > candle_range * 0.7 and close_p > open_p:
                return True, "Marubozu", 25
            if close_p > open_p and close_p > (high_p + low_p) / 2:
                return True, "Bullish", 15
        else:
            if upper_wick > body * 2:
                return True, "Pinbar", 25
            if (close_p < open_p and prev_close > prev_open and
                close_p < prev_open and open_p > prev_close):
                return True, "Engulfing", 30
            if body > candle_range * 0.7 and close_p < open_p:
                return True, "Marubozu", 25
            if close_p < open_p and close_p < (high_p + low_p) / 2:
                return True, "Bearish", 15
        
        return False, "Lemah", 0
    
    def calculate_confidence(self, candle_bobot, trend_ok, rsi_ok):
        confidence = 35  # Base 78.6%
        confidence += candle_bobot
        if trend_ok: confidence += 15
        if rsi_ok: confidence += 10
        return min(100, confidence)
    
    def check_at_level(self, price, level, tolerance):
        if level == 0: return False
        return abs(price - level) / price * 100 <= tolerance
    
    def find_trend_index(self, df_trend, current_time):
        for i in range(len(df_trend)-1, -1, -1):
            if df_trend.iloc[i]['time'] <= current_time:
                return i
        return 0
    
    def run(self, start_date, end_date):
        print(f"\n{'='*60}")
        print(f"📊 BACKTEST 78.6% + CONFIDENCE ≥ {self.min_confidence}%")
        print(f"   Pair: {self.symbol}")
        print(f"   Entry: {self.tf_entry} | Trend: {self.tf_trend}")
        print(f"   SL: {self.sl_pips} | TP: {self.tp_pips} | Ratio 1:{self.tp_pips/self.sl_pips:.1f}")
        print(f"   Periode: {start_date} → {end_date}")
        print(f"{'='*60}\n")
        
        print("📥 Mengambil data...")
        df_entry = self.get_historical_data(self.symbol, self.tf_entry, start_date, end_date)
        df_trend = self.get_historical_data(self.symbol, self.tf_trend, start_date, end_date)
        
        if df_entry is None or len(df_entry) == 0:
            print("❌ Gagal ambil data entry!")
            return None
        if df_trend is None or len(df_trend) == 0:
            print("❌ Gagal ambil data trend!")
            return None
        
        print(f"   ✅ Entry: {len(df_entry):,} candle")
        print(f"   ✅ Trend: {len(df_trend):,} candle")
        
        trades = []
        balance = 1000
        initial_balance = 1000
        open_trade = None
        min_bars = 60
        total_bars = len(df_entry) - min_bars
        last_progress = 0
        
        print(f"\n🔄 Simulasi {total_bars:,} candle...")
        start_time = datetime.now()
        
        for i in range(min_bars, len(df_entry) - 1):
            progress = int((i - min_bars) / total_bars * 100)
            if progress >= last_progress + 10:
                elapsed = (datetime.now() - start_time).seconds
                print(f"   {progress}% | {i-min_bars:,}/{total_bars:,} | {elapsed}s")
                last_progress = progress
            
            # Cek SL/TP
            if open_trade is not None:
                current_high = df_entry.iloc[i]['high']
                current_low = df_entry.iloc[i]['low']
                
                if open_trade['type'] == 'BUY':
                    if current_low <= open_trade['sl_price']:
                        loss = -self.sl_pips * 0.1
                        balance += loss
                        trades.append({
                            'type': 'BUY', 'entry_time': open_trade['time'],
                            'exit_time': df_entry.iloc[i]['time'],
                            'entry_price': open_trade['entry_price'],
                            'exit_price': open_trade['sl_price'],
                            'profit': loss, 'result': 'SL',
                            'confidence': open_trade['confidence']
                        })
                        open_trade = None
                        continue
                    if current_high >= open_trade['tp_price']:
                        profit = self.tp_pips * 0.1
                        balance += profit
                        trades.append({
                            'type': 'BUY', 'entry_time': open_trade['time'],
                            'exit_time': df_entry.iloc[i]['time'],
                            'entry_price': open_trade['entry_price'],
                            'exit_price': open_trade['tp_price'],
                            'profit': profit, 'result': 'TP',
                            'confidence': open_trade['confidence']
                        })
                        open_trade = None
                        continue
                else:
                    if current_high >= open_trade['sl_price']:
                        loss = -self.sl_pips * 0.1
                        balance += loss
                        trades.append({
                            'type': 'SELL', 'entry_time': open_trade['time'],
                            'exit_time': df_entry.iloc[i]['time'],
                            'entry_price': open_trade['entry_price'],
                            'exit_price': open_trade['sl_price'],
                            'profit': loss, 'result': 'SL',
                            'confidence': open_trade['confidence']
                        })
                        open_trade = None
                        continue
                    if current_low <= open_trade['tp_price']:
                        profit = self.tp_pips * 0.1
                        balance += profit
                        trades.append({
                            'type': 'SELL', 'entry_time': open_trade['time'],
                            'exit_time': df_entry.iloc[i]['time'],
                            'entry_price': open_trade['entry_price'],
                            'exit_price': open_trade['tp_price'],
                            'profit': profit, 'result': 'TP',
                            'confidence': open_trade['confidence']
                        })
                        open_trade = None
                        continue
                continue
            
            # Cari sinyal
            try:
                entry_highs = df_entry['high'].values[i-min_bars:i]
                entry_lows = df_entry['low'].values[i-min_bars:i]
                entry_closes = df_entry['close'].values[i-min_bars:i]
                
                swing_highs, swing_lows = self.find_swing_points(entry_highs, entry_lows, self.lookback)
                
                if len(swing_highs) < 2 or len(swing_lows) < 2:
                    continue
                
                recent_high = swing_highs[-1]['price']
                recent_low = swing_lows[-1]['price']
                fibo = self.calculate_fibo_786(recent_high, recent_low)
                
                current_time = df_entry.iloc[i]['time']
                trend_idx = self.find_trend_index(df_trend, current_time)
                if trend_idx < 50:
                    continue
                
                trend_closes = df_trend['close'].values[trend_idx-50:trend_idx]
                sma_50 = np.mean(trend_closes)
                trend_price = df_trend.iloc[trend_idx]['close']
                trend = "UP" if trend_price > sma_50 else "DOWN"
                
                current_price = df_entry.iloc[i]['close']
                
                if i < 2:
                    continue
                
                candle_ok, candle_msg, candle_bobot = self.check_candle(
                    df_entry.iloc[i]['open'], df_entry.iloc[i]['high'],
                    df_entry.iloc[i]['low'], df_entry.iloc[i]['close'],
                    df_entry.iloc[i-1]['open'], df_entry.iloc[i-1]['close'],
                    "BUY" if trend == "UP" else "SELL"
                )
                
                if not candle_ok:
                    continue
                
                # RSI
                rsi = 50
                if len(entry_closes) >= 14:
                    deltas = np.diff(entry_closes[-15:])
                    gain = np.mean(deltas[deltas > 0]) if len(deltas[deltas > 0]) > 0 else 0
                    loss = -np.mean(deltas[deltas < 0]) if len(deltas[deltas < 0]) > 0 else 0
                    if loss > 0:
                        rsi = 100 - (100 / (1 + gain/loss))
                
                at_786 = self.check_at_level(current_price, fibo['78.6'], self.tolerance)
                
                if at_786:
                    trend_ok = True
                    rsi_ok = (trend == "UP" and rsi < 50) or (trend == "DOWN" and rsi > 50)
                    confidence = self.calculate_confidence(candle_bobot, trend_ok, rsi_ok)
                    
                    # HANYA ENTRY KALO CONFIDENCE ≥ 85%
                    if confidence >= self.min_confidence:
                        if trend == "UP":
                            open_trade = {
                                'type': 'BUY', 'time': df_entry.iloc[i]['time'],
                                'entry_price': current_price,
                                'sl_price': current_price - (self.sl_pips * 0.01),
                                'tp_price': current_price + (self.tp_pips * 0.01),
                                'confidence': confidence
                            }
                        else:
                            open_trade = {
                                'type': 'SELL', 'time': df_entry.iloc[i]['time'],
                                'entry_price': current_price,
                                'sl_price': current_price + (self.sl_pips * 0.01),
                                'tp_price': current_price - (self.tp_pips * 0.01),
                                'confidence': confidence
                            }
            except:
                continue
        
        elapsed = (datetime.now() - start_time).seconds
        print(f"   100% | Selesai {elapsed}s!")
        
        self.print_results(trades, balance, initial_balance)
        return trades if trades else None
    
    def print_results(self, trades, balance, initial_balance):
        print(f"\n{'='*60}")
        print(f"📊 HASIL BACKTEST (Confidence ≥ {self.min_confidence}%)")
        print(f"{'='*60}")
        
        if len(trades) == 0:
            print(f"\n❌ TIDAK ADA TRADE!")
            print(f"   Confidence ≥ {self.min_confidence}% terlalu ketat.")
            return
        
        df = pd.DataFrame(trades)
        wins = df[df['result'] == 'TP']
        losses = df[df['result'] == 'SL']
        
        total = len(trades)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = win_count / total * 100 if total > 0 else 0
        total_profit = df['profit'].sum()
        total_return = (balance - initial_balance) / initial_balance * 100
        
        print(f"\n📈 TOTAL TRADE: {total}")
        print(f"✅ Win: {win_count} | ❌ Loss: {loss_count}")
        print(f"🎯 Win Rate: {win_rate:.1f}%")
        print(f"💰 Total Profit: ${total_profit:.2f}")
        print(f"💵 Balance: ${initial_balance:.2f} → ${balance:.2f} ({total_return:.1f}%)")
        
        if len(wins) > 0 and len(losses) > 0:
            avg_win = wins['profit'].mean()
            avg_loss = losses['profit'].mean()
            gross_profit = wins['profit'].sum()
            gross_loss = abs(losses['profit'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
            print(f"\n📊 DETAIL:")
            print(f"   Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f}")
            print(f"   Profit Factor: {profit_factor:.2f}")
        
        # Drawdown
        cumulative = np.cumsum(df['profit'].values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_dd = drawdown.min()
        max_dd_pct = abs(max_dd) / initial_balance * 100
        
        # Consecutive
        max_cl = 0
        streak = 0
        for _, row in df.iterrows():
            if row['result'] == 'SL':
                streak += 1
                max_cl = max(max_cl, streak)
            else:
                streak = 0
        
        print(f"\n📉 RISIKO:")
        print(f"   Max Drawdown: ${max_dd:.2f} ({max_dd_pct:.1f}%)")
        print(f"   Max Consecutive Losses: {max_cl}")
        
        # Confidence distribution
        print(f"\n📊 DISTRIBUSI CONFIDENCE:")
        for conf_range in [(85, 89), (90, 94), (95, 100)]:
            low, high = conf_range
            ct = df[(df['confidence'] >= low) & (df['confidence'] <= high)]
            if len(ct) > 0:
                cw = ct[ct['result'] == 'TP']
                cwr = len(cw) / len(ct) * 100
                cpl = ct['profit'].sum()
                print(f"   {low}-{high}%: {len(ct)} trades | WR: {cwr:.1f}% | P/L: ${cpl:.2f}")
        
        # Bulanan
        df['month'] = pd.to_datetime(df['entry_time']).dt.to_period('M')
        monthly = df.groupby('month').agg(
            trades=('profit', 'count'),
            profit=('profit', 'sum'),
            wins=('result', lambda x: (x == 'TP').sum())
        )
        monthly['win_rate'] = monthly['wins'] / monthly['trades'] * 100
        
        print(f"\n📅 PERFORMA BULANAN:")
        print(f"   {'Bulan':<12} {'Trades':<8} {'Win Rate':<10} {'P/L':<12}")
        print(f"   {'-'*45}")
        profitable = 0
        for month, row in monthly.iterrows():
            if row['profit'] > 0: profitable += 1
            print(f"   {str(month):<12} {int(row['trades']):<8} {row['win_rate']:.1f}%{'':<5} ${row['profit']:.2f}")
        print(f"\n   Profitable Months: {profitable}/{len(monthly)} ({profitable/len(monthly)*100:.1f}%)")
        
        try:
            df.to_csv('backtest_85conf_results.csv', index=False)
            print(f"\n📝 Detail: backtest_85conf_results.csv")
        except:
            pass
        
        print(f"\n{'='*60}")
        print(f"📋 KESIMPULAN:")
        if win_rate >= 55 and profit_factor >= 1.8 and max_dd_pct < 30:
            print(f"   ✅ STRATEGI BAGUS! WR:{win_rate:.1f}% PF:{profit_factor:.2f} DD:{max_dd_pct:.1f}%")
        elif win_rate >= 50 and profit_factor >= 1.5 and max_dd_pct < 40:
            print(f"   ⚠️  CUKUP BAGUS. Perlu money management.")
        else:
            print(f"   ❌ PERLU OPTIMASI. WR:{win_rate:.1f}% DD:{max_dd_pct:.1f}%")
        print(f"{'='*60}")


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("📊 BACKTEST 78.6% + CONFIDENCE ≥ 85%")
    print("=" * 60)
    
    LOGIN = 279668304
    PASSWORD = "$Ayunazaki123"
    SERVER = "Exness-MT5Trial8"
    
    if not mt5.initialize(login=LOGIN, password=PASSWORD, server=SERVER):
        print("❌ Gagal konek!")
        exit()
    
    print("✅ Terhubung!")
    
    print(f"\n{'='*60}")
    print("PILIH MODE:")
    print("  1. ⚡ Scalping (M15+M5) | SL150 TP300")
    print("  2. 📈 Intraday (H1+M15) | SL300 TP600")
    print("  3. 🔧 Custom")
    print(f"{'='*60}")
    
    mode = input("\nPilih (1/2/3): ").strip()
    
    if mode == "1":
        bt = Backtest786HighConf("XAUUSD", mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M15, 150, 300, 85)
        mode_name = "SCALPING (M15+M5)"
    elif mode == "2":
        bt = Backtest786HighConf("XAUUSD", mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1, 300, 600, 85)
        mode_name = "INTRADAY (H1+M15)"
    elif mode == "3":
        tf_entry = input("Entry TF (M5/M15): ").strip().upper()
        tf_trend = input("Trend TF (M15/H1): ").strip().upper()
        sl = int(input("SL (pips): "))
        tp = int(input("TP (pips): "))
        conf = int(input("Min Confidence (%): "))
        tf_map = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1}
        bt = Backtest786HighConf("XAUUSD", tf_map.get(tf_entry, mt5.TIMEFRAME_M5), tf_map.get(tf_trend, mt5.TIMEFRAME_M15), sl, tp, conf)
        mode_name = "CUSTOM"
    else:
        print("❌ Invalid!")
        mt5.shutdown()
        exit()
    
    start = input("\nStart (default: 2026-03-01): ").strip() or "2026-03-01"
    end = input("End (default: 2026-06-30): ").strip() or "2026-06-30"
    
    print(f"\n📋 {mode_name} | SL:{bt.sl_pips} TP:{bt.tp_pips} | Conf ≥ {bt.min_confidence}%")
    print(f"   {start} → {end}")
    
    if input("\nLanjut? (y/n): ").strip().lower() == 'y':
        bt.run(start, end)
    
    mt5.shutdown()
    print("\n👋 Selesai!")