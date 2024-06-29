import MetaTrader5 as mt5
from modules.meta import util
import pandas as pd
import pytz
from datetime import datetime, timedelta, time
from modules import config
from typing import Tuple
import numpy as np
from collections import deque
from typing import Dict
mt5.initialize()
import modules.meta.Currencies as curr

class Wrapper:
    def __init__(self):
        self.average_spreads:Dict[str, list] = dict()

    def _avg_spread(self, symbol:str, spread:float):
        """
        Updates the average spread for a given financial symbol.

        This function maintains a rolling average of the spread values for a specified symbol.
        If the symbol does not already exist in the `average_spreads` dictionary, it initializes
        a deque with a maximum length of 20 to store the spread values. The spread value is then
        appended to the deque for the given symbol.

        Args:
            symbol (str): The financial symbol (e.g., currency pair) for which the spread is being updated.
            spread (float): The spread value to be added to the rolling average.

        """
        if symbol not in self.average_spreads:
           self.average_spreads[symbol] = deque(maxlen=20)
        self.average_spreads[symbol].append(spread)

    def is_reasonable_spread(self, symbol:str, pips_threshold:int=15):
        """
        Determines if the current spread for a given financial symbol is reasonable.

        This function calculates the current spread for a specified symbol and updates the
        rolling average spread. It then checks if the spread is within a reasonable range
        based on predefined thresholds for different types of currency pairs. The function
        considers JPY pairs and other currencies separately, applying specific rounding and
        threshold rules.

        Args:
            symbol (str): The financial symbol (e.g., currency pair) to check the spread for.

        Returns:
            bool: True if the spread is reasonable, False otherwise.

        """
        spread = float(self.get_spread(symbol=symbol))
        self._avg_spread(symbol=symbol, spread=spread)
        if symbol in curr.master_jpy_pairs:
            spread = round(np.mean(self.average_spreads[symbol]), 3)
            pips = int(str(f"{spread:.3f}").split(".")[-1])
            if pips <= pips_threshold:
                return True
            else:
                print(symbol, pips)
        elif symbol in curr.master_currencies:
            spread = round(np.mean(self.average_spreads[symbol]), 5)
            pips = int(str(f"{spread:.5f}").split(".")[-1])
            if pips <= pips_threshold:
                return True
            else:
                print(symbol, pips)
        else:
            return True

    def get_candles_by_index(self, symbol:str, timeframe:int, candle_look_back:int=0):
        """
        Retrieves historical candle data for a specific symbol within a given index range.
        
         Parameters:
        - symbol (str): The symbol for which to retrieve candle data.
        - timeframe (str): The timeframe of the candles (e.g 15, 60, 120, 240 minutes)
        - candle_index_start (int): Start from initial bar index (includes), Which more close to current time, 0 will be the current bar, 1 will be previous to current bar
        """

        match timeframe:
            case 60:
                sel_hour = 1
                sel_min = 0
            case 15:
                sel_hour = 0
                sel_min = 15
            case 5:
                sel_hour = 0
                sel_min = 5
            case _:
                sel_hour = 0
                sel_min = 0

        current_gmt_time = util.get_current_time() + timedelta(hours=config.server_timezone)
        
        today = util.get_current_time()
        candle_start_time = datetime(int(today.year), int(today.month), int(today.day), 
                                        hour=sel_hour, minute=sel_min, tzinfo=pytz.timezone('Etc/GMT'))
        
        candles = mt5.copy_rates_range(symbol, util.match_timeframe(timeframe), candle_start_time, current_gmt_time)

        df = pd.DataFrame(candles)
        df = df.iloc[:-candle_look_back] if candle_look_back > 0 else df

        if df.empty:
            print(f"Empty DF! {symbol}")

        return df
    
    def get_last_n_candles(self, symbol:str, timeframe:int, start_candle:int=0, n_candles:int=1):
        """
        Retrieve the last `n_candles` candlestick data for a given symbol and timeframe.

        Parameters:
        ----------
        symbol : str
            The symbol (ticker) for which the candlestick data is to be retrieved.
        timeframe : int
            The timeframe for the candlesticks, typically represented as an integer
            (e.g., 1 for 1 minute, 5 for 5 minutes, etc.).
        start_candle : int, optional
            The starting position (offset) of the candle data to retrieve, with the default being 0,
            which means the most recent candle.
        n_candles : int, optional
            The number of candlesticks to retrieve, with the default being 1.

        Returns:
        -------
        pd.DataFrame
            A DataFrame containing the candlestick data, with each row representing a candle
            and columns typically including time, open, high, low, close, tick_volume, spread, and real_volume.

        Example:
        -------
        >>> get_last_n_candles("EURUSD", 1, 0, 10)
            time       open       high        low      close  tick_volume  spread  real_volume
        0  1618317120  1.17687  1.17698  1.17679  1.17683         143       0          0
        1  1618317180  1.17683  1.17690  1.17674  1.17676         168       0          0
        ...
        """
        return pd.DataFrame(mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), start_candle, n_candles))

    
    def get_candles_by_time(self, symbol:str, timeframe:int,candle_start_hour:int=0, candle_end_hour:int=9):
        """
        Defaulted to GBPUSD hours from 0 to 9
        - candle_index_start (int): Start time includes the bar
        - candle_index_end (int): End time includes the bar
        """
        current_gmt_time = util.get_current_time() + timedelta(hours=config.server_timezone)

        today = util.get_current_time()
        candle_start_time = datetime(int(today.year), int(today.month), int(today.day), 
                                        hour=candle_start_hour, minute=0, tzinfo=pytz.timezone('Etc/GMT'))
        
        candle_end_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day), 
                                        hour=candle_end_hour, minute=59, tzinfo=pytz.timezone('Etc/GMT'))
        
        candles = mt5.copy_rates_range(symbol, util.match_timeframe(timeframe), candle_start_time, candle_end_time)
        
        return pd.DataFrame(candles)
    
    def get_previous_day_candles_by_time(self, symbol:str, timeframe:int):
        """
        Defaulted to GBPUSD hours from 0 to 9
        - candle_index_start (int): Start time includes the bar
        - candle_index_end (int): End time includes the bar
        """

        current_gmt_time = util.get_current_time() + timedelta(hours=config.server_timezone)
        # Handle monday, previous trading day would be Friday
        # TODO Load the symbol last trading data and match to that date
        dynamic_day_delta = 1 if current_gmt_time.weekday() > 0 else 3
        current_gmt_time = current_gmt_time - timedelta(days=dynamic_day_delta)

        candle_start_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day), 
                                        hour=1, minute=0, tzinfo=pytz.timezone('Etc/GMT'))
        
        candle_end_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day), 
                                        hour=23, minute=59, tzinfo=pytz.timezone('Etc/GMT'))
        
        candles = mt5.copy_rates_range(symbol, util.match_timeframe(timeframe), candle_start_time, candle_end_time)
        
        return pd.DataFrame(candles)


    def get_spread(self, symbol:str) -> float:
        ask_price = mt5.symbol_info_tick(symbol).ask
        bid_price = mt5.symbol_info_tick(symbol).bid
        spread = ask_price - bid_price
        return spread

    def pre_candle_body(self, symbol, timeframe):
        previous_candle = self.get_previous_candle(symbol=symbol, timeframe=timeframe)
        body_size = abs(previous_candle["open"] - previous_candle["close"])
        return round(body_size, 5)
    

    def candle_i_body(self, symbol:str, timeframe:int, candle_index:int):
        previous_candle = self.get_candle_i(symbol=symbol, timeframe=timeframe, i=candle_index)
        body_size = abs(previous_candle["open"] - previous_candle["close"])
        return body_size
    
    def most_recent_date(self, symbol, timeframe):
        """
        Finds the most recent date for a given symbol and timeframe.

        Parameters:
        - symbol (str): The symbol for which to find the most recent date.
        - timeframe (str): The timeframe to consider for the search.

        Returns:
        - most_recent_date (datetime.date): The most recent date in the specified timeframe for the given symbol.
        """
        find_most_recent_candle = self.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=0, n_candles=2)
        find_most_recent_candle["time"] = find_most_recent_candle["time"].apply(lambda x: util.get_traded_time(epoch=x))
        most_recent_date = find_most_recent_candle["time"].max().date()
        return most_recent_date
    
    
    def get_todays_candles(self, symbol:str, timeframe:int, start_candle:int) -> pd.DataFrame:
        """
        Retrieve today's candles for a given symbol and timeframe, up to the most recent candle.

        Args:
            symbol (str): The symbol for which to retrieve candles.
            timeframe (int): The timeframe (in minutes) of the candles.
            start_candle (int): The index of the most recent candle.

        Returns:
            pd.DataFrame: DataFrame containing today's candles for the specified symbol and timeframe.
        """
        if timeframe == 15:
            n_candles = 4*24
        elif timeframe == 60:
            n_candles = 24
        elif timeframe == 30:
            n_candles = 2*24
        else:
            raise Exception("Timeframe based candles are not defined!")
        
        last_24_hour_candles = self.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=start_candle, n_candles=n_candles)

        if not last_24_hour_candles.empty:
            last_24_hour_candles["time"] = last_24_hour_candles["time"].apply(lambda x: util.get_traded_time(epoch=x))
            last_24_hour_candles["date"] = last_24_hour_candles["time"].apply(lambda x: x.date())

            most_recent_date = self.most_recent_date(symbol, timeframe)

            todays_candles:pd.DataFrame = last_24_hour_candles[last_24_hour_candles["date"] == most_recent_date].copy()
            todays_candles = todays_candles.reset_index(drop=True).reset_index()

            return todays_candles

        return pd.DataFrame()
    
    def get_latest_bar_hour(self, symbol:str, timeframe:int):
        todays_bars = self.get_todays_candles(symbol=symbol, timeframe=timeframe, start_candle=0)
        try:
            # Some cases the br is not getting loaded
            latest_bar:datetime = todays_bars.iloc[-1]["time"]
        except IndexError:
            return -1

        return latest_bar.hour
    
    def get_weekly_candles(self, symbol:str, timeframe:int, most_latest_candle:int):
        """
        Retrieves weekly based candles for a given symbol and timeframe up to the specified most recent candle.

        Args:
            symbol (str): The symbol for which to retrieve the candles.
            timeframe (str): The timeframe for which to retrieve the candles (e.g., '1h', '4h', '1d').
            most_latest_candle (int): The index of the most recent candle.

        Returns:
            pd.DataFrame: A DataFrame containing the weekly candles up to the most recent candle.
                The DataFrame includes columns such as 'time', 'open', 'high', 'low', 'close', 'volume',
                and may also include additional columns depending on the source of the data.

        Notes:
            This function calculates the number of candles to retrieve based on the current time,
            finds the date of the last Sunday using utility functions from the `util` module,
            and fetches the relevant candles using the `get_last_n_candles` method of the `wrapper` object.
            It then filters the candles to include only those after the last Sunday and returns the result.

        """
        current_time = util.get_current_time()
        candle_look_back = (current_time.weekday() + 2) * 6
        last_sunday = util.get_last_sunday()
        previous_bars = self.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=most_latest_candle, n_candles=candle_look_back)
        previous_bars["time"] = previous_bars["time"].apply(lambda x: util.get_traded_time(epoch=x))
        previous_bars = previous_bars[previous_bars["time"] > last_sunday].copy().reset_index(drop=True).reset_index()
        return previous_bars
    

    def get_previous_candle(self, symbol, timeframe):
        """
        Retrieves the previous candlestick data for a given symbol and timeframe.

        Args:
        symbol (str): The symbol for which to retrieve candlestick data.
        timeframe (str): The timeframe for the candlestick data, e.g., 'M1', 'H1', 'D1'.

        Returns:
        dict: A dictionary containing the candlestick data with keys:
            - 'time': Timestamp of the candlestick.
            - 'open': Opening price of the candlestick.
            - 'close': Closing price of the candlestick.
            - 'high': Highest price reached during the candlestick period.
            - 'low': Lowest price reached during the candlestick period.

        Note:
        The returned object can be accessed as a dictionary, e.g., obj["close"].

        Raises:
        Exception: If unable to retrieve candlestick data.

        Example:
        >>> obj = YourClass()
        >>> candle_data = obj.get_previous_candle('EURUSD', 'M5')
        >>> print(candle_data['close'])
        1.12345
        """
        return mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), 1, 1)[-1]
    

    def get_candle_i(self, symbol, timeframe, i=0):
        """
        Retrieves candlestick data for a specific candle relative to the current time.

        Args:
        symbol (str): The symbol for which to retrieve candlestick data.
        timeframe (str): The timeframe for the candlestick data, e.g., 'M1', 'H1', 'D1'.
        i (int, optional): The index of the candle relative to the current time.
            - 0: Current candle.
            - 1: Previous candle.
            - 2: Two candles behind the current candle (e.g., two days ago).

        Returns:
        dict: A dictionary containing the candlestick data for the specified candle with keys:
            - 'time': Timestamp of the candlestick.
            - 'open': Opening price of the candlestick.
            - 'close': Closing price of the candlestick.
            - 'high': Highest price reached during the candlestick period.
            - 'low': Lowest price reached during the candlestick period.

        Note:
        The returned object can be accessed as a dictionary, e.g., obj["close"].

        Raises:
        Exception: If unable to retrieve candlestick data.

        Example:
        >>> obj = YourClass()
        >>> # Retrieve data for the previous candle
        >>> candle_data = obj.get_candle_i('EURUSD', 'M5', 1)
        >>> print(candle_data['close'])
        1.12345
        """
        return mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), i, 1)[-1]
    
    
    def get_current_candle(self, symbol, timeframe):
        """
        Returns:
        Object which contains time, open, close, high, low
        Can be accessed as dictioanry e.g obj["close"]
        """
        return mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), 0, 1)[-1]
    

    def get_all_active_positions(self, raw:bool=False):
        """
        Retrieves all active trading positions.

        This method fetches all currently active positions from the MetaTrader 5 platform. By default, it returns a pandas
        DataFrame containing the positions. If the `raw` parameter is set to True, it returns the raw list of positions.

        Args:
            raw (bool, optional): If True, returns the raw list of positions. If False, returns a pandas DataFrame. Default is False.

        Returns:
            list or pandas.DataFrame: A list of positions if `raw` is True, otherwise a pandas DataFrame containing the positions.
        """
        positions = mt5.positions_get()
        if raw:
            return list(positions)
        else:
            if len(positions) > 0:
                return pd.DataFrame(list(positions),columns=positions[0]._asdict().keys())

            return pd.DataFrame()
    
    
    
    
    def limit_trades_by_same_timeframe(self, timeframe:int) -> list:
        """
        Retrieves symbols for trades limited by the same hour timeframe.

        Args:
            self: The instance of the class.
            timeframe (int): The timeframe for considering trades.

        Returns:
            list: A list of symbols restricted by the same hour timeframe.
        """
        today_trade = self.get_todays_trades()
        _, hour, _ = util.get_current_day_hour_min()
        
        if not today_trade.empty:
            only_entry_trades = today_trade[today_trade["entry"] == 0].copy()
        
            if not only_entry_trades.empty:
                only_entry_trades["hour"] = only_entry_trades["time"].apply(lambda x: util.get_traded_time(epoch=x).hour)

                # Only consider same hour trade as restricted trade
                restricted_positions = only_entry_trades[only_entry_trades["hour"] == hour]

                return restricted_positions["symbol"].unique()

        return []

    
    def get_active_positions(self, today=False) -> list:
        """
        List all the symbols which are in trade
        """
        
        live_symbols = []
        if today:
            today_date = util.get_current_time().strftime("%Y-%m-%d")
            for i in mt5.positions_get():
                symbol = i.symbol
                traded_date = util.get_traded_time(i.time).strftime("%Y-%m-%d")
                if today_date == traded_date:
                    live_symbols.append(symbol)
            
            return live_symbols

        return list(set([i.symbol for i in mt5.positions_get()]))
    

    def get_existing_pending_orders(self, turtle=False) -> Tuple[list, list]:
        """
        List all the symbols which are in trade
        """
        active_orders = mt5.orders_get()

        canceling_orders = []
        considered_active_orders = [] # So

        # Cancell all pending orders regadless of trial or real
        for active_order in active_orders:
            entry_time = util.get_traded_time(active_order.time_setup)
            current_time  = util.get_current_time()

            entry_date = entry_time.strftime("%Y-%m-%d")
            current_date = current_time.strftime("%Y-%m-%d")

            entry_hour = entry_time.hour
            current_hour = current_time.hour

            # If waiting trade is not from same day then cancel
            if entry_date != current_date:
                canceling_orders.append(active_order)

            if turtle:
                # Cancel the order on next candle if it's not filled
                if current_hour - entry_hour >= 1:
                    canceling_orders.append(active_order)    

            # If Order waits more than 8 hours, then exist
            # if current_hour - entry_hour > 3:
            #     canceling_orders.append(active_order)

            if current_hour - entry_hour < 1:
                considered_active_orders.append(active_order.symbol)
            
        return canceling_orders, considered_active_orders    


    def get_todays_trades(self, us_market_seperator=False) -> pd.DataFrame:
        """
        This include entry and exit position of a trade
        """

        server_date = util.get_current_time()

        # Generate off market hours high and lows
        start_time = datetime(int(server_date.year), int(server_date.month), int(server_date.day), 
                                hour=0, minute=0, tzinfo=pytz.timezone('Etc/GMT'))
        
        tm_zone = pytz.timezone('Etc/GMT')
        end_time = datetime.now(tm_zone) + timedelta(hours=config.server_timezone)

        position_deals = mt5.history_deals_get(start_time,  end_time)

        if len(position_deals) > 0:
            df = pd.DataFrame(position_deals, columns=position_deals[0]._asdict().keys())
            return df
        
        # return empty dataframe
        return pd.DataFrame()
    

    def get_traded_symbols(self):
        trades = self.get_todays_trades()
        
        if trades.empty:
            return True
        
        # Number of positions based on the trades, Not on the symbols
        entry_positions = trades[trades["entry"]==0]
        entry_positions["code"] = entry_positions["symbol"] + "-" + entry_positions["entry"]

        return entry_positions["code"].tolist()


    def any_remaining_trades(self, max_trades=10):
        """
        Restrict the daily trade count to a maximum number of entries, determined by 
        considering past trades and existing open positions. Additionally, any losses 
        incurred from previous trades will impact the maximum allowable trades for a given day.
        """
        # Active trades with open risk
        num_active_positions = self.get_active_positions_with_risk()

        """
        Trades which has exit with negative profit. Even it could be from previous days,
        Since our daily loss limit has to consider losses of today
        """
        lost_positions = 0
        today_trades = self.get_todays_trades()
        if not today_trades.empty:
            exit_positions = today_trades[today_trades["entry"]==1]
            if not exit_positions.empty:
                nagative_positions = exit_positions[exit_positions["profit"] < 0]
                lost_positions = nagative_positions.shape[0]

        if (num_active_positions + lost_positions) < max_trades:
            return True
        
        return False
    
    
    def get_active_positions_with_risk(self) -> int:
        """
        Get number of active positions with risk (Not covered by break even stops)
        """
        positions_with_risk = 0
        existing_positions = mt5.positions_get()
        for position in existing_positions:
            stop_price = position.sl
            entry_price = position.price_open

            match position.type:
                case 0:
                    if stop_price < entry_price:
                        positions_with_risk += 1
                case 1:
                    if stop_price > entry_price:
                        positions_with_risk += 1
        
        return positions_with_risk
    
    
    def addtional_trade_buffer(self, parallel_positions = 10):
        """
        Dynamically change the max trades per day based on the risk free positions
        The risk free positions considered once after the stop moved to breake even or already exit positions with positive profit
        """
        # Already traded positions
        already_traded_today = 0
        trades = self.get_todays_trades()
        if not trades.empty:
            # Number of positions based on the trades, Not on the symbols
            already_traded_today = trades[trades["entry"]==0].shape[0]

        # active positions
        positions_with_risk = 0
        existing_positions = mt5.positions_get()
        for position in existing_positions:
            symbol = position.symbol
            stop_price = position.sl
            entry_price = position.price_open

            if position.type == 0:
                if stop_price < entry_price:
                    positions_with_risk += 1
            
            if position.type == 1:
                if stop_price > entry_price:
                    positions_with_risk += 1
        
        # Stopped Positions with negative
        exit_positions = trades[trades["entry"]==1]
        nagative_positions = exit_positions[exit_positions["profit"] < 0]
        lost_positions = nagative_positions.shape[0]

        total_positions_used = positions_with_risk + lost_positions

        possible_addtional_entries = already_traded_today + parallel_positions - total_positions_used

        return possible_addtional_entries
    
    def get_closed_pnl(self) -> float:
        """
        Calculate the closed profit and loss (PnL) for the current day.

        This function retrieves today's trades and calculates the total 
        profit and loss including commissions. If there are no trades 
        for today, it returns 0.0.

        Returns:
            float: The total closed PnL for today. This is the sum of all 
                profits and losses from today's trades plus the sum of 
                all commissions. If there are no trades today, returns 0.0.
        """
        today_trades = self.get_todays_trades()
        if not today_trades.empty:
            total_pnl = sum(today_trades["profit"])
            commision = sum(today_trades["commission"])
            return total_pnl + commision

        return 0.0
        

    def get_heikin_ashi(self, symbol:int, timeframe:int, start_candle:int=0, n_candles:int=10):
        """
        Calculate the Heikin-Ashi candlesticks for a given symbol and timeframe.

        This function retrieves the last `n_candles` for the specified `symbol` and `timeframe`, and computes
        the Heikin-Ashi values for each candlestick. Heikin-Ashi candlesticks are a variation of traditional
        candlesticks that aim to filter out market noise and provide a clearer picture of the market trend.

        Parameters:
        - symbol (int): The identifier for the financial instrument.
        - timeframe (int): The timeframe for the candlesticks (e.g., 1 for 1-minute candles, 5 for 5-minute candles).
        - n_candles (int): The number of candles to retrieve and process.

        Returns:
        - pd.DataFrame: A DataFrame containing the Heikin-Ashi candlestick data with columns ["time", "open", "high", "low", "close"].

        The DataFrame will have the same index as the original data retrieved from `get_last_n_candles` and include:
        - 'time': The time of the original candlestick.
        - 'open': The Heikin-Ashi open price.
        - 'high': The Heikin-Ashi high price.
        - 'low': The Heikin-Ashi low price.
        - 'close': The Heikin-Ashi close price.

        Example usage:
        ```python
        ha_df = trading_system.get_heikin_ashi(symbol=1, timeframe=5, n_candles=100)
        ```

        Note:
        - The first Heikin-Ashi open price is set to the first open price of the original data.
        - Heikin-Ashi calculations are as follows:
            - HA close = (Open + High + Low + Close) / 4
            - HA open = (Previous HA open + Previous HA close) / 2
            - HA high = max(High, HA open, HA close)
            - HA low = min(Low, HA open, HA close)
        """
        # df = self.get_last_n_candles(symbol=symbol, timeframe=timeframe, start_candle=start_candle, n_candles=n_candles)
        df = self.get_todays_candles(symbol=symbol, timeframe=timeframe, start_candle=start_candle)

        heikin_ashi_df = pd.DataFrame(index=df.index, columns=["time", "open", "high", "low", "close"])

        # Copy the time column
        heikin_ashi_df['time'] = df['time']

        # Calculate Heikin-Ashi values
        heikin_ashi_df['close'] = round((df['open'] + df['high'] + df['low'] + df['close']) / 4, 5)
        heikin_ashi_df['open'] = np.nan
        heikin_ashi_df['high'] = np.nan
        heikin_ashi_df['low'] = np.nan

        for i in range(len(df)):
            if i == 0:
                heikin_ashi_df.at[i, 'open'] = round(df.at[i, 'open'], 5)
            else:
                heikin_ashi_df.at[i, 'open'] = round((heikin_ashi_df.at[i-1, 'open'] + heikin_ashi_df.at[i-1, 'close']) / 2, 5)
            heikin_ashi_df.at[i, 'high'] = round(max(df.at[i, 'high'], heikin_ashi_df.at[i, 'open'], heikin_ashi_df.at[i, 'close']), 5)
            heikin_ashi_df.at[i, 'low'] = round(min(df.at[i, 'low'], heikin_ashi_df.at[i, 'open'], heikin_ashi_df.at[i, 'close']), 5)

        return heikin_ashi_df



