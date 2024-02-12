import numpy as np
import MetaTrader5 as mt5
mt5.initialize()
import modules.util as util

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

if __name__ == "__main__":
    indi_obj = Indicators()
    print(indi_obj.get_atr("EURUSD", 60))