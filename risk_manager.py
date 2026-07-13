class RiskManager:
    def __init__(self, broker):
        self.broker = broker
        self.max_open_trades = 2
        self.min_confidence = 70
        self.max_spread = 25
        self.min_margin_level = 200
    
    def check_trade_allowed(self, account_info, decision, open_positions, spread):
        reasons = []
        
        if len(open_positions) >= self.max_open_trades:
            reasons.append(f"Max posisi ({self.max_open_trades}) tercapai")
        
        if decision['confidence'] < self.min_confidence:
            reasons.append(f"Confidence rendah ({decision['confidence']}% < {self.min_confidence}%)")
        
        if spread > self.max_spread:
            reasons.append(f"Spread besar ({spread} > {self.max_spread})")
        
        if account_info['margin_level'] < self.min_margin_level:
            reasons.append(f"Margin level rendah ({account_info['margin_level']:.1f}%)")
        
        allowed = len(reasons) == 0
        return allowed, reasons