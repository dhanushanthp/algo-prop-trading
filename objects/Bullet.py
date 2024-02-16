from objects.Directions import Directions

class Bullet:
    def __init__(self, target:str, reference:str, sniper_break_level:float, sniper_entry_level:float, trade_direction:Directions):
        self.target:str = target
        self.reference = reference
        self.sniper_break_level:float = sniper_break_level
        self.sniper_entry_level:float  = sniper_entry_level
        self.trade_direction:Directions = trade_direction
        self.pnl:float = 0
    
    def set_pnl(self, pnl):
        self.pnl = pnl

    def __eq__(self, target:str):
        return isinstance(target, str) and self.target == target

    def __repr__(self):
        return f"Bullet(target={self.target}, reference={self.reference} ,sniper_trigger_level={self.sniper_break_level}, sniper_level={self.sniper_entry_level}, shoot_direction={self.trade_direction})"