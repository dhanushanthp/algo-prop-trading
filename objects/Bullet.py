from objects.Directions import Directions

class Bullet:
    def __init__(self, target:str, reference:str, sniper_trigger_level:float, sniper_level:float, shoot_direction:Directions):
        self.target:str = target
        self.reference = reference
        self.sniper_trigger_level:float = sniper_trigger_level
        self.sniper_level:float  = sniper_level
        self.shoot_direction:Directions = shoot_direction
    
    def __eq__(self, target:str):
        return isinstance(target, str) and self.target == target

    def __repr__(self):
        return f"Bullet(target={self.target}, reference={self.reference} ,sniper_trigger_level={self.sniper_trigger_level}, sniper_level={self.sniper_level}, shoot_direction={self.shoot_direction})"