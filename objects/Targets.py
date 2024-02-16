from objects.Bullet import Bullet
from objects.Directions import Directions
from tabulate import tabulate
from typing import Dict
import pandas as pd
from objects.RiskManager import RiskManager

class Targets:
    def __init__(self, risk_manager:RiskManager, timeframe:int):
        self.targets:Dict[str, Bullet] = dict()
        self.risk_manager = risk_manager
        self.timeframe = timeframe

    def get_targets(self) -> Dict[str, Bullet]:
        return self.targets
    
    def reload_targets(self):
        # Update the targets pnl based on selected direction
        for target in self.targets.values():
            symbol = target.target
            direction = target.trade_direction
            break_level = target.sniper_break_level
    
    def load_targets(self, target:str, reference:str ,sniper_trigger_level:float, sniper_level:float, shoot_direction:Directions):
        active_bullet = Bullet(target, reference, sniper_trigger_level, sniper_level, shoot_direction)

        if target not in self.targets:
            self.targets[target] = active_bullet
        else:
            previous_sniper_level = self.targets[target].sniper_entry_level
            previous_shoot_direction = self.targets[target].trade_direction
            
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

    def trace_targets(self):
        """
        Keep update the entry point at the stop until it enter the trade on breakout
        """
        selected_targets = self.targets.keys()
        for symbol in selected_targets:
            shild_obj = self.risk_manager.get_stop_range(symbol=symbol, timeframe=self.timeframe)
            target_obj = self.targets[symbol]
            if target_obj.trade_direction == Directions.LONG:
                self.load_targets(target=symbol, reference=target_obj.reference, 
                                  sniper_trigger_level=target_obj.sniper_break_level, 
                                  sniper_level=shild_obj.get_long_stop, shoot_direction=target_obj.trade_direction)
            
            elif target_obj.trade_direction == Directions.SHORT:
                self.load_targets(target=symbol, reference=target_obj.reference, 
                                  sniper_trigger_level=target_obj.sniper_break_level, 
                                  sniper_level=shild_obj.get_short_stop, shoot_direction=target_obj.trade_direction)


    def unload_targets(self, target:str):
        if target in self.targets:
            self.targets.pop(target)
    
    def show_targets(self):
        data = {
            'Target': [self.targets[key].target for key in self.targets],
            'Reference': [self.targets[key].reference for key in self.targets],
            'SN Break': [self.targets[key].sniper_break_level for key in self.targets],
            'SN Entry': [self.targets[key].sniper_entry_level for key in self.targets],
            'Direction': [self.targets[key].trade_direction for key in self.targets]
        }

        df = pd.DataFrame(data)
        df.set_index('Target', inplace=True)
        if not df.empty:
            print()
            print(tabulate(df, headers='keys', tablefmt='fancy_grid'))

if __name__ == "__main__":
    import time
    import pandas as pd
    risk_manager = RiskManager()
    magazine = Targets(risk_manager=risk_manager, timeframe=60)
    magazine.load_targets("USDJPY", "PDH", 10, 10, Directions.LONG)
    magazine.show_targets()
    magazine.load_targets("USDJPY", "PDH", 10, 11, Directions.LONG)
    magazine.show_targets()
    magazine.load_targets("USDJPY", "PDH", 10, 9, Directions.LONG)
    print(magazine.get_targets())
    magazine.load_targets("USDJPY", "PDH", 10, 9, Directions.SHORT)
    print(magazine.get_targets())
    magazine.load_targets("USDJPY", "PDH", 10, 15, Directions.SHORT)
    print(magazine.get_targets())
    magazine.load_targets("USDJPY", "PDH", 10, 8, Directions.SHORT)
    print(magazine.get_targets())
    magazine.load_targets("XAUUSD", "PDH", 10, 8, Directions.SHORT)
    magazine.trace_targets()
    print(magazine.get_targets())
    magazine.load_targets("USDJPY", "PDH", 10, 9, Directions.LONG)
    magazine.trace_targets()
    magazine.show_targets()
    magazine.unload_targets("USDJPY")
    print(magazine.get_targets())
    magazine.unload_targets("B")
    print(magazine.get_targets())
    magazine.unload_targets("A")
    print(magazine.get_targets())
    magazine.show_targets()
    
