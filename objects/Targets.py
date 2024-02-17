from objects.Bullet import Bullet
from objects.Directions import Directions
from tabulate import tabulate
from typing import Dict
import pandas as pd
from objects.RiskManager import RiskManager
from objects. Prices import Prices

class Targets:
    def __init__(self, risk_manager:RiskManager, timeframe:int):
        self.targets:Dict[str, Bullet] = dict()
        self.risk_manager = risk_manager
        self.timeframe = timeframe
        self.prices = Prices()


    def get_targets(self) -> Dict[str, Bullet]:
        return self.targets


    def reload_targets(self):
        """
        Calculate percentage of move from the entry point (break e.g PDH, PDL) with respect to stop price (Calculated based on candles)
        """
        for target in self.targets.values():
            current_price = self.prices.get_exchange_price(symbol=target.symbol)
            
            if target.trade_direction == Directions.LONG:
                current_moved_points = current_price - target.break_level
                moved_ratio = round(current_moved_points/target.points_in_stop, 3)
                target.set_price_moved_ratio(price_moved_ratio=moved_ratio)
            elif target.trade_direction == Directions.SHORT:
                current_moved_points = target.break_level - current_price
                moved_ratio = round(current_moved_points/target.points_in_stop, 3)
                target.set_price_moved_ratio(price_moved_ratio=moved_ratio)

    
    def load_targets(self, target:str, reference:str ,sniper_trigger_level:float, sniper_level:float, shoot_direction:Directions, num_prev_breaks:int):
        active_bullet = Bullet(target, reference, sniper_trigger_level, sniper_level, shoot_direction, num_prev_breaks)

        if target not in self.targets:
            self.targets[target] = active_bullet
        else:
            previous_sniper_level = self.targets[target].entry_level
            previous_shoot_direction = self.targets[target].trade_direction
            
            # If direction is opposite then update the whole object
            if previous_shoot_direction != shoot_direction:
                self.targets[target] = active_bullet
            
            #  If the direction is same
            elif previous_shoot_direction == shoot_direction:
                # Pick the lower snipper value for 
                if shoot_direction == Directions.LONG:
                    min_level = min(previous_sniper_level, sniper_level)
                    if min_level != previous_sniper_level:
                        self.targets[target] = active_bullet

                # Pick the higher snipper value for short
                elif shoot_direction == Directions.SHORT:
                    max_level = max(previous_sniper_level, sniper_level)
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
            # TODO the stop price can be replaced with single line of if condition
            if target_obj.trade_direction == Directions.LONG:
                self.load_targets(target=symbol, reference=target_obj.reference, 
                                  sniper_trigger_level=target_obj.break_level, 
                                  sniper_level=shild_obj.get_long_stop, 
                                  shoot_direction=target_obj.trade_direction, 
                                  num_prev_breaks=target_obj.num_prev_breaks)
            
            elif target_obj.trade_direction == Directions.SHORT:
                self.load_targets(target=symbol, reference=target_obj.reference, 
                                  sniper_trigger_level=target_obj.break_level, 
                                  sniper_level=shild_obj.get_short_stop, 
                                  shoot_direction=target_obj.trade_direction, 
                                  num_prev_breaks=target_obj.num_prev_breaks)


    def unload_targets(self, target:str):
        if target in self.targets:
            self.targets.pop(target)

    
    def show_targets(self):
        data = {
            'Target': [self.targets[key].symbol for key in self.targets],
            'Reference': [self.targets[key].reference for key in self.targets],
            'SN Break': [self.targets[key].break_level for key in self.targets],
            'SN Entry': [self.targets[key].entry_level for key in self.targets],
            'Direction': [self.targets[key].trade_direction for key in self.targets],
            'PnL Ratio': [self.targets[key].price_moved_ratio for key in self.targets],
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
    
