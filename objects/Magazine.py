from objects.Bullet import Bullet
from objects.Directions import Directions
from tabulate import tabulate
from typing import Dict

class Magazine:
    def __init__(self):
        self.magazine:Dict[str, Bullet] = dict()

    def get_magazine(self) -> Dict[str, Bullet]:
        return self.magazine
    
    def load_magazine(self, target:str, sniper_trigger_level:float, sniper_level:float, shoot_direction:Directions):
        active_bullet = Bullet(target, sniper_trigger_level, sniper_level, shoot_direction)

        if target not in self.magazine:
            self.magazine[target] = active_bullet
        else:
            previous_sniper_level = self.magazine[target].sniper_level
            previous_shoot_direction = self.magazine[target].shoot_direction
            
            # If direction is opposite then update the whole object
            if previous_shoot_direction != shoot_direction:
                self.magazine[target] = active_bullet
            
            #  If the direction is same
            elif previous_shoot_direction == shoot_direction:
                # Pick the lower snipper value for long
                if shoot_direction == Directions.LONG:
                    min_level = min(previous_sniper_level, sniper_level)
                    if min_level != previous_sniper_level:
                        self.magazine[target] = active_bullet

                # Pick the higher snipper value for long 
                elif shoot_direction == Directions.SHORT:
                    max_level = max(previous_sniper_level, sniper_level)
                    if max_level != previous_sniper_level:
                        self.magazine[target] = active_bullet
        
    def unload_magazine(self, target:str):
        if target in self.magazine:
            self.magazine.pop(target)
    
    def show_magazine(self):
        data = {
            'Target': [self.magazine[key].target for key in self.magazine],
            'SN Break': [self.magazine[key].sniper_trigger_level for key in self.magazine],
            'SN Entry': [self.magazine[key].sniper_level for key in self.magazine],
            'Direction': [self.magazine[key].shoot_direction for key in self.magazine]
        }

        df = pd.DataFrame(data)
        df.set_index('Target', inplace=True)
        if not df.empty:
            print()
            print(tabulate(df, headers='keys', tablefmt='fancy_grid'))

if __name__ == "__main__":
    import time
    import pandas as pd
    magazine = Magazine()
    magazine.load_magazine("A", 10, 10, Directions.LONG)
    magazine.show_magazine()
    magazine.load_magazine("A", 10, 11, Directions.LONG)
    magazine.show_magazine()
    magazine.load_magazine("A", 10, 9, Directions.LONG)
    print(magazine.get_magazine())
    magazine.load_magazine("A", 10, 9, Directions.SHORT)
    print(magazine.get_magazine())
    magazine.load_magazine("A", 10, 15, Directions.SHORT)
    print(magazine.get_magazine())
    magazine.load_magazine("A", 10, 8, Directions.SHORT)
    print(magazine.get_magazine())
    magazine.load_magazine("B", 10, 8, Directions.SHORT)
    print(magazine.get_magazine())
    magazine.load_magazine("A", 10, 9, Directions.LONG)
    magazine.show_magazine()
    magazine.unload_magazine("A")
    print(magazine.get_magazine())
    magazine.unload_magazine("B")
    print(magazine.get_magazine())
    magazine.unload_magazine("A")
    print(magazine.get_magazine())
    magazine.show_magazine()
    
