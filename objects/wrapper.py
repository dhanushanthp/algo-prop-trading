import MetaTrader5 as mt5
from objects import util
import pandas as pd
import pytz
from datetime import datetime, timedelta, time
from modules import config
mt5.initialize()

class Wrapper:
    def __init__(self) -> None:
        pass

    
    def get_candles_by_index(self, symbol:str, candle_index_start:int, candle_index_end:int, timeframe:int):
        """
        Retrieves historical candle data for a specific symbol within a given index range.

        Parameters:
        - symbol (str): The symbol for which to retrieve candle data.
        - candle_index_start (int): Initial bar index, Which more close to current time.
        - candle_index_end (int): Number of bars, Get all pervious bars from 
        - timeframe (str): The timeframe of the candles (e.g 15, 60, 120, 240 minutes)

        Returns:
        - list of dict: A list of candle data represented as dictionaries.

        Note:
        The candle_index_start and candle_index_end parameters refer to the index positions of the candles,
        with 0 being the most recent candle.
        """

        return pd.DataFrame(mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), candle_index_start, candle_index_end))

    def get_spread(self, symbol) -> float:
        ask_price = mt5.symbol_info_tick(symbol).ask
        bid_price = mt5.symbol_info_tick(symbol).bid
        spread = ask_price - bid_price
        return spread

    def pre_candle_body(self, symbol, timeframe):
        previous_candle = self.get_previous_candle(symbol=symbol, timeframe=timeframe)
        body_size = abs(previous_candle["open"] - previous_candle["close"])
        return body_size
    
    def get_previous_candle(self, symbol, timeframe):
        """
        Returns:
        Object which contains time, open, close, high, low
        Can be accessed as dictioanry e.g obj["close"]
        """
        return mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), 1, 1)[-1]
    
    def get_previous_candle_i(self, symbol, timeframe, i=0):
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

        current_gmt_time = util.get_current_time() + timedelta(hours=2)

        # Generate off market hours high and lows
        start_time = datetime(int(current_gmt_time.year), int(current_gmt_time.month), int(current_gmt_time.day), 
                                hour=0, minute=0, tzinfo=pytz.timezone('Etc/GMT'))
        
        tm_zone = pytz.timezone('Etc/GMT')
        end_time = datetime.now(tm_zone) + timedelta(hours=2)

        position_deals = mt5.history_deals_get(start_time,  end_time)

        if len(position_deals) > 0:
            df = pd.DataFrame(position_deals, columns=position_deals[0]._asdict().keys())
            # df = df[df["entry"] == 1].copy()
            return df
        
        # return empty dataframe
        return pd.DataFrame()


if "__main__" == __name__:
    obj = Wrapper()
    import sys
    symbol = sys.argv[1]
    timeframe = int(sys.argv[2])
    # print(obj.get_candles_by_index(symbol=symbol, candle_index_start=0, candle_index_end=10, timeframe=timeframe))
    # print(obj.get_current_candle(symbol=symbol, timeframe=timeframe))
    # print(obj.get_previous_candle(symbol=symbol, timeframe=timeframe))
    # print(obj.get_existing_symbols())
    # print(obj.get_todays_trades())
    print(obj.pre_candle_body(symbol, timeframe))
    print(obj.get_spread(symbol))