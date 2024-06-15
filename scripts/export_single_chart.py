import sys
from modules.meta.wrapper import Wrapper
from modules.meta import util

symbol = sys.argv[1]
timeframe = int(sys.argv[2])

wrapper = Wrapper()
actual_chart = wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, n_candles=100)
actual_chart["time"] = actual_chart["time"].apply(lambda x: util.get_traded_time(epoch=x))

heikinashi = wrapper.get_heikin_ashi(symbol=symbol, timeframe=timeframe, n_candles=100)
heikinashi["time"] = heikinashi["time"].apply(lambda x: util.get_traded_time(epoch=x))

actual_chart.to_csv(f"data/chart_data/{symbol}_{timeframe}.csv", index=False)
heikinashi.to_csv(f"data/chart_data/{symbol}_{timeframe}_heikin.csv", index=False)
