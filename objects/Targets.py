from objects.Bullet import Bullet
from objects.Directions import Directions
from tabulate import tabulate
from typing import Dict
import pandas as pd

class Targets:
    def __init__(self):
        self.targets:Dict[str, Bullet] = dict()

    def get_targets(self) -> Dict[str, Bullet]:
        return self.targets
    
    def load_targets(self, target:str, sniper_trigger_level:float, sniper_level:float, shoot_direction:Directions):
        active_bullet = Bullet(target, sniper_trigger_level, sniper_level, shoot_direction)

        if target not in self.targets:
            self.targets[target] = active_bullet
        else:
            previous_sniper_level = self.targets[target].sniper_level
            previous_shoot_direction = self.targets[target].shoot_direction
            
            # If direction is opposite then update the whole object
            if previous_shoot_direction != shoot_direction:
                self.targets[target] = active_bullet
            
            #  If the direction is same
            elif previous_shoot_direction == shoot_direction:
                # Pick the lower snipper value for long
                if shoot_direction == Directions.LONG:
                    min_level = max(previous_sniper_level, sniper_level)
                    if min_level != previous_sniper_level:
                        self.targets[target] = active_bullet

                # Pick the higher snipper value for long 
                elif shoot_direction == Directions.SHORT:
                    max_level = min(previous_sniper_level, sniper_level)
                    if max_level != previous_sniper_level:
                        self.targets[target] = active_bullet
        
    def unload_targets(self, target:str):
        if target in self.targets:
            self.targets.pop(target)
    
    def show_targets(self):
        data = {
            'Target': [self.targets[key].target for key in self.targets],
            'SN Break': [self.targets[key].sniper_trigger_level for key in self.targets],
            'SN Entry': [self.targets[key].sniper_level for key in self.targets],
            'Direction': [self.targets[key].shoot_direction for key in self.targets]
        }

        df = pd.DataFrame(data)
        df.set_index('Target', inplace=True)
        if not df.empty:
            print()
            print(tabulate(df, headers='keys', tablefmt='fancy_grid'))

if __name__ == "__main__":
    import time
    import pandas as pd
    magazine = Targets()
    magazine.load_targets("A", 10, 10, Directions.LONG)
    magazine.show_targets()
    magazine.load_targets("A", 10, 11, Directions.LONG)
    magazine.show_targets()
    magazine.load_targets("A", 10, 9, Directions.LONG)
    print(magazine.get_targets())
    magazine.load_targets("A", 10, 9, Directions.SHORT)
    print(magazine.get_targets())
    magazine.load_targets("A", 10, 15, Directions.SHORT)
    print(magazine.get_targets())
    magazine.load_targets("A", 10, 8, Directions.SHORT)
    print(magazine.get_targets())
    magazine.load_targets("B", 10, 8, Directions.SHORT)
    print(magazine.get_targets())
    magazine.load_targets("A", 10, 9, Directions.LONG)
    magazine.show_targets()
    magazine.unload_targets("A")
    print(magazine.get_targets())
    magazine.unload_targets("B")
    print(magazine.get_targets())
    magazine.unload_targets("A")
    print(magazine.get_targets())
    magazine.show_targets()
    
