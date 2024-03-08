import numpy as np
from objects.Signal import Signal
from typing import Tuple, List, Dict
from clients.ibrk_wrapper import IBRK

class Indicators:
    def __init__(self):
        self.ibrk = IBRK()

    def get_atr(self, symbol:str, timeframe:int) -> float:
        """
        Get ATR based on timeframe
        """    
        rates = self.ibrk.get_candles(symbol=symbol, timeframe=timeframe, days=2)
        
        high = np.array(rates["high"].tolist())
        low = np.array(rates["low"].tolist())
        close = np.array(rates["close"].tolist())

        true_range = np.maximum(high[1:] - low[1:], abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1]))
        atr = np.mean(true_range[-14:])

        return round(atr, 5)

    
    def get_current_day_levels(self, symbol, timeframe) -> Tuple[Signal, Signal]:
        previous_bars = self.ibrk.get_candles(symbol=symbol, timeframe=timeframe)

        if not previous_bars.empty:
            off_hour_highs = Signal(reference="HOD", level=max(previous_bars["high"]), break_bar_index=previous_bars["high"].idxmax())
            off_hour_lows = Signal(reference="LOD", level=min(previous_bars["low"]), break_bar_index=previous_bars["low"].idxmin())
            return off_hour_highs, off_hour_lows

        return None, None


    def get_king_of_levels(self, symbol, timeframe) -> Dict[str, List[Signal]]:
        highs = []
        lows = []
        ofh, ofl = self.get_current_day_levels(symbol=symbol, timeframe=timeframe)
        
        if ofh:                
            highs.append(ofh)
        
        if ofl:
            lows.append(ofl)

        return {"resistance": highs, "support": lows}

if __name__ == "__main__":
    indi_obj = Indicators()
    import sys
    symbol = sys.argv[1]
    timeframe = int(sys.argv[2])
    print(indi_obj.get_current_day_levels(symbol, timeframe))
    print(indi_obj.get_atr(symbol, timeframe))