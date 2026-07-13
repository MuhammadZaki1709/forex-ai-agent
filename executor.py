import MetaTrader5 as mt5
from datetime import datetime

class TradeExecutor:
    def __init__(self, broker):
        self.broker = broker
        self.magic_number = 123456
    
    def execute_order(self, symbol, action, volume_lots, sl_pips, tp_pips):
        if not self.broker.connected:
            print("❌ Tidak terkoneksi ke MT5!")
            return None
        
        if not mt5.symbol_select(symbol, True):
            print(f"❌ Gagal pilih {symbol}")
            return None
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"❌ {symbol} tidak ada")
            return None
        
        point = symbol_info.point
        price = mt5.symbol_info_tick(symbol)
        
        if action == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            entry = price.ask
            sl = entry - (sl_pips * 10 * point)
            tp = entry + (tp_pips * 10 * point)
        else:
            order_type = mt5.ORDER_TYPE_SELL
            entry = price.bid
            sl = entry + (sl_pips * 10 * point)
            tp = entry - (tp_pips * 10 * point)
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume_lots),
            "type": order_type,
            "price": entry,
            "sl": round(sl, symbol_info.digits),
            "tp": round(tp, symbol_info.digits),
            "deviation": 20,
            "magic": self.magic_number,
            "comment": "AI_AGENT",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        print(f"\n📤 ORDER {action}:")
        print(f"   Volume: {volume_lots} lots")
        print(f"   Entry: {entry:.{symbol_info.digits}f}")
        print(f"   SL: {request['sl']:.{symbol_info.digits}f}")
        print(f"   TP: {request['tp']:.{symbol_info.digits}f}")
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ GAGAL! Kode: {result.retcode}")
            print(f"   Pesan: {result.comment}")
            return None
        
        print(f"✅ SUKSES! Ticket: {result.order}")
        
        return {
            'ticket': result.order,
            'symbol': symbol,
            'action': action,
            'volume': result.volume,
            'price': result.price,
            'sl': request['sl'],
            'tp': request['tp'],
            'time': datetime.now().isoformat()
        }
    
    def get_open_positions(self):
        if not self.broker.connected:
            return []
        
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            return []
        
        result = []
        for pos in positions:
            if pos.magic == self.magic_number:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == 0 else 'SELL',
                    'volume': pos.volume,
                    'open_price': pos.price_open,
                    'current_price': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'time': datetime.fromtimestamp(pos.time).isoformat()
                })
        
        return result
    
    def close_all(self):
        positions = self.get_open_positions()
        for pos in positions:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos['symbol'],
                "volume": pos['volume'],
                "type": mt5.ORDER_TYPE_SELL if pos['type'] == 'BUY' else mt5.ORDER_TYPE_BUY,
                "position": pos['ticket'],
                "price": mt5.symbol_info_tick(pos['symbol']).bid if pos['type'] == 'BUY' else mt5.symbol_info_tick(pos['symbol']).ask,
                "deviation": 20,
                "magic": self.magic_number,
                "comment": "AI_CLOSE_ALL",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Ditutup: {pos['ticket']} | P/L: ${pos['profit']:.2f}")
        print(f"🚨 Semua posisi ditutup!")


# ============================================
# TEST EXECUTOR
# ============================================
if __name__ == "__main__":
    from broker_exness import ExnessBroker
    
    print("=" * 60)
    print("🧪 TEST EXECUTOR")
    print("=" * 60)
    
    broker = ExnessBroker(
        login=12345678,
        password="password_lo",
        server="Exness-Demo"
    )
    
    if broker.connect():
        executor = TradeExecutor(broker)
        
        positions = executor.get_open_positions()
        print(f"\n📊 Posisi Open: {len(positions)}")
        for pos in positions:
            print(f"   {pos['symbol']} {pos['type']} | P/L: ${pos['profit']:.2f}")
        
        broker.disconnect()