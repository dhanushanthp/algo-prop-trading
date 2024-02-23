import MetaTrader5 as mt5
from objects import util
import pandas as pd
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

    def get_previous_candle(self, symbol, timeframe):
        """
        Returns:
        Object which contains time, open, close, high, low
        Can be accessed as dictioanry e.g obj["close"]
        """
        return mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), 1, 1)[-1]
    
    def get_current_candle(self, symbol, timeframe):
        """
        Returns:
        Object which contains time, open, close, high, low
        Can be accessed as dictioanry e.g obj["close"]
        """
        return mt5.copy_rates_from_pos(symbol, util.match_timeframe(timeframe), 0, 1)[-1]


if "__main__" == __name__:
    obj = Wrapper()
    import sys
    symbol = sys.argv[1]
    timeframe = int(sys.argv[2])
    print(obj.get_candles_by_index(symbol=symbol, candle_index_start=0, candle_index_end=10, timeframe=timeframe))
    print(obj.get_current_candle(symbol=symbol, timeframe=timeframe))
    print(obj.get_previous_candle(symbol=symbol, timeframe=timeframe))