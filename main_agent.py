from broker_exness import ExnessBroker
from data_fetcher import MarketData
from ai_brain import TradingBrain
from executor import TradeExecutor
from risk_manager import RiskManager
from datetime import datetime
import time
import json
import MetaTrader5 as mt5
import numpy as np
import threading

class FibonacciStrategy:
    """Strategi Fibonacci 78.6% ONLY - High Probability"""
    
    def __init__(self, market, executor, tf_trend, tf_entry, sl, tp, name):
        self.market = market
        self.executor = executor
        self.symbol = "XAUUSD"
        self.tf_trend = tf_trend
        self.tf_entry = tf_entry
        self.sl_pips = sl
        self.tp_pips = tp
        self.name = name
        self.lookback = 5
        self.max_spread = 150
        self.max_positions = 1
        self.tolerance = 0.20
    
    def find_swing_points(self, df, lookback):
        highs = df['high'].values
        lows = df['low'].values
        swing_highs = []
        swing_lows = []
        for i in range(lookback, len(highs) - lookback):
            if highs[i] == max(highs[i-lookback:i+lookback+1]):
                swing_highs.append({'price': highs[i], 'index': i})
            if lows[i] == min(lows[i-lookback:i+lookback+1]):
                swing_lows.append({'price': lows[i], 'index': i})
        return swing_highs, swing_lows
    
    def calculate_fibo_786(self, high, low):
        """Hitung HANYA level 78.6%"""
        diff = high - low
        return {
            '78.6': low + diff * 0.786,
            '0': low,
            '100': high
        }
    
    def check_candle(self, df, direction):
        if len(df) < 2:
            return False, "Data kurang", 0
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        body = abs(last['close'] - last['open'])
        candle_range = last['high'] - last['low']
        
        if candle_range == 0:
            return False, "Range 0", 0
        
        lower_wick = min(last['open'], last['close']) - last['low']
        upper_wick = last['high'] - max(last['open'], last['close'])
        
        if direction == "BUY":
            if lower_wick > body * 2:
                return True, "Bullish Pinbar", 25
            if (last['close'] > last['open'] and prev['close'] < prev['open'] and
                last['close'] > prev['open'] and last['open'] < prev['close']):
                return True, "Bullish Engulfing", 30
            if body > candle_range * 0.7 and last['close'] > last['open']:
                return True, "Bullish Marubozu", 25
            if last['close'] > last['open'] and last['close'] > (last['high'] + last['low']) / 2:
                return True, "Bullish Candle", 15
        else:
            if upper_wick > body * 2:
                return True, "Bearish Pinbar", 25
            if (last['close'] < last['open'] and prev['close'] > prev['open'] and
                last['close'] < prev['open'] and last['open'] > prev['close']):
                return True, "Bearish Engulfing", 30
            if body > candle_range * 0.7 and last['close'] < last['open']:
                return True, "Bearish Marubozu", 25
            if last['close'] < last['open'] and last['close'] < (last['high'] + last['low']) / 2:
                return True, "Bearish Candle", 15
        
        return False, "Candle lemah", 0
    
    def calculate_confidence(self, candle_bobot, trend_ok, rsi_ok):
        """Confidence khusus 78.6%"""
        confidence = 35  # Base 78.6% = level kuat
        confidence += candle_bobot
        if trend_ok:
            confidence += 15
        if rsi_ok:
            confidence += 10
        return min(100, confidence)
    
    def analyze(self, account, open_positions):
        df_entry = self.market.get_candles(self.symbol, self.tf_entry, 120)
        if df_entry is None or len(df_entry) < 40:
            return {'action': 'HOLD', 'reason': f'[{self.name}] Data entry kurang'}
        
        df_trend = self.market.get_candles(self.symbol, self.tf_trend, 50)
        if df_trend is None or len(df_trend) < 30:
            return {'action': 'HOLD', 'reason': f'[{self.name}] Data trend kurang'}
        
        price_info = self.market.broker.get_price(self.symbol)
        if price_info is None:
            return {'action': 'HOLD', 'reason': f'[{self.name}] Gagal harga'}
        
        current_bid = price_info['bid']
        current_ask = price_info['ask']
        spread = price_info['spread']
        
        gold_positions = [p for p in open_positions if 'XAU' in p['symbol']]
        if len(gold_positions) >= self.max_positions:
            total_pl = sum(p['profit'] for p in gold_positions)
            return {'action': 'HOLD', 'reason': f'[{self.name}] Posisi: {len(gold_positions)} | P/L: ${total_pl:.2f}'}
        
        if spread > self.max_spread:
            return {'action': 'HOLD', 'reason': f'[{self.name}] Spread {spread}'}
        
        # Trend
        close_trend = df_trend['close'].values
        sma_50 = np.mean(close_trend[-50:]) if len(close_trend) >= 50 else np.mean(close_trend)
        current_trend_price = close_trend[-1]
        
        if current_trend_price > sma_50:
            trend = "UP"
            trend_detail = f"🟢 {self.name} UP"
        else:
            trend = "DOWN"
            trend_detail = f"🔴 {self.name} DOWN"
        
        # Swing Points
        recent_df = df_entry.iloc[-80:].copy()
        swing_highs, swing_lows = self.find_swing_points(recent_df, self.lookback)
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {'action': 'HOLD', 'reason': f'[{self.name}] Swing: H{len(swing_highs)}/L{len(swing_lows)} | {trend_detail}'}
        
        recent_high = swing_highs[-1]['price']
        recent_low = swing_lows[-1]['price']
        fibo = self.calculate_fibo_786(recent_high, recent_low)
        
        # Candle
        candle_ok, candle_msg, candle_bobot = self.check_candle(df_entry, "BUY" if trend == "UP" else "SELL")
        
        # RSI
        close_entry = df_entry['close'].values
        rsi = 50
        if len(close_entry) >= 14:
            deltas = np.diff(close_entry[-15:])
            gain = np.mean(deltas[deltas > 0]) if len(deltas[deltas > 0]) > 0 else 0
            loss = -np.mean(deltas[deltas < 0]) if len(deltas[deltas < 0]) > 0 else 0
            if loss > 0:
                rsi = 100 - (100 / (1 + gain/loss))
        
        # Cek level 78.6% ONLY
        at_786 = abs(current_bid - fibo['78.6']) / current_bid * 100 <= self.tolerance
        dist_786 = abs(current_bid - fibo['78.6']) / 0.01
        
        # ===== KEPUTUSAN 78.6% ONLY =====
        if trend == "UP" and candle_ok and at_786:
            trend_ok = True
            rsi_ok = rsi < 50
            confidence = self.calculate_confidence(candle_bobot, trend_ok, rsi_ok)
            
            return {
                'action': 'BUY',
                'reason': f'🔥 Fibo 78.6% + {candle_msg} | {trend_detail} | RSI:{rsi:.0f}',
                'sl_pips': self.sl_pips,
                'tp_pips': self.tp_pips,
                'confidence': confidence
            }
        
        if trend == "DOWN" and candle_ok and at_786:
            trend_ok = True
            rsi_ok = rsi > 50
            confidence = self.calculate_confidence(candle_bobot, trend_ok, rsi_ok)
            
            return {
                'action': 'SELL',
                'reason': f'🔥 Fibo 78.6% + {candle_msg} | {trend_detail} | RSI:{rsi:.0f}',
                'sl_pips': self.sl_pips,
                'tp_pips': self.tp_pips,
                'confidence': confidence
            }
        
        return {
            'action': 'HOLD',
            'reason': f'[{self.name}] 78.6%: {dist_786:.0f}pips | C:{candle_msg} | {trend_detail}'
        }


