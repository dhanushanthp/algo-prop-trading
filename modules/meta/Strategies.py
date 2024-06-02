from modules.common.Directions import Directions
from modules.meta.wrapper import Wrapper
from modules.meta.Indicators import Indicators


class Strategies:
    def __init__(self, wrapper:Wrapper, indicators:Indicators):
        self.wrapper:Wrapper = wrapper
        self.indicators:Indicators = indicators

    def get_three_candle_strike(self, symbol, timeframe=60, start_candle=1) -> Directions:
        """
        Determines the direction of a three-candle with given conditions

        Args:
            self: The instance of the class.
            symbol: The symbol to analyze.
            timeframe (int, optional): The timeframe for analyzing candles. Defaults to 60.

        Returns:
            Directions or None: The direction of the three-candle strike pattern (LONG or SHORT) if identified, otherwise None.
        """
        previous_bars = self.wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=start_candle, n_candles=4)

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
    
    def get_dtop_dbottom(self, symbol:str, timeframe:int=60) -> Directions:
        """
        Double Top and Double Bottom
        """
        previous_bars = self.wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=1, n_candles=6)
        first_3_bars = previous_bars.head(3)
        last_3_bar = previous_bars.tail(3)

        spread = self.wrapper.get_spread(symbol=symbol)

        def is_higher_pivot(data):
            first_bar = data.iloc[0]["high"]
            second_bar = data.iloc[1]["high"]
            third_bar = data.iloc[2]["high"]

            if first_bar < second_bar and second_bar > third_bar and abs(first_bar-second_bar) > spread and abs(second_bar-third_bar) > spread:
                return True
            
        def is_lower_pivot(data):
            first_bar = data.iloc[0]["low"]
            second_bar = data.iloc[1]["low"]
            third_bar = data.iloc[2]["low"]

            if first_bar > second_bar and second_bar < third_bar and abs(first_bar-second_bar) > spread and abs(second_bar-third_bar) > spread:
                return True
        
        double_top = is_higher_pivot(first_3_bars) and is_higher_pivot(last_3_bar) and (first_3_bars.iloc[1]["high"] < last_3_bar.iloc[1]["high"])
        double_bottom = is_lower_pivot(first_3_bars) and is_lower_pivot(last_3_bar) and (first_3_bars.iloc[1]["low"] > last_3_bar.iloc[1]["low"])

        if double_top:
            return Directions.SHORT

        if double_bottom:
            return Directions.LONG
        
        return None


    def get_four_candle_pullback(self, symbol, timeframe=60, extrame=False) -> Directions:
        """
        Determines the directional change based on four-candle pattern analysis.

        Args:
            self: Instance of the class.
            symbol (str): Symbol for which the analysis is conducted.
            timeframe (int, optional): Timeframe for candlestick data. Defaults to 60.

        Returns:
            Directions or None: The predicted direction (Directions.LONG or Directions.SHORT) based on the candlestick pattern analysis,
            or None if no significant pattern is detected.

        This function analyzes a four-candle pattern to predict the directional change in the market.
        It retrieves two consecutive three-candle patterns and compares them to determine the directional change.
        The function returns the predicted direction based on the analysis, or None if no significant pattern is found.

        """
        three_cdl_strike = self.get_three_candle_strike(symbol=symbol, timeframe=timeframe, start_candle=2)
        
        prev_to_prev_candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=timeframe, i=2)
        prev_candle = self.wrapper.get_candle_i(symbol=symbol, timeframe=timeframe, i=1)
        prev_candle_direction = Directions.LONG if prev_candle["close"] > prev_candle["open"] else Directions.SHORT

        # sma_direction = self.indicators.sma_direction(symbol=symbol, timeframe=timeframe, reverse=True)
        
        if self.indicators.is_solid_candle(symbol=symbol, timeframe=timeframe, index=1, ratio=0.6):
            if (three_cdl_strike == Directions.LONG) and (prev_candle_direction == Directions.SHORT):
                if ((prev_candle["close"] < prev_to_prev_candle["low"]) and not extrame) or \
                    ((prev_candle["low"] < prev_to_prev_candle["low"]) and extrame):
                    return Directions.LONG

            if (three_cdl_strike == Directions.SHORT) and (prev_candle_direction == Directions.LONG):
                if ((prev_candle["close"] > prev_to_prev_candle["high"]) and not extrame) or \
                    ((prev_candle["high"] > prev_to_prev_candle["high"]) and extrame):
                    return Directions.SHORT
        
        return None

    
    def daily_high_low_breakouts(self, symbol:str, timeframe:int, min_gap:int=2) -> Directions:
        """
        Determines the breakout direction based on the daily high and low levels.

        Args:
            symbol (str): The symbol for which to calculate the breakout.
            timeframe (int): The timeframe for the candlestick data.
            min_gap (int, optional): The minimum gap between the breakout candle and the previous swing high/low.
                                    Defaults to 2.

        Returns:
            Directions: The direction of the breakout, either LONG or SHORT.

        """
        high_of_day, low_of_day = self.indicators.get_current_day_levels(symbol=symbol, 
                                                                         timeframe=timeframe, 
                                                                         start_reference_bar=2)

        previous_candles = self.wrapper.get_todays_candles(symbol=symbol, 
                                                           timeframe=timeframe,
                                                           start_candle=1)
        
        if not previous_candles.empty and high_of_day and low_of_day:
            previous_candle = previous_candles.iloc[-1]
        
            if (previous_candle["low"] < high_of_day.level and previous_candle["close"] > high_of_day.level):
                candle_gap = previous_candle["index"] - high_of_day.break_bar_index
                if candle_gap > min_gap:
                    return Directions.LONG
        
            if (previous_candle["high"] > low_of_day.level and previous_candle["close"] < low_of_day.level):
                candle_gap = previous_candle["index"] - low_of_day.break_bar_index
                if candle_gap > min_gap:
                    return Directions.SHORT
                

    def daily_high_low_breakout_double_high_hit(self, symbol:str, timeframe:int, min_gap:int=2) -> Directions:
        """
        Determines the breakout direction based on a double high hit pattern.

        Args:
            symbol (str): The symbol for which to calculate the breakout.
            timeframe (int): The timeframe for the candlestick data.
            min_gap (int, optional): The minimum gap between the breakout candle and the previous swing high/low.
                                    Defaults to 2.

        Returns:
            Directions: The direction of the breakout, either LONG or SHORT.
            
        Note:
            This function identifies a double high hit pattern where both the current and previous candlesticks
            have lows below the high of the day and highs above the high of the day for a long breakout, or 
            highs above the low of the day and lows below the low of the day for a short breakout.
        """
        high_of_day, low_of_day = self.indicators.get_current_day_levels(symbol=symbol, 
                                                                         timeframe=timeframe, 
                                                                         start_reference_bar=3)

        previous_candles = self.wrapper.get_todays_candles(symbol=symbol,
                                                           timeframe=timeframe,
                                                           start_candle=1)

        if not previous_candles.empty and len(previous_candles) > 2 and high_of_day and low_of_day:
            last_2_candles = previous_candles.tail(2).copy()

            last_2_candles["lower_than_hod"] = last_2_candles["low"] < high_of_day.level
            last_2_candles["higher_than_hod"] = last_2_candles["high"] > high_of_day.level
            last_2_candles["closed_bull_cdl"] = last_2_candles["close"] > last_2_candles["open"]

            last_2_candles["lower_than_lod"] = last_2_candles["low"] < low_of_day.level
            last_2_candles["higher_than_lod"] = last_2_candles["high"] > low_of_day.level
            last_2_candles["closed_bear_cdl"] = last_2_candles["close"] < last_2_candles["open"]

            if all(last_2_candles["lower_than_hod"]) and all(last_2_candles["higher_than_hod"]) and all(last_2_candles["closed_bull_cdl"]):
                candle_gap = last_2_candles.iloc[0]["index"] - high_of_day.break_bar_index
                
                if candle_gap > min_gap:
                    return Directions.LONG
            
            if all(last_2_candles["lower_than_lod"]) and all(last_2_candles["higher_than_lod"]) and all(last_2_candles["closed_bear_cdl"]):
                candle_gap = last_2_candles.iloc[0]["index"] - low_of_day.break_bar_index
                
                if candle_gap > min_gap:
                    return Directions.SHORT
    

    def weekly_high_low_breakouts(self, symbol:str, timeframe:int, min_gap:int=2) -> Directions:
        """
        Determines breakout direction based on weekly high and low levels.

        Args:
            symbol (str): The symbol of the financial instrument.
            timeframe (int): The timeframe in minutes.
            min_gap (int, optional): Minimum gap in number of candles for the breakout to be considered significant. Default is 2.

        Returns:
            Directions: The direction of breakout (LONG for upward breakout, SHORT for downward breakout).

        Notes:
            This function relies on indicator data and current candle information to determine if the asset has broken out
            above the weekly high or below the weekly low with a significant gap.

        Raises:
            None

        Examples:
            To determine if there's a significant upward breakout for symbol 'AAPL' with a weekly timeframe:
            >>> direction = weekly_high_low_breakouts('AAPL', timeframe=10080)

        """
        if timeframe < 240:
            raise Exception(f"The trading candle should be more than 4 hour!, Given was {timeframe}")

        high_of_week, low_of_week = self.indicators.get_weekly_day_levels(symbol=symbol, timeframe=timeframe, most_latest_candle=1)
                                    
        current_candle = self.wrapper.get_weekly_candles(symbol=symbol, timeframe=timeframe, most_latest_candle=0).iloc[-1]
    
        if (current_candle["low"] < high_of_week.level and current_candle["close"] > high_of_week.level):
            candle_gap = current_candle["index"] - high_of_week.break_bar_index
            if candle_gap > min_gap:
                return Directions.LONG
    
        if (current_candle["high"] > low_of_week.level and current_candle["close"] < low_of_week.level):
            candle_gap = current_candle["index"] - low_of_week.break_bar_index
            if candle_gap > min_gap:
                return Directions.SHORT


