import numpy as np
import MetaTrader5 as mt5
mt5.initialize()
import modules.util as util
from datetime import datetime,  timedelta
import pytz
from modules import config
import pandas as pd
from objects.Signal import Signal
from typing import Tuple, List, Dict
from objects import logme

class Indicators:
    def __init__(self) -> None:
        pass

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

    def get_previous_day_levels(self, symbol) -> Tuple[Signal, Signal]:
        previous_day = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1 , 1, 1)[0]
        high = Signal(reference="PDH", level=previous_day["high"])
        low = Signal(reference="PDL", level=previous_day["low"])
        return high, low
    
    def get_off_market_levels(self, symbol) -> Tuple[Signal, Signal]:
        
         # Current US time
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
            start_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day), hour=0, minute=0, 
                                tzinfo=pytz.timezone(f'Etc/GMT-{config.server_timezone}'))
            
            end_time = check_us_time_start.astimezone(pytz.timezone(f'Etc/GMT-{config.server_timezone}')) - timedelta(hours=1)
            
            previous_bars = pd.DataFrame(mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start_time , end_time))
            
            if not previous_bars.empty:
                off_hour_highs = Signal(reference="OMH", level=max(previous_bars["high"])) 
                off_hour_lows = Signal(reference="OML", level=min(previous_bars["low"])) 
                return off_hour_highs, off_hour_lows
            else:
                logme.logger.debug(f"{symbol}, {start_time}, {end_time}")

            return None, None
        
        return None, None


    def get_king_of_levels(self, symbol) -> Dict[str, List[Signal]]:
        highs = []
        lows = []
        pdh, pdl = self.get_previous_day_levels(symbol=symbol)
        ofh, ofl = self.get_off_market_levels(symbol=symbol)

        if pdh:
            highs.append(pdh)
        
        if ofh:
            highs.append(ofh)
        
        if pdl:
            lows.append(pdl)
        
        if ofl:
            lows.append(ofl)

        return {"resistance": highs, "support": lows}

if __name__ == "__main__":
    indi_obj = Indicators()
    print(indi_obj.get_atr("EURUSD", 60))
    print(indi_obj.get_off_market_levels("EURUSD"))
    print(indi_obj.get_king_of_levels("EURUSD"))