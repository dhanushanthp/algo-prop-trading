import MetaTrader5 as mt5
from modules.meta import util
import pandas as pd
import pytz
from datetime import datetime, timedelta, time
from modules import config
from typing import Tuple
mt5.initialize()

class Wrapper:
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


    def get_spread(self, symbol) -> float:
        ask_price = mt5.symbol_info_tick(symbol).ask
        bid_price = mt5.symbol_info_tick(symbol).bid
        spread = ask_price - bid_price
        return spread

    def pre_candle_body(self, symbol, timeframe):
        previous_candle = self.get_previous_candle(symbol=symbol, timeframe=timeframe)
        body_size = abs(previous_candle["open"] - previous_candle["close"])
        return round(body_size, 5)
    
    def get_previous_candle(self, symbol, timeframe):
        """
        Returns:
        Object which contains time, open, close, high, low
        Can be accessed as dictioanry e.g obj["close"]
        """
        return mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), 1, 1)[-1]
    
    def get_candle_i(self, symbol, timeframe, i=0):
        """
        0: Current candle
        1: Previous candle
        2: 2 Bar behind from current candle (e.g. Day before yesterday)
        """
        return mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), i, 1)[-1]
    
    
    def get_current_candle(self, symbol, timeframe):
        """
        Returns:
        Object which contains time, open, close, high, low
        Can be accessed as dictioanry e.g obj["close"]
        """
        return mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), 0, 1)[-1]
    

    def get_all_active_positions(self):
        positions = mt5.positions_get()
        return pd.DataFrame(list(positions),columns=positions[0]._asdict().keys())

    
    def get_active_positions(self, today=False):
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
            # symbol = position.symbol
            stop_price = position.sl
            entry_price = position.price_open

            if position.type == 0:
                if stop_price < entry_price:
                    positions_with_risk += 1
            
            if position.type == 1:
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
        

    def get_heikin_ashi(self, symbol, timeframe):
        """
        Calculate Heikin-Ashi OHLC (Open-High-Low-Close) values from an OHLC DataFrame.

        Parameters:
        df (DataFrame): OHLC DataFrame with columns 'Open', 'High', 'Low', 'Close'.

        Returns:
        DataFrame: DataFrame containing Heikin-Ashi OHLC values with columns renamed to lowercase.
        """

        df = self.get_last_n_candles(symbol=symbol, timeframe=timeframe, n_candles=4)
        print(df[["open", "close", "low", "high"]])

        heikin_ashi_df = df[["open", "close", "low", "high"]].copy()
        
        heikin_ashi_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4        
        heikin_ashi_df['open'] = (df['close'].shift(1) + df['open'].shift(1)) / 2

        import numpy as np
        heikin_ashi_df['high'] = np.maximum(df['high'], df[['open', 'close']].iloc[:-1].max(axis=1))
        heikin_ashi_df['low'] = np.minimum(df['low'], df[['open', 'close']].iloc[:-1].min(axis=1))
        # heikin_ashi_df['high'] = df["high"]
        # heikin_ashi_df['low'] = df["low"]

        heikin_ashi_df["signal"] = heikin_ashi_df["close"] - heikin_ashi_df["open"]
        heikin_ashi_df["signal"] = heikin_ashi_df["signal"].apply(lambda x: "bullish" if x > 0 else "bearish")

        return heikin_ashi_df

if "__main__" == __name__:
    obj = Wrapper()
    import sys
    symbol = sys.argv[1]
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
    print(obj.any_remaining_trades(max_trades=11))
    print(obj.get_all_active_positions())

