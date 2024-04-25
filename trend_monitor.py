import MetaTrader5 as mt
mt.initialize()
import time
from modules.meta.Indicators import Indicators
import modules.meta.Currencies as curr
from modules.common.slack_msg import Slack
import pandas as pd
from modules.meta.wrapper import Wrapper
from modules.meta.Prices import Prices

indi_obj = Indicators(wrapper=Wrapper(), prices=Prices())
alert = Slack()

tracker = dict()

while True:
    signals = []
    for symbol in curr.get_major_symbols(security="FOREX"):
        signal = indi_obj.get_candle_cross_sma(symbol=symbol, sma_crossing=50, timeframe=60)
        
        if signal:
            direction, hour = signal
            if symbol not in tracker:
                tracker[symbol] = hour
                signals.append((symbol, direction))
            else:
                previous_hour = tracker[symbol]
                if previous_hour != hour:
                    tracker[symbol] = hour
                    signals.append((symbol, direction))
    
    df = pd.DataFrame(signals, columns=["symbol", "direction"])
    if not df.empty:
        df = df.groupby("direction")["symbol"].agg(lambda x: ','.join(x)).reset_index()
        msg = df.to_string()
        alert.send_msg(msg=msg)

    time.sleep(30)