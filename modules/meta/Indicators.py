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
from modules.meta.Prices import Prices
from modules.common.Directions import Directions

class Indicators:
    def __init__(self, wrapper: Wrapper, prices:Prices) -> None:
        self.wrapper = wrapper
        self.prices = prices
    
    def get_atr(self, symbol:str, timeframe:int, start_candle:int=0) -> float:
        rates = self.wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, last_n_candle=20)
        
        if rates.empty:
            return 0

        high = rates['high']
        low = rates['low']
        close = rates['close']

        true_range = np.maximum(high[1:] - low[1:], abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1]))
        atr = np.mean(true_range[-14:])

        return round(atr, 5)
    
    def simple_moving_average(self, symbol:str, timeframe:int, n_moving_average:int=0) -> float:
        """
        Find the simple moving average of last candle
        """
        last_n_candles = self.wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=0, last_n_candle=n_moving_average)
        close_prices = last_n_candles["close"]
        return close_prices.mean()
    
    def bollinger_bands(self, symbol:str, timeframe:int, window_size=20, num_std_dev=2) -> Tuple[float, float]:
        """
        Calculate Bollinger Bands (upper and lower) based on close prices.

        Parameters:
            window_size (int): The size of the moving average window.
            num_std_dev (int): The number of standard deviations for the bands.

        Returns:
            upper_band (numpy.array): The upper Bollinger Band.
            lower_band (numpy.array): The lower Bollinger Band.
        """
        last_n_candles = self.wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=0, last_n_candle=window_size)
        close_prices = last_n_candles["close"]
        close_prices = np.array(close_prices)
        middle_band = np.convolve(close_prices, np.ones(window_size) / window_size, mode='valid')
        std_dev = np.std(close_prices[:window_size])  # Standard deviation of the initial window
        upper_band = middle_band + num_std_dev * std_dev
        lower_band = middle_band - num_std_dev * std_dev
        return upper_band[-1], lower_band[-1]


    def sma_direction(self, symbol:str, timeframe:int, short_ma:int=10, long_ma:int=20) -> Directions:
        # Find the SMA cross over based on the last candle
        short_sma = self.simple_moving_average(symbol=symbol, timeframe=timeframe, n_moving_average=short_ma)
        long_sma = self.simple_moving_average(symbol=symbol, timeframe=timeframe, n_moving_average=long_ma)

        if short_sma > long_sma:
            return Directions.LONG
        else:
            return Directions.SHORT

    def get_previous_day_levels(self, symbol, timeframe=60) -> Tuple[Signal, Signal]:
        previous_bars = pd.DataFrame(self.wrapper.get_previous_day_candles_by_time(symbol=symbol, 
                                                                                   timeframe=timeframe))
        if not previous_bars.empty:
            off_hour_highs = Signal(reference="PDH", level=max(previous_bars["high"]), break_bar_index=previous_bars["high"].idxmax())
            off_hour_lows = Signal(reference="PDL", level=min(previous_bars["low"]), break_bar_index=previous_bars["low"].idxmin())
            return off_hour_highs, off_hour_lows

        return None, None
    
    def get_candle_cross_sma(self, symbol:str, timeframe:int, sma_crossing:int) -> Tuple[Directions, int]:
        sma_direction = self.sma_direction(symbol=symbol, timeframe=timeframe, short_ma=10, long_ma=20)
        previous_candle = self.wrapper.get_previous_candle(symbol=symbol, timeframe=timeframe)

        sma_crossing = self.simple_moving_average(symbol=symbol, timeframe=timeframe, n_moving_average=sma_crossing)

        _, hour, min = util.get_current_day_hour_min()
        break_hour = hour - 1

        bearish_cross = previous_candle["high"] > sma_crossing and previous_candle["low"] < sma_crossing and previous_candle["close"] < previous_candle["open"]
        bullish_cross = previous_candle["low"] < sma_crossing and previous_candle["high"] > sma_crossing and previous_candle["close"] > previous_candle["open"]

        if bearish_cross and sma_direction == Directions.SHORT:
            return Directions.SHORT.name, break_hour
        
        if bullish_cross and sma_direction == Directions.LONG:
            return Directions.LONG.name, break_hour
        
        return None

    
    def get_three_candle_strike(self, symbol, timeframe=60) -> Directions:
        previous_bars = self.wrapper.get_candles_by_index(symbol=symbol, timeframe=timeframe, candle_look_back=1)

        if len(previous_bars) >= 3:
            last_3_bars = previous_bars.tail(3).copy()
            last_3_bars["body_size"] = last_3_bars["close"] - last_3_bars["open"]

            is_higher_high = (last_3_bars["high"] > last_3_bars["high"].shift(1)).iloc[1:]
            is_higher_low = (last_3_bars["low"] > last_3_bars["low"].shift(1)).iloc[1:]

            is_lower_high = (last_3_bars["high"] < last_3_bars["high"].shift(1)).iloc[1:]
            is_lower_low = (last_3_bars["low"] < last_3_bars["low"].shift(1)).iloc[1:]
            
            is_bullish = all(last_3_bars["body_size"] > 0) and all(is_higher_high) and all(is_higher_low)
            is_bearish = all(last_3_bars["body_size"] < 0) and all(is_lower_high) and all(is_lower_low)

            if is_bullish:
                return Directions.LONG
            
            if is_bearish:
                return Directions.SHORT
        
        return None
    
    def get_two_candle_strike(self, symbol, timeframe=60) -> Directions:
        previous_bars = self.wrapper.get_candles_by_index(symbol=symbol, timeframe=timeframe, candle_look_back=1)

        if len(previous_bars) >= 3:
            last_2_bars = previous_bars.tail(2).copy()
            last_2_bars["body_size"] = last_2_bars["close"] - last_2_bars["open"]

            is_higher_high = (last_2_bars["high"] > last_2_bars["high"].shift(1)).iloc[1:]
            is_higher_low = (last_2_bars["low"] > last_2_bars["low"].shift(1)).iloc[1:]

            is_lower_high = (last_2_bars["high"] < last_2_bars["high"].shift(1)).iloc[1:]
            is_lower_low = (last_2_bars["low"] < last_2_bars["low"].shift(1)).iloc[1:]
            
            is_bullish = all(last_2_bars["body_size"] > 0) and all(is_higher_high) and all(is_higher_low)
            is_bearish = all(last_2_bars["body_size"] < 0) and all(is_lower_high) and all(is_lower_low)

            if is_bullish:
                return Directions.LONG
            
            if is_bearish:
                return Directions.SHORT
        
        return None

    def get_four_candle_reverse(self, symbol, timeframe=60) -> Directions:
        previous_bars = self.wrapper.get_candles_by_index(symbol=symbol, timeframe=timeframe, candle_look_back=2)
        previous_bar = self.wrapper.get_previous_candle(symbol=symbol, timeframe=timeframe)

        if len(previous_bars) >= 3:
            last_3_bars = previous_bars.tail(3).copy()
            last_3_bars["body_size"] = last_3_bars["close"] - last_3_bars["open"]

            is_higher_high = (last_3_bars["high"] > last_3_bars["high"].shift(1)).iloc[1:]
            is_higher_low = (last_3_bars["low"] > last_3_bars["low"].shift(1)).iloc[1:]

            is_lower_high = (last_3_bars["high"] < last_3_bars["high"].shift(1)).iloc[1:]
            is_lower_low = (last_3_bars["low"] < last_3_bars["low"].shift(1)).iloc[1:]
            
            is_bullish = all(last_3_bars["body_size"] > 0) and all(is_higher_high) and all(is_higher_low)
            is_bearish = all(last_3_bars["body_size"] < 0) and all(is_lower_high) and all(is_lower_low)

            pre_can_bullish = previous_bar["open"] < previous_bar["close"]
            pre_can_bearish = previous_bar["open"] > previous_bar["close"]

            if is_bullish and pre_can_bearish:
                return Directions.SHORT
            
            if is_bearish and pre_can_bullish:
                return Directions.LONG
        
        return None
    

    def get_three_candle_exit(self, symbol, ratio=2, timeframe=60) -> bool:
        """
        Exist the position if candle is randing for last 3 hours, which has longer wicks than the body
        """
        previous_bars = self.wrapper.get_candles_by_index(symbol=symbol, timeframe=timeframe, candle_look_back=1)

        if len(previous_bars) >= 3:
            last_3_bars = previous_bars.tail(3).copy()
            last_3_bars["body_size"] = abs(last_3_bars["close"] - last_3_bars["open"])
            last_3_bars["wick_size"] = abs(last_3_bars["high"] - last_3_bars["low"]) - last_3_bars["body_size"]
            last_3_bars["ratio"] = last_3_bars["wick_size"]/last_3_bars["body_size"] # Calcullate the Ratio

            is_ranging = all(last_3_bars["ratio"] > ratio)
            
            return is_ranging
        
        return False

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
    
    def get_current_day_levels(self, symbol, timeframe, start_reference_bar=2) -> Tuple[Signal, Signal]:
        previous_bars = self.wrapper.get_candles_by_index(symbol=symbol, timeframe=timeframe, candle_look_back=start_reference_bar)

        if not previous_bars.empty:
            off_hour_highs = Signal(reference="HOD", level=max(previous_bars["high"]), break_bar_index=previous_bars["high"].idxmax() + 1)
            off_hour_lows = Signal(reference="LOD", level=min(previous_bars["low"]), break_bar_index=previous_bars["low"].idxmin() + 1)
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

    def candle_move_ratio(self, symbol, timeframe):
        # Start from 2, Since we take the trade based on previous candle, So ATR will be calculated from previous to previous candle
        atr =  self.get_atr(symbol, timeframe, start_candle=2)
        body =  self.wrapper.pre_candle_body(symbol, timeframe)
        ratio = round(body/atr, 3)
        return ratio

    def get_pivot_levels(self, symbol:str, timeframe:int) -> Tuple[Signal, Signal]:
        """
        Identifies potential support and resistance levels based on recent price behavior.

        Parameters:
        - symbol (str): The trading symbol for the financial instrument.
        - timeframe (str): The timeframe for historical price data (e.g., 'M1', 'H1', 'D1').

        Returns:
        dict: A dictionary containing identified support and resistance levels.
            Example:
            {
                'support': [support_level1, support_level2, ...],
                'resistance': [resistance_level1, resistance_level2, ...]
            }

        The function analyzes recent price behavior by examining the highs and lows of the past three candles.
        It identifies potential resistance levels when the difference between the high of the middle candle
        and the highs of the adjacent candles is greater than 3 times the spread. Similarly, it identifies
        potential support levels when the difference between the low of the middle candle and the lows of
        the adjacent candles is greater than 3 times the spread.

        The function further filters out levels that intersect with previous candles to provide clean support
        and resistance levels.

        Note: The function relies on a helper function, `match_timeframe`, and assumes the existence of
        another helper function, `is_number_between`.

        :param symbol: Trading symbol for the financial instrument
        :param timeframe: Timeframe for recent price data
        :return: A dictionary with 'support' and 'resistance' levels
        """
        start_reference_bar = 1

        # If does the mid values intersect with previous 5 bars
        # get past 5 candles and start from prevous second candle
        past_candles = self.wrapper.get_candles_by_index(symbol=symbol, timeframe=timeframe, candle_look_back=start_reference_bar)
        spread = self.prices.get_spread(symbol=symbol)

        # Define a function to compare three rows
        def compare_three_rows(window, column) -> bool:
            # Extract values of each row in the window
            start_candle = window.iloc[0]
            middle_candle = window.iloc[1]
            end_candle = window.iloc[2]

            if column == "high" and  ((middle_candle - end_candle) > spread) and ((middle_candle - start_candle) > spread):
                return True
            
            if column == "low" and ((end_candle - middle_candle) > spread) and ((start_candle - middle_candle) > spread):
                return True
            
            return False
        
        if past_candles.empty:
            print(f"DF is empty: {symbol}")
            return None, None

        past_candles['is_resistance'] = past_candles['high'].rolling(window=3).apply(lambda x: compare_three_rows(x, "high"), raw=False)
        past_candles['is_support'] = past_candles['low'].rolling(window=3).apply(lambda x: compare_three_rows(x, "low"), raw=False)
        past_candles = past_candles.reset_index()
        past_candles["is_resistance"] = past_candles["is_resistance"].shift(-1)
        past_candles["is_support"] = past_candles["is_support"].shift(-1)

        pivot_high = None
        pivot_low = None

        resistance_levels = past_candles[past_candles["is_resistance"] == 1][["index", "high"]]
        resistance_levels = dict(zip(resistance_levels['index'], resistance_levels['high']))

        support_levels = past_candles[past_candles["is_support"] == 1][["index", "low"]]
        support_levels = dict(zip(support_levels['index'], support_levels['low']))

        # Based on the loop, The most recent near to the current time will overwrite all the previous pivot levels
        for index, level in resistance_levels.items():
            upcoming_levels = past_candles["high"].tolist()[index+1:]
            validator = []
            for i in upcoming_levels:
                if level > i:
                    validator.append(True)
                else:
                    validator.append(False)
            
            # All the candles which comes after a pivot should have higher highs compared to pivot
            if all(validator) and len(validator) > 0:
                pivot_high = Signal(reference="PVH", level=level, break_bar_index=index)

        # Based on the loop, The most recent near to the current time will overwrite all the previous pivot levels
        for index, level in support_levels.items():
            upcoming_levels = past_candles["low"].tolist()[index+1:]
            validator = []
            for i in upcoming_levels:
                if level < i:
                    validator.append(True)
                else:
                    validator.append(False)
            
            # All the candles which comes after a pivot should have lower lows compared to pivot
            if all(validator) and len(validator) > 0:
                pivot_low = Signal(reference="PVL", level=level, break_bar_index=index)
        
        return pivot_high, pivot_low
        
    def is_number_between(self, number, lower_limit, upper_limit):
        if lower_limit > upper_limit:
            return lower_limit > number > upper_limit
        else:
            return lower_limit < number < upper_limit

    def get_king_of_levels(self, symbol, timeframe, start_reference_bar=2) -> Dict[str, List[Signal]]:
        highs = []
        lows = []
        hod, lod = self.get_current_day_levels(symbol=symbol, timeframe=timeframe, start_reference_bar=start_reference_bar)

        if hod:                
            highs.append(hod)
        
        if lod:
            lows.append(lod)
        
        # if config.local_ip == "172_16_27_128":
        #     pvh, pvl = self.get_pivot_levels(symbol=symbol, timeframe=timeframe)
            
        #     # Only add when pivot level is lower than the high of the day, If pivot is higher then it would be covered by HOD
        #     if pvh and (pvh.level < hod.level):
        #         highs.append(pvh)
            
        #     # Only add when pivot level is high than the low of the day, If pivot is lower then it would be covered by LOD
        #     if pvl and (pvl.level > lod.level):
        #         lows.append(pvl)

        return {"resistance": highs, "support": lows}

