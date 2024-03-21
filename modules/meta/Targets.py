from modules.common.Bullet import Bullet
from modules.common.Directions import Directions
from tabulate import tabulate
from typing import Dict, Tuple
import pandas as pd
from modules.meta.RiskManager import RiskManager
from modules.meta.Indicators import Indicators
from modules.meta.Prices import Prices
from modules.meta import util
from modules import config
from modules.meta.wrapper import Wrapper

class Targets:
    def __init__(self, risk_manager:RiskManager, timeframe:int):
        self.targets:Dict[str, Bullet] = dict()
        self.risk_manager = risk_manager
        self.timeframe = timeframe
        self.prices = Prices()
        self.wrapper = Wrapper()
        self.indicator = Indicators()


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

    
    def check_signal_validity(self, symbol:str, reference:str, break_level:float, shoot_direction:Directions, past_break_index:int, timeframe:int=60):
        # The reason we are using -3, it's because we wanted the index to be previous one. which is 2 (mt5 index wise it's 1 since the current candle start from 0)
        # w.r.t hours our first hour start from 1, which is equal to 0 index in dataframe. So the 2 from mt5 and 1 from df adjustment we subtract 3
        current_break_bar_index = util.get_nth_bar(symbol=symbol, timeframe=timeframe) - 3
        candle_gap = current_break_bar_index - past_break_index
        
        dynamic_gap = 3 if timeframe in [5, 15] else 6

        if candle_gap > dynamic_gap:
            # Check does this already has trades on same direction, Load Passed Data
            todays_trades = self.wrapper.get_todays_trades()

            # If the symbol is not already traded, then take the trade
            if todays_trades.empty or (symbol not in list(todays_trades["symbol"])):
                active_bullet = Bullet(symbol, reference, break_level, current_break_bar_index, shoot_direction, past_break_index)
                self.targets[symbol] = active_bullet
                return True, candle_gap
            else:
                if shoot_direction == Directions.LONG:
                    traded_symbol = todays_trades[(todays_trades["symbol"] == symbol) & (todays_trades["type"] == 0) & (todays_trades["entry"] == 0)]
                    if traded_symbol.empty:
                        active_bullet = Bullet(symbol, reference, break_level, current_break_bar_index, shoot_direction, past_break_index)
                        self.targets[symbol] = active_bullet
                        return True, candle_gap
                elif shoot_direction == Directions.SHORT:
                    traded_symbol = todays_trades[(todays_trades["symbol"] == symbol) & (todays_trades["type"] == 1) & (todays_trades["entry"] == 0)]
                    if traded_symbol.empty:
                        active_bullet = Bullet(symbol, reference, break_level, current_break_bar_index, shoot_direction, past_break_index)
                        self.targets[symbol] = active_bullet
                        return True, candle_gap

        return False, candle_gap

    
    def any_previous_breakouts(self, symbol:str, timeframe:int=60) -> Tuple[list, list]:
        confirmation_candle = util.get_nth_bar(symbol=symbol, timeframe=timeframe) - 2
        previous_breaks = []
        previous_brk_index = []
        # Find which candle has the break and it's break ID
        # Loop through backkword to find which candle has the breakout candle w.r.t previous highs or lows
        for candle_index in range(2, confirmation_candle):
            breaking_candle = confirmation_candle - candle_index
            previous_candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=timeframe, i=candle_index)
            king_of_levels = self.indicator.get_king_of_levels(symbol=symbol, timeframe=timeframe, start_reference_bar=candle_index + 1)

            for resistance in king_of_levels["resistance"]:
                if previous_candle["low"] < resistance.level and previous_candle["close"] > resistance.level:
                    bar_gap = breaking_candle - resistance.break_bar_index
                    if bar_gap > 2:
                        # "HOD", breaking_candle
                        previous_breaks.append(resistance.reference)
                        previous_brk_index.append(breaking_candle)
                        
            
            for support in king_of_levels["support"]:
                if previous_candle["high"] > support.level and previous_candle["close"] < support.level:
                    bar_gap = breaking_candle - resistance.break_bar_index
                    if bar_gap > 2:
                        # print("LOD", breaking_candle)
                        previous_breaks.append(support.reference)
                        previous_brk_index.append(breaking_candle)
                    
        return previous_breaks, previous_brk_index


    def load_targets(self, target:str, reference:str ,sniper_trigger_level:float, sniper_level:float, shoot_direction:Directions, num_prev_breaks:int, timeframe:int=60):
        nth_break_bar = util.get_nth_bar(symbol=target, timeframe=timeframe)

        active_bullet = Bullet(target, reference, sniper_trigger_level, sniper_level, shoot_direction, num_prev_breaks)
        active_bullet.set_break_nth_bar(break_hour=nth_break_bar)

        if target not in self.targets:
            self.targets[target] = active_bullet
        else:
            previous_bullet = self.targets[target]
            previous_sniper_level = self.targets[target].entry_level
            previous_shoot_direction = self.targets[target].trade_direction
            previous_break_bar = self.targets[target].first_break_hour

            # The gap should not have the abs, because the upcoming hour shouor be > current hour
            if nth_break_bar != previous_break_bar:
                previous_bullet.set_bar_gap(nth_break_bar - previous_break_bar)
            
            # Then update the latest break
            previous_bullet.set_break_nth_bar(break_hour=nth_break_bar)
            
            # If direction is opposite then update the whole object
            # If the Level of break don't match the current one, consider new level
            if (previous_shoot_direction != shoot_direction):
                self.targets[target] = active_bullet
            
            #  If the direction is same
            elif previous_shoot_direction == shoot_direction:
                # Pick the lower snipper value for 
                if shoot_direction == Directions.LONG:
                    min_level = min(previous_sniper_level, sniper_level)
                    if min_level != previous_sniper_level:
                        previous_bullet.update_entry_level(sniper_level)
                        self.targets[target] = previous_bullet

                # Pick the higher snipper value for short
                elif shoot_direction == Directions.SHORT:
                    max_level = max(previous_sniper_level, sniper_level)
                    if max_level != previous_sniper_level:
                        previous_bullet.update_entry_level(sniper_level)
                        self.targets[target] = previous_bullet


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
            # self.targets.pop(target)
            self.targets[target].set_bar_gap(0)

    
    def show_targets(self, persist=False):
        data = {
            'Time' : [util.get_current_time()] * len(self.targets),
            'Target': [self.targets[key].symbol for key in self.targets],
            'Direction': [self.targets[key].trade_direction for key in self.targets],
            'Reference': [self.targets[key].reference for key in self.targets],
            'SN Break': [self.targets[key].break_level for key in self.targets],
            'Past Index': [self.targets[key].num_prev_breaks for key in self.targets],
            'Current Index': [self.targets[key].entry_level for key in self.targets],
            'Max Gap': [self.targets[key].hour_gap for key in self.targets],
        }

        df = pd.DataFrame(data)
        df.set_index('Target', inplace=True)
        if not df.empty:
            print()
            print(tabulate(df.drop("Time", axis=1).sort_values(by="Target"), headers='keys', tablefmt='fancy_grid'))

            if persist:
                df.to_csv(f'{config.local_ip}_{util.get_current_time().strftime("%Y%m%d")}.csv', mode='a', header=False)

if __name__ == "__main__":
    import time
    import pandas as pd
    import sys
    symbol = sys.argv[1]
    timeframe = int(sys.argv[2])
    risk_manager = RiskManager()
    magazine = Targets(risk_manager=risk_manager, timeframe=timeframe)
    # magazine.load_targets("AUS200.cash", "",  7666.7,  7666.7, Directions.SHORT, 1)
    # magazine.show_targets()
    # magazine.load_targets("AUS200.cash", "",  7666.7,  7666.7, Directions.SHORT, 4)
    # magazine.show_targets()
    # magazine.load_targets("AUS200.cash", "",  7666.7,  7666.7, Directions.SHORT, 5)
    # magazine.show_targets()
    # magazine.load_targets("AUS200.cash", "",  7666.7,  7666.7, Directions.SHORT, 7)
    # magazine.show_targets()
    # magazine.load_targets("AUS200.cash", "",  7666.7,  7666.7, Directions.SHORT, 1)
    # magazine.show_targets()

    print(magazine.any_previous_breakouts(symbol=symbol, timeframe=timeframe))
    # print(magazine.check_signal_validity(symbol=symbol, reference="PDH", break_level=9.090, shoot_direction=Directions.SHORT, past_break_index=0, timeframe=timeframe))
