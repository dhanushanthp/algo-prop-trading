import MetaTrader5 as mt5
from modules.meta import util
import pandas as pd
import pytz
from datetime import datetime, timedelta, time
from modules import config
mt5.initialize()

class Wrapper:
    def __init__(self) -> None:
        pass

    
    def get_candles_by_index(self, symbol:str, timeframe:int, candle_look_back:int=0):
        """
        Retrieves historical candle data for a specific symbol within a given index range.
        
         Parameters:
        - symbol (str): The symbol for which to retrieve candle data.
        - timeframe (str): The timeframe of the candles (e.g 15, 60, 120, 240 minutes)
        - candle_index_start (int): Start from initial bar index (includes), Which more close to current time, 0 will be the current bar, 1 will be previous to current bar

        """

        if timeframe == 60:
            sel_hour = 1
            sel_min = 0
        elif timeframe == 15:
            sel_hour = 0
            sel_min = 15
        elif timeframe == 5:
            sel_hour = 0
            sel_min = 5
        else:
            sel_hour = 0
            sel_min = 0

        current_gmt_time = util.get_current_time() + timedelta(hours=config.server_timezone)

        candle_start_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day), 
                                        hour=sel_hour, minute=sel_min, tzinfo=pytz.timezone('Etc/GMT'))
        
        candles = mt5.copy_rates_range(symbol, util.match_timeframe(timeframe), candle_start_time, current_gmt_time)

        df = pd.DataFrame(candles)
        df = df.iloc[:-candle_look_back] if candle_look_back > 0 else df

        return df
    
    def get_candles_by_time(self, symbol:str, timeframe:int,candle_start_hour:int=0, candle_end_hour:int=9):
        """
        Defaulted to GBPUSD hours from 0 to 9
        - candle_index_start (int): Start time includes the bar
        - candle_index_end (int): End time includes the bar
        """
        current_gmt_time = util.get_current_time() + timedelta(hours=config.server_timezone)

        candle_start_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day), 
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
    

    def get_existing_symbols(self):
        """
        List all the symbols which are in trade
        """
        return list(set([i.symbol for i in mt5.positions_get()]))
    

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


if "__main__" == __name__:
    obj = Wrapper()
    import sys
    symbol = sys.argv[1]
    timeframe = int(sys.argv[2])
    start_hour = int(sys.argv[3])
    # end_hour = int(sys.argv[4])
    # print(obj.get_current_candle(symbol=symbol, timeframe=timeframe))
    # print(obj.get_previous_candle(symbol=symbol, timeframe=timeframe))
    # print(obj.get_existing_symbols())
    # print(obj.get_todays_trades())
    # print(obj.pre_candle_body(symbol, timeframe))
    # print(obj.get_spread(symbol))
    # print(obj.get_candles_by_time(symbol, timeframe, start_hour, end_hour))
    print(obj.get_candles_by_index(symbol=symbol, timeframe=timeframe, candle_look_back=start_hour))

