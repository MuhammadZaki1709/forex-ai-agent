from groq import Groq
import json
import os
from dotenv import load_dotenv

load_dotenv()

class TradingBrain:
    def analyze_scalp(self, market_data, account_info, open_positions):
        """AI analisa khusus scalping XAUUSD"""
        
        if open_positions and len(open_positions) > 0:
            pos_list = []
            for p in open_positions:
                pos_list.append(f"{p['type']} {p['symbol']} Profit: ${p['profit']:.2f}")
            position_summary = ", ".join(pos_list)
        else:
            position_summary = "Tidak ada posisi"
        
        prompt = f"""Kamu AI Scalping XAUUSD (Gold) profesional. Timeframe M15.

MARKET XAUUSD:
- Harga: {market_data['bid']:.2f}/{market_data['ask']:.2f}
- Spread: {market_data['spread']} points
- RSI: {market_data['rsi']:.2f}
- SMA20: {market_data['sma_20']:.2f}
- SMA50: {market_data['sma_50']:.2f}
- Trend: {market_data['trend']}
- Candle: {market_data['candle_direction']}

AKUN:
- Balance: ${account_info['balance']:.2f}
- Open Posisi: {len(open_positions) if open_positions else 0}
- Posisi: {position_summary}

ATURAN SCALPING XAUUSD:
- Entry kalo ada momentum jelas
- SL: 30-80 pips 
- TP: 50-150 pips
- Max 2 posisi Gold
- Volume: selalu 0.01 lot
- Ikut tren M15
- RSI < 35 = peluang BUY, RSI > 65 = peluang SELL
- Confidence minimal 65%

RESPON HANYA JSON:
{{"action": "BUY", "confidence": 75, "reasoning": "alasan", "sl_pips": 50, "tp_pips": 100, "volume_lots": 0.01}}"""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Kamu scalper Gold profesional. HANYA berikan JSON valid."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300,
            )
            
            response_text = response.choices[0].message.content.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            decision = json.loads(response_text)
            
            decision['action'] = decision.get('action', 'HOLD').upper()
            if decision['action'] not in ['BUY', 'SELL', 'HOLD']:
                decision['action'] = 'HOLD'
            
            decision['confidence'] = int(decision.get('confidence', 0))
            decision['confidence'] = min(100, max(0, decision['confidence']))
            
            decision['sl_pips'] = int(decision.get('sl_pips', 50))
            decision['sl_pips'] = max(30, min(80, decision['sl_pips']))
            
            decision['tp_pips'] = int(decision.get('tp_pips', 100))
            decision['tp_pips'] = max(50, min(150, decision['tp_pips']))
            
            decision['volume_lots'] = 0.01
            decision['reasoning'] = decision.get('reasoning', 'Scalping setup')
            
            return decision
            
        except Exception as e:
            print(f"❌ Scalp AI Error: {e}")
            return {
                "action": "HOLD", "confidence": 0,
                "reasoning": f"Error: {str(e)}",
                "sl_pips": 50, "tp_pips": 100, "volume_lots": 0.01
            }

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("❌ GROQ_API_KEY tidak ditemukan di .env!")
            raise Exception("GROQ_API_KEY missing")
        
        self.client = Groq(api_key=api_key)
        print("✅ Groq AI siap! (Llama 3.3 70B - GRATIS)")
    
    def analyze(self, market_data, account_info, open_positions):
        # Ringkasan posisi
        if open_positions and len(open_positions) > 0:
            pos_list = []
            for p in open_positions:
                pos_list.append(f"{p['type']} Profit: ${p['profit']:.2f}")
            position_summary = ", ".join(pos_list)
        else:
            position_summary = "Tidak ada posisi"
        
        prompt = f"""Kamu AI Forex Trader. Analisis EURUSD dan berikan keputusan.

MARKET EURUSD:
- Harga: {market_data['bid']:.5f}/{market_data['ask']:.5f}
- Spread: {market_data['spread']} points
- RSI: {market_data['rsi']:.2f}
- SMA20: {market_data['sma_20']:.5f}
- SMA50: {market_data['sma_50']:.5f}
- EMA20: {market_data['ema_20']:.5f}
- Trend: {market_data['trend']}
- Volume: {market_data['volume_ratio']}x normal
- Candle: {market_data['candle_direction']}

AKUN:
- Balance: ${account_info['balance']:.2f}
- Equity: ${account_info['equity']:.2f}
- Margin Level: {account_info['margin_level']:.1f}%
- Open Posisi: {len(open_positions) if open_positions else 0}
- Posisi: {position_summary}

ATURAN:
- Max 2 posisi
- Risk 2% per trade
- SL min 20 pips, TP min 30 pips
- Spread > 25 = jangan entry
- Ikut tren: UP = BUY, DOWN = SELL
- RSI < 30 = oversold, RSI > 70 = overbought

RESPON HANYA JSON:
{{"action": "BUY", "confidence": 85, "reasoning": "alasan", "sl_pips": 20, "tp_pips": 40, "volume_lots": 0.01}}"""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Kamu forex trader expert. HANYA berikan JSON valid. Tidak boleh teks lain."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300,
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Bersihin response
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            decision = json.loads(response_text)
            
            # Validasi
            decision['action'] = decision.get('action', 'HOLD').upper()
            if decision['action'] not in ['BUY', 'SELL', 'HOLD']:
                decision['action'] = 'HOLD'
            
            decision['confidence'] = int(decision.get('confidence', 0))
            decision['confidence'] = min(100, max(0, decision['confidence']))
            
            decision['sl_pips'] = int(decision.get('sl_pips', 20))
            decision['sl_pips'] = max(20, decision['sl_pips'])
            
            decision['tp_pips'] = int(decision.get('tp_pips', 40))
            decision['tp_pips'] = max(30, decision['tp_pips'])
            
            decision['volume_lots'] = float(decision.get('volume_lots', 0.01))
            decision['volume_lots'] = max(0.01, min(1.0, decision['volume_lots']))
            
            decision['reasoning'] = decision.get('reasoning', 'Tidak ada alasan')
            
            return decision
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON Error: {e}")
            print(f"   Response: {response_text}")
            return {
                "action": "HOLD", "confidence": 0,
                "reasoning": "JSON parse error",
                "sl_pips": 20, "tp_pips": 40, "volume_lots": 0.01
            }
        except Exception as e:
            print(f"❌ Groq Error: {e}")
            return {
                "action": "HOLD", "confidence": 0,
                "reasoning": f"Error: {str(e)}",
                "sl_pips": 20, "tp_pips": 40, "volume_lots": 0.01
            }


# ============================================
# TEST AI BRAIN
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST AI BRAIN - GROQ")
    print("=" * 60)
    
    brain = TradingBrain()
    
    test_market = {
        'bid': 1.08500, 'ask': 1.08512, 'spread': 12,
        'rsi': 45.5, 'sma_20': 1.08450, 'sma_50': 1.08300,
        'ema_20': 1.08460, 'trend': 'UP',
        'volume_ratio': 1.2, 'candle_direction': 'BULLISH',
        'candle_size': 0.75
    }
    
    test_account = {
        'balance': 10000, 'equity': 10000, 'margin_level': 1000
    }
    
    print("\n🤔 AI menganalisa...")
    decision = brain.analyze(test_market, test_account, [])
    
    print(f"\n📋 KEPUTUSAN AI:")
    print(f"   Action: {decision['action']}")
    print(f"   Confidence: {decision['confidence']}%")
    print(f"   Alasan: {decision['reasoning']}")
    print(f"   SL: {decision['sl_pips']} pips")
    print(f"   TP: {decision['tp_pips']} pips")
    print(f"   Volume: {decision['volume_lots']} lots")
    print("\n✅ Test selesai!")