class ForexAIAgent:
    def __init__(self, login, password, server):
        print("=" * 60)
        print("🔥 FIBO 78.6% AGENT - HIGH PROBABILITY")
        print("=" * 60)
        
        self.broker = ExnessBroker(login, password, server)
        self.market = MarketData(self.broker)
        self.brain = TradingBrain()
        self.executor = TradeExecutor(self.broker)
        self.risk = RiskManager(self.broker)
        
        self.gold_scalp = FibonacciStrategy(
            self.market, self.executor,
            mt5.TIMEFRAME_M15, mt5.TIMEFRAME_M5,
            150, 300, "XAU-SCALP"
        )
        
        self.gold_intra = FibonacciStrategy(
            self.market, self.executor,
            mt5.TIMEFRAME_H1, mt5.TIMEFRAME_M15,
            300, 600, "XAU-INTRADAY"
        )
        
        self.min_confidence = 70
        
        self.running = False
        self.trade_count = 0
        self.wins = 0
        self.losses = 0
        self.log_file = "trading_log.txt"
    
    def start(self):
        if not self.broker.connect():
            print("❌ Gagal konek!")
            return False
        
        print(f"\n🔥 STRATEGI FIBO 78.6% ONLY:")
        print(f"   💶 EURUSD → AI Trend (H1)")
        print(f"   ⚡ XAU SCALP → 78.6% | M15+M5 | SL150/TP300")
        print(f"   📈 XAU INTRA → 78.6% | H1+M15 | SL300/TP600")
        print(f"   🎯 Min Confidence: {self.min_confidence}%")
        print(f"   ❌ Level 61.8% DIABAIKAN")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        return True
    
    def analyze_eurusd(self, account, open_positions):
        print(f"\n{'─'*60}")
        print(f"💶 [EURUSD] AI Trend - H1")
        
        symbol = "EURUSD"
        market_state = self.market.get_market_state(symbol, mt5.TIMEFRAME_H1)
        if market_state is None:
            print(f"   ❌ Gagal data")
            return None
        
        price = self.market.broker.get_price(symbol)
        if price:
            print(f"   💹 {price['bid']:.5f}/{price['ask']:.5f} | Spread: {price['spread']}")
        print(f"   📊 RSI: {market_state['rsi']:.2f} | Trend: {market_state['trend']}")
        
        decision = self.brain.analyze(market_state, account, open_positions)
        print(f"   🎯 {decision['action']} ({decision['confidence']}%)")
        
        return {'symbol': symbol, 'decision': decision, 'strategy': 'EURUSD_AI'}
    
    def analyze_gold(self, strategy, account, open_positions):
        print(f"\n{'─'*60}")
        print(f"{'⚡' if 'SCALP' in strategy.name else '📈'} [XAUUSD] 78.6% {strategy.name}")
        
        result = strategy.analyze(account, open_positions)
        if result is None:
            return None
        
        price = self.market.broker.get_price("XAUUSD")
        if price:
            df_trend = self.market.get_candles("XAUUSD", strategy.tf_trend, 50)
            if df_trend is not None:
                close_t = df_trend['close'].values
                sma = np.mean(close_t[-50:]) if len(close_t) >= 50 else np.mean(close_t)
                trend = "🟢 UP" if price['bid'] > sma else "🔴 DOWN"
                print(f"   💹 {price['bid']:.2f}/{price['ask']:.2f} | {trend} | Spread: {price['spread']}")
        
        print(f"   📋 {result['reason']}")
        
        confidence = result.get('confidence', 0)
        decision = {
            'action': result['action'],
            'confidence': confidence,
            'reasoning': result['reason'],
            'sl_pips': result.get('sl_pips', strategy.sl_pips),
            'tp_pips': result.get('tp_pips', strategy.tp_pips),
            'volume_lots': 0.01
        }
        
        status = "✅" if confidence >= self.min_confidence else "❌"
        print(f"   🎯 {decision['action']} | Conf: {confidence}% {status}")
        if decision['action'] in ['BUY', 'SELL'] and confidence >= self.min_confidence:
            print(f"   🛑 SL:{decision['sl_pips']} | 🎯 TP:{decision['tp_pips']} | 📐 1:2")
        
        return {'symbol': 'XAUUSD', 'decision': decision, 'strategy': strategy.name}
    
    def analyze_all(self):
        print(f"\n{'='*60}")
        print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        account = self.broker.get_account_info()
        open_positions = self.executor.get_open_positions()
        
        print(f"\n💰 Balance: ${account['balance']:.2f} | Equity: ${account['equity']:.2f}")
        print(f"📊 Open: {len(open_positions)} posisi")
        
        if open_positions:
            total_pl = sum(p['profit'] for p in open_positions)
            print(f"💵 Total P/L: ${total_pl:.2f}")
            for pos in open_positions:
                e = "📈" if pos['profit'] >= 0 else "📉"
                print(f"   {e} {pos['symbol']} {pos['type']} | ${pos['profit']:.2f}")
        
        recommendations = []
        
        eur = self.analyze_eurusd(account, open_positions)
        if eur and eur['decision']['action'] in ['BUY', 'SELL'] and eur['decision']['confidence'] >= self.min_confidence:
            recommendations.append(eur)
        
        for strat in [self.gold_scalp, self.gold_intra]:
            g = self.analyze_gold(strat, account, open_positions)
            if g and g['decision']['action'] in ['BUY', 'SELL'] and g['decision']['confidence'] >= self.min_confidence:
                recommendations.append(g)
        
        return recommendations, account, open_positions
    
    def show_recommendations(self, recommendations, account, open_positions):
        if not recommendations:
            print(f"\n⏸️  TIDAK ADA SINYAL (78.6% + Conf ≥ {self.min_confidence}%)")
            return False
        
        print(f"\n🔥 SINYAL 78.6%:")
        for i, rec in enumerate(recommendations, 1):
            d = rec['decision']
            emoji = "💶" if 'EUR' in rec['strategy'] else ("⚡" if 'SCALP' in rec['strategy'] else "📈")
            print(f"  [{i}] {emoji} {rec['symbol']} → {d['action']} ({rec['strategy']})")
            print(f"      {d['reasoning']} | Conf: {d['confidence']}%")
            print(f"      🛑 SL:{d['sl_pips']} | 🎯 TP:{d['tp_pips']}")
        print(f"  [0] Skip | [A] All | [1-{len(recommendations)}] Pilih")
        return True
    
    def execute_trade(self, rec):
        decision = rec['decision']
        symbol = rec['symbol']
        
        if decision['confidence'] < self.min_confidence:
            return False
        
        open_positions = self.executor.get_open_positions()
        pair_positions = [p for p in open_positions if p['symbol'] == symbol]
        
        if pair_positions:
            print(f"   ❌ Sudah ada {symbol}")
            return False
        if len(open_positions) >= 3:
            print(f"   ❌ Max 3 posisi")
            return False
        
        result = self.executor.execute_order(
            symbol=symbol, action=decision['action'],
            volume_lots=0.01, sl_pips=decision['sl_pips'], tp_pips=decision['tp_pips']
        )
        
        if result:
            self.trade_count += 1
            print(f"   ✅ Ticket: {result['ticket']}")
            return True
        else:
            print(f"   ❌ Gagal!")
            return False
    
    def run_auto_mode(self, mode='ALL'):
        print(f"\n🤖 AUTO 78.6% | {mode} | Conf ≥ {self.min_confidence}%")
        print(f"   Cek tiap 30s | Ketik STOP\n")
        
        stop_flag = threading.Event()
        threading.Thread(target=lambda: [stop_flag.set() if input().strip().upper()=='STOP' else None for _ in iter(int,1)], daemon=True).start()
        
        while not stop_flag.is_set():
            try:
                account = self.broker.get_account_info()
                open_positions = self.executor.get_open_positions()
                
                eur_pos = [p for p in open_positions if 'EUR' in p['symbol']]
                gold_pos = [p for p in open_positions if 'XAU' in p['symbol']]
                
                for pos in open_positions:
                    if pos['profit'] >= 3: self.wins += 1
                    elif pos['profit'] <= -2: self.losses += 1
                
                if open_positions:
                    pl = sum(p['profit'] for p in open_positions)
                    print(f"⏸️  [{datetime.now().strftime('%H:%M:%S')}] EUR:{len(eur_pos)} Gold:{len(gold_pos)} | ${pl:.2f}")
                    time.sleep(30)
                    continue
                
                if mode in ['ALL', 'EURUSD'] and not eur_pos:
                    eur = self.analyze_eurusd(account, open_positions)
                    if eur and eur['decision']['action'] in ['BUY', 'SELL'] and eur['decision']['confidence'] >= self.min_confidence:
                        print(f"\n💶 EURUSD {eur['decision']['action']}! ({eur['decision']['confidence']}%)")
                        if self.execute_trade(eur): continue
                
                if mode in ['ALL', 'XAU_SCALP'] and not gold_pos:
                    gs = self.analyze_gold(self.gold_scalp, account, open_positions)
                    if gs and gs['decision']['action'] in ['BUY', 'SELL'] and gs['decision']['confidence'] >= self.min_confidence:
                        print(f"\n⚡ XAU SCALP {gs['decision']['action']}! ({gs['decision']['confidence']}%)")
                        if self.execute_trade(gs): continue
                
                if mode in ['ALL', 'XAU_INTRA'] and not gold_pos:
                    gi = self.analyze_gold(self.gold_intra, account, open_positions)
                    if gi and gi['decision']['action'] in ['BUY', 'SELL'] and gi['decision']['confidence'] >= self.min_confidence:
                        print(f"\n📈 XAU INTRA {gi['decision']['action']}! ({gi['decision']['confidence']}%)")
                        if self.execute_trade(gi): continue
                
                time.sleep(30)
            except Exception as e:
                print(f"❌ {e}")
                time.sleep(30)
        
        print(f"\n✅ Selesai | Trade:{self.trade_count} | W:{self.wins} L:{self.losses}")
    
    def stop(self):
        print(f"\n🛑 STOP | Trade:{self.trade_count} | W:{self.wins} L:{self.losses}")
        positions = self.executor.get_open_positions()
        if positions:
            print(f"⚠️  {len(positions)} posisi open | P/L: ${sum(p['profit'] for p in positions):.2f}")
        self.broker.disconnect()


