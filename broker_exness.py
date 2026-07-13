import MetaTrader5 as mt5
from datetime import datetime

class ExnessBroker:
    def __init__(self, login, password, server):
        self.login = login
        self.password = password
        self.server = server
        self.connected = False
    
    def connect(self):
        print("🔌 Menghubungkan ke MT5/EXNESS...")
        
        if not mt5.initialize(
            login=self.login,
            password=self.password,
            server=self.server
        ):
            error = mt5.last_error()
            print(f"❌ GAGAL KONEK: {error}")
            return False
        
        self.connected = True
        
        account = mt5.account_info()
        print(f"✅ BERHASIL KONEK!")
        print(f"   Akun: {account.name}")
        print(f"   Server: {account.server}")
        print(f"   Balance: ${account.balance:.2f}")
        print(f"   Equity: ${account.equity:.2f}")
        print(f"   Leverage: 1:{account.leverage}")
        return True
    
    def disconnect(self):
        mt5.shutdown()
        self.connected = False
        print("🔌 Terputus dari MT5")
    
    def get_account_info(self):
        account = mt5.account_info()
        if account is None:
            return None
        
        return {
            'name': account.name,
            'login': account.login,
            'balance': account.balance,
            'equity': account.equity,
            'margin': account.margin,
            'margin_free': account.margin_free,
            'margin_level': account.margin_level,
            'profit': account.profit
        }
    
    def get_symbol_info(self, symbol="EURUSD"):
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"❌ {symbol} tidak ditemukan!")
            return None
        
        return {
            'symbol': symbol_info.name,
            'bid': symbol_info.bid,
            'ask': symbol_info.ask,
            'spread': symbol_info.spread,
            'point': symbol_info.point,
            'digits': symbol_info.digits,
            'min_volume': symbol_info.volume_min,
            'max_volume': symbol_info.volume_max,
            'contract_size': symbol_info.trade_contract_size
        }
    
    def get_price(self, symbol="EURUSD"):
        info = self.get_symbol_info(symbol)
        if info:
            return {
                'bid': info['bid'],
                'ask': info['ask'],
                'spread': info['spread'],
                'time': datetime.now()
            }
        return None


# ============================================
# TEST KONEKSI
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST KONEKSI EXNESS")
    print("=" * 60)
    
    # GANTI DENGAN DATA EXNESS LO
    broker = ExnessBroker(
        login=12345678,
        password="your_password",
        server="Exness-MT5Trial8"
    )
    
    if broker.connect():
        # Test harga
        price = broker.get_price("EURUSD")
        if price:
            print(f"\n💹 EURUSD: {price['bid']:.5f}/{price['ask']:.5f}")
            print(f"   Spread: {price['spread']} points")
        
        # Test akun
        acc = broker.get_account_info()
        print(f"\n💰 Balance: ${acc['balance']:.2f}")
        print(f"📊 Equity: ${acc['equity']:.2f}")
        print(f"📈 Margin Level: {acc['margin_level']:.1f}%")
        
        broker.disconnect()