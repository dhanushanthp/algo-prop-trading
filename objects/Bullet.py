from objects.Directions import Directions

class Bullet:
    def __init__(self, symbol:str, reference:str, break_level:float, entry_level:float, trade_direction:Directions, num_prev_breaks:int):
        self.symbol:str = symbol
        self.reference = reference
        self.break_level:float = break_level
        self.entry_level:float  = entry_level
        self.trade_direction:Directions = trade_direction
        self.points_in_stop:float = abs(break_level - entry_level)
        self.price_moved_ratio:float = 0
        self.num_prev_breaks:int = num_prev_breaks
    
    def set_price_moved_ratio(self, price_moved_ratio):
        self.price_moved_ratio = price_moved_ratio

    def __eq__(self, symbol:str):
        return isinstance(symbol, str) and self.symbol == symbol

    def __repr__(self):
        return f"Bullet(target={self.symbol}, reference={self.reference} ,sniper_trigger_level={self.break_level}, sniper_level={self.entry_level}, shoot_direction={self.trade_direction}, pnl_ratio={self.price_moved_ratio})"