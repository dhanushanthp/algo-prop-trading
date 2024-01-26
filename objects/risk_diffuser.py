class RiskDiffuser:
    def __init__(self, direction ,symbol, stop_price, position_risk):
        self.direction = direction
        self.symbol = symbol
        self.stop_price = stop_price
        self.position_risk = position_risk