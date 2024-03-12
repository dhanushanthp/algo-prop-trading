import numpy as np
import MetaTrader5 as mt5
mt5.initialize()
import modules.meta.util as util
from datetime import datetime,  timedelta
import pytz
from modules import config
import pandas as pd
from modules.common.Signal import Signal
from typing import Tuple, List, Dict
from modules.common import logme
from modules.meta.wrapper import Wrapper
from modules.common.Directions import Directions

class Indicators:
    def __init__(self) -> None:
        self.wrapper = Wrapper()

    def get_atr(self, symbol:str, timeframe:int) -> float:
        """
        Get ATR based on 4 hour
        """    
        selected_time = util.match_timeframe(timeframe=timeframe)
        rates = mt5.copy_rates_from_pos(symbol, selected_time, 0, 20)
        
        high = np.array([x['high'] for x in rates])
        low = np.array([x['low'] for x in rates])
        close = np.array([x['close'] for x in rates])

        true_range = np.maximum(high[1:] - low[1:], abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1]))
        atr = np.mean(true_range[-14:])

        return round(atr, 5)


    def get_all_previous_bars_for_hours(self, symbol):
        # Current GMT time
        tm_zone = pytz.timezone(f'Etc/GMT-{config.server_timezone}')
        current_gmt_time = datetime.now(tm_zone)

        # Generate off market hours high and lows
        # Ignore the candle which is in middle of the day close and open
        start_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day), 
                              hour=1, minute=0, tzinfo=pytz.timezone(f'Etc/GMT'))
        
        end_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day),
                            hour=int(current_gmt_time.hour) - 1, minute=0, tzinfo=pytz.timezone(f'Etc/GMT'))
        
        previous_bars = pd.DataFrame(mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start_time , end_time))

        return previous_bars


    def get_previous_day_levels(self, symbol) -> Tuple[Signal, Signal]:
        previous_day = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1 , 1, 1)[0]

        all_previous_bars = self.get_all_previous_bars_for_hours(symbol=symbol)

        if not all_previous_bars.empty:
            high_break_counter = all_previous_bars[all_previous_bars["high"] > previous_day["high"]]["time"].count()
            low_break_counter = all_previous_bars[all_previous_bars["low"] < previous_day["low"]]["time"].count()
        else:
            high_break_counter = 0
            low_break_counter = 0


        high_signal = Signal(reference="PDH", level=previous_day["high"], num_breaks=high_break_counter)
        low_signal = Signal(reference="PDL", level=previous_day["low"], num_breaks=low_break_counter)

        return high_signal, low_signal
    

    def solid_open_bar(self, symbol, timeframe) -> Directions:
        """
        When previous bar is bearish, then the high and open price of that bar will be same
        When previous bar is bullish, then the low and open price of that bar will be same
        """
        _,hour,_ = util.get_current_day_hour_min()
        spread = self.wrapper.get_spread(symbol=symbol)
        previoud_cdl_body = self.wrapper.pre_candle_body(symbol=symbol, timeframe=timeframe)
        
        # Consider the bars 3 hours after the market open
        if hour > 4 and (previoud_cdl_body > spread):
            previous_bar = self.wrapper.get_previous_candle(symbol=symbol, timeframe=timeframe)

            # Long Signal
            if (previous_bar["close"]  > previous_bar["open"]) and (previous_bar["open"] == previous_bar["low"]):
                return Directions.LONG
            
            # Short Signal
            elif (previous_bar["close"]  < previous_bar["open"]) and (previous_bar["open"] == previous_bar["high"]):
                return Directions.SHORT


    def get_off_market_levels(self, symbol) -> Tuple[Signal, Signal]:
        current_us_time = datetime.now(pytz.timezone('US/Eastern'))
        today_year = int(current_us_time.year)
        today_month = int(current_us_time.month)
        today_date = int(current_us_time.day)

        # Check US Time
        # Added 4 minute delta, Sincd some reason the timezone is 4 min back compared to current time
        check_us_time_start = datetime(today_year, today_month, today_date, hour=9, minute=30, 
                                tzinfo=pytz.timezone('US/Eastern')) + timedelta(minutes=4)
        
        check_us_time_end = datetime(today_year, today_month, today_date, hour=15, 
                                tzinfo=pytz.timezone('US/Eastern')) + timedelta(minutes=4)
        
        if (current_us_time >= check_us_time_start) and (current_us_time < check_us_time_end):

            # Current GMT time
            tm_zone = pytz.timezone(f'Etc/GMT-{config.server_timezone}')
            current_gmt_time = datetime.now(tm_zone)

            # Generate off market hours high and lows
            start_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day), 
                                  hour=0, minute=0, tzinfo=pytz.timezone(f'Etc/GMT'))
            
            end_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day),
                            hour=int(current_gmt_time.hour) - 1, minute=0, tzinfo=pytz.timezone(f'Etc/GMT'))
            
            previous_bars = pd.DataFrame(mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start_time , end_time))
            
            if not previous_bars.empty:
                off_hour_highs = Signal(reference="OMH", level=max(previous_bars["high"])) 
                off_hour_lows = Signal(reference="OML", level=min(previous_bars["low"])) 
                return off_hour_highs, off_hour_lows
            else:
                logme.logger.debug(f"OffMar, {symbol}, {start_time}, {end_time}")

            return None, None
        
        return None, None
    
    def get_current_day_levels(self, symbol, timeframe) -> Tuple[Signal, Signal]:
        n_bars = util.get_nth_bar(symbol=symbol, timeframe=timeframe)

        previous_bars = pd.DataFrame(self.wrapper.get_candles_by_index(symbol=symbol, 
                                                                       timeframe=timeframe, 
                                                                       candle_index_start=2, 
                                                                       candle_index_end=n_bars-3))

        if not previous_bars.empty:
            off_hour_highs = Signal(reference="HOD", level=max(previous_bars["high"]), break_bar_index=previous_bars["high"].idxmax())
            off_hour_lows = Signal(reference="LOD", level=min(previous_bars["low"]), break_bar_index=previous_bars["low"].idxmin())
            return off_hour_highs, off_hour_lows

        return None, None
    
    def get_time_based_levels(self, symbol, timeframe, candle_start_hour, candle_end_hour) -> Tuple[Signal, Signal]:
        previous_bars = self.wrapper.get_candles_by_time(symbol=symbol,
                                                         timeframe=timeframe,
                                                         candle_start_hour=candle_start_hour,
                                                         candle_end_hour=candle_end_hour)
                                                         
        if not previous_bars.empty:
            pre_market_high = Signal(reference="HOD", level=max(previous_bars["high"]), break_bar_index=previous_bars["high"].idxmax())
            pre_market_low = Signal(reference="LOD", level=min(previous_bars["low"]), break_bar_index=previous_bars["low"].idxmin())
            return pre_market_high, pre_market_low


    def get_king_of_levels(self, symbol, timeframe) -> Dict[str, List[Signal]]:
        highs = []
        lows = []
        ofh, ofl = self.get_current_day_levels(symbol=symbol, timeframe=timeframe)
        
        if ofh:                
            highs.append(ofh)
        
        if ofl:
            lows.append(ofl)

        return {"resistance": highs, "support": lows}

if __name__ == "__main__":
    indi_obj = Indicators()
    import sys
    symbol = sys.argv[1]
    timeframe = int(sys.argv[2])
    # print("ATR" ,indi_obj.get_atr(symbol, 60))
    # print(indi_obj.get_current_day_levels(symbol, timeframe))
    print(indi_obj.get_time_based_levels(symbol=symbol, timeframe=timeframe, candle_start_hour=0, candle_end_hour=9))
    # print(indi_obj.solid_open_bar(symbol, timeframe))
    # print("OFF MARKET LEVELS", indi_obj.get_off_market_levels(symbol))
    # print("KING LEVELS", indi_obj.get_king_of_levels(symbol, timeframe))
