from Bullet import Bullet
from Directions import Directions

class Magazine:
    def __init__(self):
        self.magazine = dict()
    
    def load_magazine(self, target, sniper_trigger_level, sniper_level, shoot_direction):
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
        
    def unload_magazine(self, target):
        self.magazine.pop(target)
    
    def get_table(self):
        # Convert dictionary to lists for DataFrame construction
        data = {
            'Target': [self.magazine[key].target for key in self.magazine],
            'SN Break': [self.magazine[key].sniper_trigger_level for key in self.magazine],
            'SN Entry': [self.magazine[key].sniper_level for key in self.magazine],
            'Direction': [self.magazine[key].shoot_direction for key in self.magazine]
        }

        df = pd.DataFrame(data)
        df.set_index('Target', inplace=True)
        return df

if __name__ == "__main__":
    import time
    import pandas as pd
    magazine = Magazine()
    magazine.load_magazine("A", 10, 10, Directions.LONG)
    print(magazine.get_table())
    magazine.load_magazine("A", 10, 11, Directions.LONG)
    print(magazine.get_table())
    magazine.load_magazine("A", 10, 9, Directions.LONG)
    print(magazine.magazine)
    magazine.load_magazine("A", 10, 9, Directions.SHORT)
    print(magazine.magazine)
    magazine.load_magazine("A", 10, 15, Directions.SHORT)
    print(magazine.magazine)
    magazine.load_magazine("A", 10, 8, Directions.SHORT)
    print(magazine.magazine)
    magazine.load_magazine("B", 10, 8, Directions.SHORT)
    print(magazine.magazine)
    magazine.load_magazine("A", 10, 9, Directions.LONG)
    print(magazine.get_table())
    magazine.unload_magazine("A")
    print(magazine.magazine)
    magazine.unload_magazine("B")
    print(magazine.magazine)
    if "A" in magazine.magazine:
        magazine.unload_magazine("A")
    print(magazine.magazine)
    
