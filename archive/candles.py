import MetaTrader5 as mt5
# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()
    

def is_hammer(candle_points):
    close = candle_points["close"]
    open = candle_points["open"]
    high = candle_points["high"]
    low = candle_points["low"]
    print(candle_points)
    print(((high - low) > 3 * (open - close)))
    print(((close - low) / (0.001 + high - low)))

    signal =  (((high - low) > 3 * (open - close)) 
               and ((close - low) / (0.001 + high - low) > 0.6) 
               and ((open - low) / (0.001 + high - low) > 0.6))
    
    return signal


def is_inverted_hammer(candle_points):
    close = candle_points["close"]
    open = candle_points["open"]
    high = candle_points["high"]
    low = candle_points["low"]

    signal = (((high - low) > 3 * (open - close))
              and ((high - close) / (0.001 + high - low) > 0.6)
              and ((high - open) / (0.001 + high - low) > 0.6))
    
    return signal


h1_1 = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H4, 1, 1)[0]

print(is_hammer(h1_1))
print(is_inverted_hammer(h1_1))