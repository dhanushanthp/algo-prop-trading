import numpy as np
import MetaTrader5 as mt5
mt5.initialize()
import modules.meta.util as util
from datetime import datetime,  timedelta
import pytz
from modules import config
import pandas as pd
from modules.common.Signal import Signal
from modules.common.Directions import Directions
from typing import Tuple, List, Dict
from modules.common import logme
from modules.meta.wrapper import Wrapper
from modules.meta.Prices import Prices
from modules.common.Directions import Directions
import modules.meta.Currencies as curr
from modules.common import files_util
import time

class Indicators:
    def __init__(self, wrapper: Wrapper, prices:Prices) -> None:
        self.wrapper = wrapper
        self.prices = prices
    
    def get_atr(self, symbol:str, timeframe:int, start_candle:int=0, n_atr:int=14) -> float:
        rates = self.wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=start_candle, n_candles=n_atr + 3)
        
        if rates.empty:
            return 0

        high = rates['high']
        low = rates['low']
        close = rates['close']

        true_range = np.maximum(high[1:] - low[1:], np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1]))
        atr = np.mean(true_range[-n_atr:])

        return round(atr, 5)
    
    def simple_moving_average(self, symbol:str, timeframe:int, n_moving_average:int=10) -> float:
        """
        Calculates the Simple Moving Average (SMA) of the closing prices for the last `n_moving_average` candles.

        The SMA is computed by summing the closing prices of the last `n_moving_average` candles and dividing by `n_moving_average`.

        Parameters:
        ----------
        symbol : str
            The trading symbol (e.g., 'AAPL', 'BTC/USD') for which the SMA is to be calculated.
        timeframe : int
            The timeframe of the candles (e.g., 1 for 1-minute candles, 60 for hourly candles).
        n_moving_average : int, optional
            The number of candles to include in the SMA calculation. Default is 10.

        Returns:
        -------
        float
            The computed Simple Moving Average (SMA) for the last `n_moving_average` candles.

        Raises:
        ------
        KeyError
            If the 'close' field is missing in the candle data returned by the wrapper.

        Notes:
        ------
        This method assumes the existence of a `wrapper.get_last_n_candles` method that retrieves the candle data. The 
        returned candle data is expected to be a dictionary with a 'close' key containing the closing prices.

        Example:
        -------
        >>> sma = obj.simple_moving_average(symbol='BTC/USD', timeframe=60, n_moving_average=5)
        >>> print(sma)
        43500.25
        """
        last_n_candles = self.wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=0, n_candles=n_moving_average)
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
        last_n_candles = self.wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=0, n_candles=window_size)
        close_prices = last_n_candles["close"]
        close_prices = np.array(close_prices)
        middle_band = np.convolve(close_prices, np.ones(window_size) / window_size, mode='valid')
        std_dev = np.std(close_prices[:window_size])  # Standard deviation of the initial window
        upper_band = middle_band + num_std_dev * std_dev
        lower_band = middle_band - num_std_dev * std_dev
        return upper_band[-1], lower_band[-1]


    def sma_direction(self, symbol:str, timeframe:int, short_ma:int=10, long_ma:int=20, reverse=False) -> Directions:
        """
        Determines the direction based on the Simple Moving Average (SMA) crossover strategy.

        Args:
            symbol (str): The trading symbol.
            timeframe (int): The time frame for the data.
            short_ma (int): The period for the short moving average. Defaults to 10.
            long_ma (int): The period for the long moving average. Defaults to 20.
            reverse (bool): If True, reverse the direction interpretation.

        Returns:
            Directions: The direction based on SMA crossover strategy.
        """
        short_sma = self.simple_moving_average(symbol=symbol, timeframe=timeframe, n_moving_average=short_ma)
        long_sma = self.simple_moving_average(symbol=symbol, timeframe=timeframe, n_moving_average=long_ma)

        if short_sma > long_sma:
            return Directions.LONG if not reverse else Directions.SHORT
        else:
            return Directions.SHORT if not reverse else Directions.LONG
    
    @staticmethod
    def has_three_consecutive_same_direction(lst):
        if len(lst) > 2:
            for i in range(len(lst) - 2):
                if lst[i] == lst[i+1] == lst[i+2]:
                    return True
        return False

    def get_three_candle_strike_data_points(self, symbol:str, timeframe:int, start_candle=1, ignore_body:bool=False) -> bool:
        """
        This function checks if there are three consecutive candles in the same direction for a given symbol and timeframe.

        Parameters:
        symbol (str): The trading symbol to analyze.
        timeframe (int): The timeframe for the candles.
        start_candle (int, optional): The starting candle index. Defaults to 1.
        ignore_body (bool, optional): Flag to ignore the candle body. Defaults to False.

        Returns:
        Directions: Indicates if there are three consecutive candles in the same direction.
        """
        previous_bars = self.wrapper.get_todays_candles(symbol=symbol, timeframe=timeframe, start_candle=start_candle)

        if not previous_bars.empty:
            previous_bars["direction"] = previous_bars["close"] - previous_bars["open"] > 0
            has_three_cdls = self.has_three_consecutive_same_direction(previous_bars["direction"].tolist())
            return has_three_cdls

    def higher_high_lower_low_reversal(self, symbol: str, timeframe: int, start_candle: int = 1, atr_split: int = 2, testing:bool=False) -> pd.DataFrame:
        """
        Identify higher high and lower low reversals based on ATR Range.
        
        Parameters:
        symbol (str): The trading symbol.
        timeframe (int): The timeframe for the candles.
        start_candle (int): The starting candle index.
        atr_split (int): The factor to split the ATR.
        
        Returns:
        pd.DataFrame: DataFrame containing the reversal signals.
        """
        
        # Get today's high and low
        hod, lod = self.get_today_high_low(symbol=symbol, start_candle=start_candle)
        
        # Calculate ATR and split it by the given factor
        split_atr = self.get_atr(symbol=symbol, timeframe=timeframe) / atr_split
        
        # Initialize a dictionary to track signals
        track_signals = {"time": [], "reversal_at": [], "range": [], "actualPeak":[]}
        
        # Get today's candles data
        todays_candles: pd.DataFrame = self.wrapper.get_todays_candles(symbol=symbol, timeframe=timeframe, start_candle=start_candle)
        
        # Iterate over each candle
        for index, each_candle in todays_candles.iterrows():
            # Update high of the day (HOD) and low of the day (LOD) up to the current candle for testing purpose, otherwise use the overall high and low of the day
            if testing:
                hod = todays_candles.iloc[0:index]["high"].max()
                lod = todays_candles.iloc[0:index]["low"].min()
            
            # Check for higher high reversal, If we are taking of the the open condition, then we need to have the max number trade limit
            top_range = hod - split_atr
            # Check for lower low reversal
            bottom_range = lod + split_atr
            
            """
            I was considering adding candle-based conditions, like having the open price fall below or above a certain range. 
            However, let's keep the indicator focused purely on price movements, without being tied to a specific candle timeframe. 
            For instance, if the timeframe is switched to 5 minutes, it would remain purely based on price movement. Every 15 seconds, 
            during each iteration, we would check the high and low values, without considering the candle's open or close prices.
            For now, we're sticking with a 15-minute timeframe to avoid too many checks
            """
            # This condition avoid the intersection of the ranges, Where the candle movement is less.
            if top_range > bottom_range:
                if each_candle["high"] > top_range and each_candle["low"] < top_range:
                    track_signals["time"].append(each_candle["time"])
                    track_signals["reversal_at"].append("high")
                    track_signals["range"].append(top_range)
                    track_signals["actualPeak"].append(hod)

                if each_candle["low"] < bottom_range and each_candle["high"] > bottom_range:
                    track_signals["time"].append(each_candle["time"])
                    track_signals["reversal_at"].append("low")
                    track_signals["range"].append(bottom_range)
                    track_signals["actualPeak"].append(lod)
        
        # Return the signals as a DataFrame
        return pd.DataFrame(track_signals)


    def get_three_cdl_reversal_points(self, symbol:str, timeframe:int=60, start_candle:int=1) -> pd.DataFrame:
        today_candles = self.wrapper.get_todays_candles(symbol=symbol, timeframe=timeframe, start_candle=start_candle)

        hod, lod = self.get_today_high_low(symbol=symbol, start_candle=2)

        df_dict = {"time":[], "type":[], "value":[], "peak_level":[]}

        if len(today_candles) >= 3:
            today_candles = today_candles.value_counts()
            for i in range(len(today_candles)-2):
                start_candle = today_candles[i].reset_index().iloc[0]
                start_cdl_body = start_candle["close"] - start_candle["open"]
                middle_candle = today_candles[i+1].reset_index().iloc[0]
                end_candle = today_candles[i+2].reset_index().iloc[0]
                end_cdl_body = end_candle["close"] - end_candle["open"]

                # RED and GREEN and END CDL HIGH > MIDD CDL HIGH and 
                if (start_cdl_body < 0) and (end_cdl_body > 0) and (end_candle["high"] > middle_candle["high"]) and (start_candle["high"] > middle_candle["high"]):
                    # print("LOWPOINT", middle_candle["time"] ,middle_candle["low"])
                    df_dict["time"].append(middle_candle["time"])
                    df_dict["type"].append("low")
                    df_dict["value"].append(middle_candle["low"])
                    df_dict["peak_level"].append(lod >= middle_candle["low"])

                
                if (start_cdl_body > 0) and (end_cdl_body < 0) and (end_candle["low"] < middle_candle["low"]) and (start_candle["low"] < middle_candle["low"]):
                    df_dict["time"].append(middle_candle["time"])
                    df_dict["type"].append("high")
                    df_dict["value"].append(middle_candle["high"])
                    df_dict["peak_level"].append(hod <= middle_candle["high"])
        
        return pd.DataFrame(df_dict)

    
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


    def get_historic_three_candle_strike(self, symbol, timeframe=60):
        return ""
    

    def is_solid_candle(self, symbol:str, timeframe:60, index:int, ratio:float=0.6):
        """
        Determines if a candle in a given symbol and timeframe is solid based on a specified ratio of body length to total length.

        Args:
            symbol (str): The symbol of the asset.
            timeframe (int): The timeframe of the candlestick data in minutes. Default is 60.
            index (int): The index of the candle in the historical data.
            ratio (float): The ratio threshold defining a solid candle. Default is 0.6.

        Returns:
            bool: True if the candle is solid, False otherwise.

        Example:
            is_solid = is_solid_candle("BTCUSD", timeframe=30, index=5, ratio=0.7)
        """
        candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=timeframe, i=index)
        body = abs(candle["close"] - candle["open"])
        total_length = candle["high"] - candle["low"]
        lenth_body_ratio = round(body/total_length, 1)
        if lenth_body_ratio >= ratio:
            return True
    

    def solid_candle_direction(self, symbol:str, timeframe:60, index:int, ratio:float=0.6):
        """
        Determines if a candle in a given symbol and timeframe is solid based on a specified ratio of body length to total length.

        Args:
            symbol (str): The symbol of the asset.
            timeframe (int): The timeframe of the candlestick data in minutes. Default is 60.
            index (int): The index of the candle in the historical data.
            ratio (float): The ratio threshold defining a solid candle. Default is 0.6.

        Returns:
            bool: True if the candle is solid, False otherwise.

        Example:
            is_solid = is_solid_candle("BTCUSD", timeframe=30, index=5, ratio=0.7)
        """
        candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=timeframe, i=index)
        body = abs(candle["close"] - candle["open"])
        total_length = candle["high"] - candle["low"]
        lenth_body_ratio = round(body/total_length, 1)
        if lenth_body_ratio >= ratio:
            if candle["close"] > candle["open"]:
                return Directions.LONG
            else:
                return Directions.SHORT
    

    def is_wick_candle(self, symbol, timeframe, index, ratio:float=0.4):
        """
        Determines if a candle is a 'wick candle' based on the body-to-total length ratio.

        A 'wick candle' is defined as a candle where the body length is less than or equal to
        a specified ratio of the total candle length.

        Parameters:
        symbol (str): The symbol for the financial instrument.
        timeframe (str): The timeframe of the candle (e.g., '1m', '5m', '1h').
        index (int): The index of the candle in the data series.
        ratio (float, optional): The maximum body-to-total length ratio to consider a candle as a 'wick candle'. Default is 0.4.

        Returns:
        bool: True if the candle is a 'wick candle', False otherwise.
        """
        candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=timeframe, i=index)
        body = abs(candle["close"] - candle["open"])
        total_length = candle["high"] - candle["low"]
        lenth_body_ratio = round(body/total_length, 1)
        if lenth_body_ratio <= ratio:
            return True
    
    def hammer_candle(self, symbol, timeframe, index):
        """
        Analyzes a specific candlestick to determine if it forms a hammer pattern, which can signal potential 
        market reversals. The method calculates the body, upper wick, and lower wick of the candlestick and 
        determines if it meets the criteria for a bullish or bearish hammer pattern.

        Args:
            symbol (str): The trading symbol (e.g., 'EURUSD') of the asset being analyzed.
            timeframe (str): The timeframe for the candlestick data (e.g., '1h', '4h', '1d').
            index (int): The index of the candlestick to analyze (0 for the most recent candlestick).

        Returns:
            Directions: An enumeration indicating the trade direction:
                - Directions.SHORT: If a bearish hammer pattern is detected.
                - Directions.LONG: If a bullish hammer pattern is detected.
                - None: If no hammer pattern is detected.
        """
        candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=timeframe, i=index)
        body = candle["close"] - candle["open"]
        spread = self.wrapper.get_spread(symbol=symbol)
        if abs(body) > spread:
            if body > 0:
                # bullish
                lower_wick = candle["open"] - candle["low"]
                upper_wick = candle["high"] - candle["close"]
            elif body < 0:
                # bearish
                lower_wick = candle["close"] - candle["low"]
                upper_wick = candle["high"] - candle["open"]
            else:
                lower_wick = upper_wick = None

            if lower_wick:
                if (upper_wick > 2* lower_wick) and (upper_wick > 2 * abs(body)):
                    return Directions.SHORT
                elif (lower_wick > 2 * upper_wick) and (lower_wick > 2 * abs(body)):
                    return Directions.LONG
    

    def get_three_candle_exit(self, symbol, wick_body_ratio=2, timeframe=60) -> bool:
        """
        Exist the position if candle is ranging for last 3 hours, which has longer wicks than the body
        """
        previous_bars = self.wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=1, n_candles=4)

        if len(previous_bars) >= 3:
            last_3_bars = previous_bars.tail(3).copy()
            last_3_bars["body_size"] = abs(last_3_bars["close"] - last_3_bars["open"])
            last_3_bars["wick_size"] = abs(last_3_bars["high"] - last_3_bars["low"]) - last_3_bars["body_size"]
            last_3_bars["ratio"] = last_3_bars["wick_size"]/last_3_bars["body_size"] # Calcullate the Ratio

            is_ranging = all(last_3_bars["ratio"] > wick_body_ratio)
            
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
                logme.log_it("INDICATOR").debug(f"OffMar, {symbol}, {start_time}, {end_time}")

            return None, None
        
        return None, None
    
    def get_current_day_levels(self, symbol, timeframe, start_reference_bar=2) -> Tuple[Signal, Signal]:
        """
        Retrieves the current day's high and low levels based on the provided symbol and timeframe.

        Parameters:
        - symbol (str): The symbol for which to retrieve levels.
        - timeframe (int): The timeframe for the candlesticks in minutes.
        - start_reference_bar (int): The index of the reference bar to start from (default is 2).

        Returns:
        - Tuple[Signal, Signal]: A tuple containing the signal for the day's high (HOD) and low (LOD),
        or (None, None) if data is not available.

        Example:
        ```
        hod_signal, lod_signal = get_current_day_levels("AAPL", 60, 2)
        ```
        """
        previous_bars = self.wrapper.get_todays_candles(symbol=symbol, timeframe=timeframe, start_candle=start_reference_bar)

        if not previous_bars.empty:
            off_hour_highs = Signal(reference="HOD", level=max(previous_bars["high"]), break_bar_index=previous_bars["high"].idxmax())
            off_hour_lows = Signal(reference="LOD", level=min(previous_bars["low"]), break_bar_index=previous_bars["low"].idxmin())
            return off_hour_highs, off_hour_lows

        return None, None

    def fib_retracement(self, high: float, low: float):
        # Fibonacci retracement levels
        fib_levels = [0.236, 0.382, 0.500, 0.618, 0.786]

        # Calculate the difference between high and low
        difference = high - low

        # Calculate the retracement levels
        retracement_levels = {f"{int(level*100)}": high - difference * level for level in fib_levels}

        return retracement_levels
        
    
    def get_today_high_low(self, symbol, start_candle=1) -> Tuple[float, float]:
        """
        Retrieves the highest and lowest prices for today's trading session for a given symbol.

        This function fetches today's candlestick data for the specified symbol with a 5-minute timeframe.
        It then adjusts the high and low prices of the first bar based on the opening and closing prices
        to ignore opening price fluctuations. Finally, it returns the maximum high and minimum low prices
        from the adjusted data.

        Parameters:
        symbol (str): The trading symbol for which to retrieve the high and low prices.

        Returns:
        Tuple[float, float]: A tuple containing the highest and lowest prices for today's trading session.
                            Returns (None, None) if no data is available.
        """
        previous_bars = self.wrapper.get_todays_candles(symbol=symbol, timeframe=5, start_candle=start_candle)
        if not previous_bars.empty:
            first_bar = previous_bars.iloc[0]
            # Ignore the opening price flutations by seeting the high and low to open and close prices.
            if first_bar["close"] > first_bar["open"]:
                previous_bars.loc[0, "low"] = previous_bars.loc[0, "open"]
                previous_bars.loc[0, "high"] = previous_bars.loc[0, "close"]
            else:
                previous_bars.loc[0, "high"] = previous_bars.loc[0, "open"]
                previous_bars.loc[0, "low"] = previous_bars.loc[0, "close"]
            
            return max(previous_bars["high"]), min(previous_bars["low"])

        return None, None
    
    def get_weekly_day_levels(self, symbol, timeframe, most_latest_candle=1) -> Tuple[Signal, Signal]:
        """
        Retrieves the weekly high and low levels for a given symbol and timeframe.

        Args:
            symbol (str): The symbol for which to retrieve the levels.
            timeframe (str): The timeframe for which to retrieve the levels (e.g., '1h', '4h', '1d').
            most_latest_candle (int, optional): The index of the most recent candle. Defaults to 1.

        Returns:
            Tuple[Signal, Signal]: A tuple containing two signals representing the weekly high and low levels.
                The signals are instances of the Signal class and include information about the reference,
                level, and break bar index.

        Notes:
            This function calculates the weekly high and low levels based on the candles available
            since the last Sunday up to the most recent candle specified by `most_latest_candle`.
            It utilizes utility functions from the `util` module, such as `get_current_time()`
            and `get_last_sunday()`, and accesses candle data using the `get_last_n_candles` method
            of the `wrapper` object.

        """
        previous_bars = self.wrapper.get_weekly_candles(symbol=symbol, timeframe=timeframe, most_latest_candle=most_latest_candle)

        if not previous_bars.empty:
            off_hour_highs = Signal(reference="HOW", level=max(previous_bars["high"]), break_bar_index=previous_bars["high"].idxmax())
            off_hour_lows = Signal(reference="LOW", level=min(previous_bars["low"]), break_bar_index=previous_bars["low"].idxmin())
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
        
    
    def candle_strength(self, symbol, timeframe, index, threshold=0.8):
        candle_body = self.wrapper.candle_i_body(symbol=symbol, timeframe=timeframe, candle_index=index)
        atr = self.get_atr(symbol=symbol, timeframe=timeframe, start_candle=index)

        if candle_body/atr > threshold:
            var = index, candle_body, atr, candle_body>atr, round(candle_body/atr, 2)
            print(var)
            return True, var

        return None, None

    def pullback_candle_breaks(self, symbol:str, timeframe:int=60, breakout_gap:int=3, breakout_candle_index:int=1) -> Tuple[Directions, int]:
        """
        Pulls back candle breaks within a specified timeframe.

        Parameters:
        - symbol (str): The symbol for which to pull back candle breaks.
        - timeframe (int): The timeframe for the candlesticks in minutes (default is 60).
        - breakout_gap (int): The number of candlesticks to skip for breakout (default is 3).
        - breakout_candle_index (int): The index of the breakout candle (default is 1).

        Returns:
        - Tuple[Directions, int]: A tuple containing the direction (LONG or SHORT) and the index of the break, or (None, None) if no break is found.

        Example:
        ```
        direction, break_index = pullback_candle_breaks("AAPL", 60, 3, 1)
        ```
        """
        
        match timeframe:
            case 60:
                # In last 24 hours
                n_candles = 24
            case 240:
                # In last 3 days 3x6
                n_candles = 18

        # Pick last 10 candles, Starting from previous candle
        previous_candles = self.wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=breakout_candle_index, n_candles=n_candles)
        previous_candles = previous_candles.iloc[::-1].reset_index(drop=True) # reverse the data

        # Previous candles, which is already close
        signal_check_candle = previous_candles.iloc[0]

        for i in range(breakout_gap, len(previous_candles) + 1):
            # Start checking the candles from previous to previous, it's 1, since our start candle is previous candle
            selected_candles = previous_candles.iloc[1: i]

            index_of_high = selected_candles['high'].idxmax()
            high_of_candels = selected_candles["high"].max()
            if signal_check_candle["close"] > high_of_candels:
                if index_of_high > 2:
                    return Directions.LONG, index_of_high
            
            low_of_candels = selected_candles["low"].min()
            index_of_low = selected_candles['high'].idxmax()
            if signal_check_candle["close"] < low_of_candels:
                if index_of_low > 2:
                    return Directions.SHORT, index_of_low
                
        return None, None

    def get_dominant_market_actual_direction(self, lookback=1) -> str:
        symbols = curr.get_symbols(symbol_selection="PRIMARY")
        # Ignore US500 and XAUUSD since they don't open at the time of forex open
        symbols = [i for i in symbols if i not in ["US500.cash", "XAUUSD"]]
        long_count = 0
        short_count = 0
        even_count = 0
        for symbol in symbols:
            if not self.wrapper.is_chart_upto_date(symbol=symbol):
                # If the chart is not update to then don't take the trade atleast for single symbol
                print(f"MISSING Symbol Chart, Dominant Direction: {symbol}")
                mt5.symbol_select(symbol, True)
                week_day = util.get_week_day()
                if week_day in [5, 6]:
                    print("Weekend Wait 1 Hour")
                    # Wait for 1 hour on weekends
                    time.sleep(60 * 60)
                    return "UNKNOWN"

                # On weekdays get the most update data
                time.sleep(10)
                return self.get_dominant_market_actual_direction(lookback=lookback)
            
            prev_candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=1440, i=lookback)
            prev_prev_candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=1440, i=lookback+1)

            prev_dir = "long" if prev_candle["close"] > prev_candle["open"] else "short"
            prev_prev_dir = "long" if prev_prev_candle["close"] > prev_prev_candle["open"] else "short"
            
            if prev_dir == prev_prev_dir== "long":
                long_count += 1
            
            if prev_dir == prev_prev_dir== "short":
                short_count += 1
            
            if prev_dir != prev_prev_dir:
                even_count += 1
        
        print(f"Long Count: {long_count}, Short Count: {short_count}, Even Count: {even_count}")
        
        if long_count > short_count:
            print(f"Long Confidence: {round(long_count/8, 2)}")
            return Directions.LONG
        elif short_count > long_count:
            print(f"Short Confidence: {round(short_count/8, 2)}")
            return Directions.SHORT
        else:
            if long_count > even_count:
                print(f"Even Long Confidence: {round(long_count/8, 2)}")
                return Directions.LONG
            elif short_count > even_count:
                print(f"Even Short Confidence: {round(short_count/8, 2)}")
                return Directions.SHORT
            else:
                print(f"Even Confidence: {round(even_count/8, 2)}")
                return Directions.LONG

    def get_dominant_direction(self, lookback=1, timeframe:int=1440) -> str:
        """
        Identify the potential direction of the market move.

        This method analyzes the direction of previous market movements to predict the potential direction of the market. 
        It compares the direction of two consecutive candles (previous and the one before it) to determine if the market is 
        more likely to continue in the same direction (BREAK) or reverse (REVERSE).

        Parameters:
        lookback (int): The number of previous days to look back. Default is 1, referring to the previous trading day. 
                        For example, if `lookback=1`, the method compares the previous day's candle to the candle of 
                        the day before the previous day (lookback+1).

        Returns:
        str: "BREAK" if the market direction is expected to continue in the same direction, "REVERSE" if the market direction 
            is expected to change.

        Example:
        >>> market_direction = instance.get_dominant_direction(lookback=1)
        >>> print(market_direction)
        "BREAK"

        Calculation:
        - The method loops through a list of symbols.
        - For each symbol, it retrieves the candle data for the given lookback period and the period before it.
        - It determines the direction of each candle (either "long" if the close price is higher than the open price, or "short" if the close price is lower than the open price).
        - It compares the directions of the two candles:
            - If the directions are the same (both "long" or both "short"), it increments the `break_count`.
            - If the directions are different (one "long" and the other "short"), it increments the `reverse_count`.
        - After looping through all symbols, the method returns "BREAK" if `break_count` is greater than `reverse_count`, indicating that the market is likely to continue in the same direction. Otherwise, it returns "REVERSE", indicating that the market is likely to change direction.
        """

        """
        This function fetches the previous PNLs data, checks if all values in 
        the 'rr' column are greater than 0, and then verifies if there's only 
        one unique strategy value that is 'REVERSE'. If both conditions are met, 
        it returns 'BREAK'.
        """
        # pnl_df = files_util.get_previous_pnls()
        # if pnl_df is not None:
        #     if all(pnl_df["rr"] > 0):
        #         unique_strategy = pnl_df["strategy"].unique()
        #         if len(unique_strategy) == 1 and unique_strategy == "REVERSE":
        #             print("Previous 3 REVERSE Win")
        #             return "BREAK"
        
        """
        Most of the days If it's monday then REVERSE works the best, So we manually overide the rule
        """
        # week_day = util.get_week_day()
        # if week_day == 0:
        #     print("Monday Reversal Manual Set")
        #     return "REVERSE"


        symbols = curr.get_symbols(symbol_selection="PRIMARY")
        # Ignore US500 and XAUUSD since they don't open at the time of forex open
        symbols = [i for i in symbols if i not in ["US500.cash", "XAUUSD"]]
        break_count = 0
        reverse_count = 0
        for symbol in symbols:
            if not self.wrapper.is_chart_upto_date(symbol=symbol):
                # If the chart is not update to then don't take the trade atleast for single symbol
                print(f"MISSING Symbol Chart, Dominant Direction: {symbol}")
                mt5.symbol_select(symbol, True)
                week_day = util.get_week_day()
                if week_day in [5, 6]:
                    print("Weekend Wait 1 Hour")
                    # Wait for 1 hour on weekends
                    time.sleep(60 * 60)
                    return "UNKNOWN"

                # On weekdays get the most update data
                time.sleep(10)
                return self.get_dominant_direction(lookback=lookback)
            
            prev_candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=timeframe, i=lookback)
            prev_prev_candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=timeframe, i=lookback+1)
            prev_dir = "long" if prev_candle["close"] > prev_candle["open"] else "short"
            prev_prev_dir = "long" if prev_prev_candle["close"] > prev_prev_candle["open"] else "short"
            if prev_dir == prev_prev_dir:
                break_count += 1
            else:
                reverse_count += 1

        if break_count > reverse_count:
            print(f"Break Confidence: {round(break_count/8, 2)}")
            return "BREAK"
        
        print(f"Reverse Confidence: {round(reverse_count/8, 2)}")
        return "REVERSE"


