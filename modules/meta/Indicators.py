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


    def get_previous_day_levels(self, symbol, timeframe=60) -> Tuple[Signal, Signal]:
        previous_bars = pd.DataFrame(self.wrapper.get_previous_day_candles_by_time(symbol=symbol, 
                                                                                   timeframe=timeframe))
        if not previous_bars.empty:
            off_hour_highs = Signal(reference="PDH", level=max(previous_bars["high"]), break_bar_index=previous_bars["high"].idxmax())
            off_hour_lows = Signal(reference="PDL", level=min(previous_bars["low"]), break_bar_index=previous_bars["low"].idxmin())
            return off_hour_highs, off_hour_lows

        return None, None


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


        #     pdh, pdl = self.get_previous_day_levels(symbol=symbol, timeframe=timeframe)
            
        #     if pdh:
        #         highs.append(pdh)
            
        #     if pdl:
        #         lows.append(pdl)

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
    # print(indi_obj.get_previous_day_levels(symbol, timeframe))
    # print(indi_obj.get_time_based_levels(symbol=symbol, timeframe=timeframe, candle_start_hour=0, candle_end_hour=9))
    # print(indi_obj.solid_open_bar(symbol, timeframe))
    # print("OFF MARKET LEVELS", indi_obj.get_off_market_levels(symbol))
    print("KING LEVELS", indi_obj.get_king_of_levels(symbol, timeframe))