if __name__ == "__main__":
    print("\n🔥 FIBO 78.6% ONLY - HIGH PROBABILITY")
    print("   💶 EURUSD AI | ⚡ XAU SCALP | 📈 XAU INTRA")
    
    agent = ForexAIAgent(279668304, "$Ayunazaki123", "Exness-MT5Trial8")
    
    if agent.start():
        while True:
            print(f"\n{'='*60}")
            print("MENU: 1.Analisa 2.Auto ALL 3.EUR 4.XAU Scalp 5.XAU Intra 0.Keluar")
            try:
                p = input("Pilih: ").strip()
                if p == "0": agent.stop(); break
                elif p == "1":
                    recs, acc, pos = agent.analyze_all()
                    if agent.show_recommendations(recs, acc, pos):
                        pilih = input("Pilih: ").strip().upper()
                        if pilih == 'A':
                            for r in recs: agent.execute_trade(r)
                        elif pilih.isdigit():
                            i = int(pilih)-1
                            if 0 <= i < len(recs): agent.execute_trade(recs[i])
                elif p == "2": agent.run_auto_mode('ALL')
                elif p == "3": agent.run_auto_mode('EURUSD')
                elif p == "4": agent.run_auto_mode('XAU_SCALP')
                elif p == "5": agent.run_auto_mode('XAU_INTRA')
            except KeyboardInterrupt: agent.stop(); break