if __name__ == "__main__":
    wrapper = Wrapper()
    from modules.meta.Prices import Prices
    import modules.meta.Currencies as curr
    indicators = Indicators(wrapper=wrapper, prices=Prices())
    strat_obj = Strategies(wrapper=wrapper, indicators=indicators)
    import sys
    strategy = sys.argv[1]
    batch = sys.argv[2]
    timeframe = int(sys.argv[3])  

    match strategy:
        case "3CDL_STK":
            # python modules\meta\Strategies.py 3CDL_STK y 60
            if batch == "y":
                for symbol in curr.master_currencies:
                    direction = strat_obj.get_three_candle_strike(symbol=symbol, timeframe=timeframe)
                    if direction:
                        print(symbol, ": ", direction)
            else:
                symbol = sys.argv[4]
                print(strat_obj.get_three_candle_strike(symbol=symbol, timeframe=timeframe))

        case "4CDL_REV":
            # python modules\meta\Strategies.py 4CDL_REV y 60
            if batch == "y":
                for symbol in curr.master_currencies:
                    direction = strat_obj.get_four_candle_pullback(symbol=symbol, timeframe=timeframe)
                    if direction:
                        print(symbol, ": ", direction)
            else:
                symbol = sys.argv[4]
                print(strat_obj.get_four_candle_pullback(symbol=symbol, timeframe=timeframe))

        case "4CDL_REV_EXT":
            # python modules\meta\Strategies.py 4CDL_REV_EXT y 60
            if batch == "y":
                for symbol in curr.master_currencies:
                    direction = strat_obj.get_four_candle_pullback(symbol=symbol, timeframe=timeframe, extrame=True)
                    if direction:
                        print(symbol, ": ", direction)
            else:
                symbol = sys.argv[4]
                print(strat_obj.get_four_candle_pullback(symbol=symbol, timeframe=timeframe))
        
        case "DLY_BRK":
            # python modules\meta\Strategies.py DLY_BRK y 60
            if batch == "y":
                for symbol in curr.master_currencies:
                    direction = strat_obj.daily_high_low_breakouts(symbol=symbol, timeframe=timeframe)
                    if direction:
                        print(symbol, ": ", direction)
            else:
                symbol = sys.argv[4]
                print(strat_obj.daily_high_low_breakouts(symbol=symbol, timeframe=timeframe))
        
        case "DLY_BRK_DOH":
            # python modules\meta\Strategies.py DLY_BRK_DOH y 60
            if batch == "y":
                for symbol in curr.master_currencies:
                    direction = strat_obj.daily_high_low_breakout_double_high_hit(symbol=symbol, timeframe=timeframe)
                    if direction:
                        print(symbol, ": ", direction)
            else:
                symbol = sys.argv[4]
                print(strat_obj.daily_high_low_breakout_double_high_hit(symbol=symbol, timeframe=timeframe))
        
        case "WEEKLY_BRK":
            # python modules\meta\Strategies.py WEEKLY_BRK y 60
            if batch == "y":
                for symbol in curr.master_currencies:
                    direction = strat_obj.weekly_high_low_breakouts(symbol=symbol, timeframe=timeframe)
                    if direction:
                        print(symbol, ": ", direction)
            else:
                symbol = sys.argv[4]
                print(strat_obj.weekly_high_low_breakouts(symbol=symbol, timeframe=timeframe))
        
        case "D_TOP_BOTTOM":
            # python modules\meta\Strategies.py WEEKLY_BRK y 60
            if batch == "y":
                for symbol in curr.master_currencies:
                    direction = strat_obj.get_dtop_dbottom(symbol=symbol, timeframe=timeframe)
                    if direction:
                        print(symbol, ": ", direction)
            else:
                symbol = sys.argv[4]
                print(strat_obj.get_dtop_dbottom(symbol=symbol, timeframe=timeframe))