if __name__ == "__main__":
    indi_obj = Indicators(wrapper=Wrapper(), prices=Prices())
    import sys
    symbol = sys.argv[1]
    timeframe = int(sys.argv[2])
    # start_reference = int(sys.argv[3])
    # print("ATR", indi_obj.get_atr(symbol, timeframe, 2))
    # print("Body", indi_obj.wrapper.pre_candle_body(symbol, timeframe))
    # print("Ratio", indi_obj.candle_move_ratio(symbol, timeframe))
    # print(indi_obj.get_previous_day_levels(symbol, timeframe))
    # print(indi_obj.get_time_based_levels(symbol=symbol, timeframe=timeframe, candle_start_hour=0, candle_end_hour=9))
    # print(indi_obj.solid_open_bar(symbol, timeframe))
    # print("OFF MARKET LEVELS", indi_obj.get_off_market_levels(symbol))
    # print("KING LEVELS", indi_obj.get_king_of_levels(symbol, timeframe, start_reference))
    # print("PIVOT", indi_obj.get_pivot_levels(symbol=symbol, timeframe=timeframe))
    # print(indi_obj.get_three_candle_strike(symbol=symbol, timeframe=timeframe))
    # print(indi_obj.get_three_candle_exit(symbol))
    # print(indi_obj.sma_direction(symbol=symbol, timeframe=60*4))
    # print(indi_obj.get_candle_cross_sma(symbol=symbol, sma_crossing=timeframe))
    # print(indi_obj.get_two_candle_strike(symbol=symbol, timeframe=timeframe))
    print(indi_obj.bollinger_bands(symbol=symbol, timeframe=timeframe, window_size=20))
