from Directions import Directions

class Bullet:
    def __init__(self, target:str, sniper_trigger_level:float, sniper_level:float, shoot_direction:Directions):
        self.target = target
        self.sniper_trigger_level = sniper_trigger_level
        self.sniper_level  = sniper_level
        self.shoot_direction = shoot_direction
    
    def __eq__(self, target:str):
        return isinstance(target, str) and self.target == target

    def __repr__(self):
        return f"Bullet(target={self.target}, sniper_trigger_level={self.sniper_trigger_level}, sniper_level={self.sniper_level}, shoot_direction={self.shoot_direction})"