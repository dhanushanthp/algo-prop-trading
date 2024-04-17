import MetaTrader5 as mt
mt.initialize()
import time
from modules.meta.Indicators import Indicators
import modules.meta.Currencies as curr
from modules.common.slack_msg import Slack


indi_obj = Indicators()
alert = Slack()

tracker = dict()

while True:
    print("Checking Signals...")
    for symbol in curr.get_major_symbols(security="FOREX"):
        signal = indi_obj.get_candle_cross_sma(symbol=symbol, sma_crossing=10)
        if signal:
            direction, hour = signal
            if symbol not in tracker:
                tracker[symbol] = hour
                alert.send_msg(f"{symbol}: {direction}")
            else:
                previous_hour = tracker[symbol]
                if previous_hour != hour:
                    tracker[symbol] = hour
                    alert.send_msg(f"{symbol}: {direction}")

    time.sleep(30)