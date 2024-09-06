from modules.meta.wrapper import Wrapper
from modules.meta import util
from tqdm import tqdm
import modules.meta.Currencies as curr
wrapper = Wrapper()
for symbol in  tqdm(curr.master_currencies + curr.us_indexes):
    for timeframe in [5]:
        if timeframe >= 1440:
            n_candles = 210
        else:
            n_candles = 700*4*10

        actual_chart = wrapper.get_last_n_candles(symbol=symbol, timeframe=timeframe, n_candles=n_candles)
        actual_chart["time"] = actual_chart["time"].apply(lambda x: util.get_traded_time(epoch=x))
        actual_chart["symbol"] = symbol
        actual_chart.to_csv(f"notebooks/data/candles/{symbol}_{timeframe}.csv", index=False)