if __name__ == "__main__":
    indi_obj = Indicators(wrapper=Wrapper(), prices=Prices())
    import sys
    indicator = sys.argv[1]
    # start_reference = int(sys.argv[3])
    # print("ATR", indi_obj.get_atr(symbol, timeframe, 2))
    # print("Body", indi_obj.wrapper.pre_candle_body(symbol, timeframe))
    # print("Ratio", indi_obj.candle_move_ratio(symbol, timeframe))
    # print(indi_obj.get_previous_day_levels(symbol, timeframe))
    # print(indi_obj.get_time_based_levels(symbol=symbol, timeframe=timeframe, candle_start_hour=0, candle_end_hour=9))
    # print(indi_obj.solid_open_bar(symbol, timeframe))
    # print("OFF MARKET LEVELS", indi_obj.get_off_market_levels(symbol))
    # print("KING LEVELS", indi_obj.get_king_of_levels(symbol, timeframe, 1))
    # print("PIVOT", indi_obj.get_pivot_levels(symbol=symbol, timeframe=timeframe))
    # print(indi_obj.get_three_candle_exit(symbol))
    # print(indi_obj.sma_direction(symbol=symbol, timeframe=60*4))
    # print(indi_obj.get_candle_cross_sma(symbol=symbol, sma_crossing=timeframe))
    # print(indi_obj.get_two_candle_strike(symbol=symbol, timeframe=timeframe))
    # print(indi_obj.bollinger_bands(symbol=symbol, timeframe=timeframe, window_size=20))
    # print(indi_obj.pullback_candle_breaks(symbol=symbol, timeframe=timeframe))
    # print(indi_obj.hammer_candle(symbol=symbol, timeframe=60, index=timeframe))
    # print(indi_obj.get_weekly_day_levels(symbol=symbol, timeframe=240, most_latest_candle=0))

    match indicator:
        case "dominant_direction":
            # python modules/meta/Indicators.py dominant_direction AUDUSD
            print(indi_obj.get_dominant_market_actual_direction())

        case "body_ratio":
            symbol = sys.argv[2]
            timeframe = int(sys.argv[3])
            index = int(sys.argv[4])
            print(indi_obj.is_solid_candle(symbol=symbol, timeframe=timeframe, index=index))
        case "sma_direction":
            symbol = sys.argv[2]
            timeframe = int(sys.argv[3])
            index = int(sys.argv[4])
            print(indi_obj.sma_direction(symbol=symbol, timeframe=timeframe, reverse=True))
        case "daily_levels":
            """
            Test High and Low Of the Day
            """
            # python modules/meta/Indicators.py daily_levels AUDUSD 15
            symbol = sys.argv[2]
            timeframe = int(sys.argv[3])
            # index = int(sys.argv[4])
            previous_candle = indi_obj.wrapper.get_todays_candles(symbol=symbol,timeframe=60, start_candle=1).iloc[-1]
            hod, lod = indi_obj.get_current_day_levels(symbol=symbol, timeframe=60, start_reference_bar=0)
            print("PREV Candle", previous_candle)
            
            print("Today High/Low")
            print(indi_obj.get_today_high_low(symbol=symbol))

            print("HOD")
            print(hod)
            print(previous_candle["low"] < hod.level and previous_candle["close"] > hod.level)
            print(previous_candle["index"] - hod.break_bar_index)
            
            print("LOD")
            print(lod)
            print(previous_candle["high"] > lod.level and previous_candle["close"] < lod.level)
            print(previous_candle["index"] - lod.break_bar_index)
        
        case "solid_candle":
            symbol = sys.argv[2]
            timeframe = int(sys.argv[3])
            index = int(sys.argv[4])
            print(indi_obj.solid_candle_direction(symbol=symbol, timeframe=timeframe, index=index))
        
        case "other_candle":
            # python modules/meta/Indicators.py other_candle AUDUSD 15 1
            symbol = sys.argv[2]
            timeframe = int(sys.argv[3])
            index = int(sys.argv[4])
            print(indi_obj.hammer_candle(symbol=symbol, timeframe=timeframe, index=index))
            print(indi_obj.is_wick_candle(symbol=symbol, timeframe=timeframe, index=index))
        
        case "atr":
            symbol = sys.argv[2]
            timeframe = int(sys.argv[3])
            print(indi_obj.get_atr(symbol=symbol, timeframe=timeframe, start_candle=0))
        
        case "atr_ratio":
            # python modules/meta/Indicators.py atr_ratio AUDUSD
            symbol = sys.argv[2]
            atr_5 = indi_obj.get_atr(symbol=symbol, timeframe=5, start_candle=0, n_atr=12)
            atr_15 = indi_obj.get_atr(symbol=symbol, timeframe=15, start_candle=0)
            # atr_day = indi_obj.get_atr(symbol=symbol, timeframe=1440, start_candle=0)
            price = indi_obj.prices.get_exchange_price(symbol=symbol)
            # If the move is 0.05%
            factor_of_price = price/100 * 0.05
            print(f"5: {round(atr_5 , 4)}, 15: {round(atr_15, 4)}, 0.1% {round(factor_of_price, 5)}")
            print(f"15/5 {round(atr_15/atr_5, 2)}")
            print(f"5/0.1% {round(atr_5/factor_of_price, 3)}")
            print(f"15/0.1% {round(atr_15/factor_of_price, 3)}")
            print(atr_15/price * 100)
        
        case "3cdl_reversal":
            # python modules/meta/Indicators.py 3cdl_reversal AUDUSD 15
            symbol = sys.argv[2]
            timeframe = int(sys.argv[3])
            print(indi_obj.get_three_cdl_reversal_points(symbol=symbol, timeframe=timeframe))
            print(indi_obj.get_three_candle_strike_data_points(symbol=symbol, timeframe=timeframe))

        
        case "trade_direction":
            # python modules/meta/Indicators.py trade_direction
            # for i in range(0, 10):
            print(f"Today ", indi_obj.get_dominant_direction())
        
        case "high_low_range_hunt":
            # python modules/meta/Indicators.py high_low_range_hunt 15 2
            timeframe = int(sys.argv[2])
            split = int(sys.argv[3])

            # symbol = sys.argv[4]
            
            import modules.meta.Currencies as curr
            signals = {"symbol":[], "signal":[], "level":[]}
            for symbol in curr.get_symbols():
                peak_signals = indi_obj.higher_high_lower_low_reversal(symbol=symbol, timeframe=timeframe, atr_split=split, testing=True)

                if len(peak_signals) >= 2:
                    last_signal = peak_signals.iloc[-1]
                    previous_signal = peak_signals.iloc[-2]

                    if last_signal["reversal_at"] == previous_signal["reversal_at"] == "high" and last_signal["range"] == previous_signal["range"]:
                        signals["symbol"].append(symbol)
                        signals["signal"].append("SHORT")
                        signals["level"].append(last_signal["range"])
                    
                    if last_signal["reversal_at"] == previous_signal["reversal_at"] == "low" and last_signal["range"] == previous_signal["range"]:
                        signals["symbol"].append(symbol)
                        signals["signal"].append("LONG")
                        signals["level"].append(last_signal["range"])
            
            df = pd.DataFrame(signals)
            print(df.sort_values("symbol"))
        
        case "high_low_range_hunt_single":
            # python modules/meta/Indicators.py high_low_range_hunt_single 15 2 XAUUSD
            timeframe = int(sys.argv[2])
            split = int(sys.argv[3])
            symbol = sys.argv[4]
            peak_signals = indi_obj.higher_high_lower_low_reversal(symbol=symbol, timeframe=timeframe, atr_split=split, testing=True)
            peak_signals = peak_signals.map(lambda x: "" if x==False else x)
            print(peak_signals)
            last_signal = peak_signals.iloc[-1]
            previous_signal = peak_signals.iloc[-2]
            
            time_gap = last_signal["time"] - previous_signal["time"]
            print(time_gap.total_seconds() / 60)


                    