if "__main__" == __name__:
    obj = Wrapper()
    import sys
    # symbol = sys.argv[1]
    # index = int(sys.argv[2])
    # timeframe = int(sys.argv[2])
    # timeframe = int(sys.argv[2])
    # start_hour = int(sys.argv[3])
    # end_hour = int(sys.argv[4])
    # print(obj.get_current_candle(symbol=symbol, timeframe=timeframe))
    # print(obj.get_previous_candle(symbol=symbol, timeframe=timeframe))
    # print(obj.get_existing_symbols(today=True))
    # print(obj.get_existing_pending_orders())
    # print(obj.get_todays_trades())
    # print(obj.pre_candle_body(symbol, timeframe))
    # print(obj.get_spread(symbol))
    # print(obj.get_candles_by_time(symbol, timeframe, start_hour, end_hour))
    # print(obj.get_candles_by_index(symbol=symbol, timeframe=timeframe, candle_look_back=start_hour))
    # print(obj.get_heikin_ashi(symbol=symbol, timeframe=60))
    # print(obj.get_traded_symbols())
    # print(obj.any_remaining_trades(max_trades=11))
    # print(obj.get_all_active_positions())
    # print(obj.candle_i_body(symbol=symbol, timeframe=60, candle_index=int(index)))
    # print(obj.get_weekly_candles(symbol=symbol, timeframe=240, most_latest_candle=0))
    # print(obj.get_todays_candles(symbol=symbol, timeframe=60, start_candle=index))
    # print(obj.get_latest_bar_hour(symbol=symbol, timeframe=index))
    # print(obj.get_closed_pnl())

    from modules.meta import Currencies
    while True:
        for symbol in Currencies.get_major_symbols():
            print(symbol, obj.is_reasonable_spread(symbol=symbol))
        print("\n\n\n")
        import time
        time.sleep(15)
    

