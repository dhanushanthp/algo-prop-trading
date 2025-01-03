import MetaTrader5 as mt
mt.initialize()
import time
from modules.common.slack_msg import Slack
from modules.meta.wrapper import Wrapper

wrapper = Wrapper()
alert = Slack()

tracker = []

while True:
    current_positions = wrapper.get_all_active_positions()

    if not current_positions.empty:
        current_positions["trade"] = current_positions["symbol"] + " : " + current_positions["type"].apply(lambda x: "long" if x == 0 else "short")
        symbols = current_positions["trade"].unique()
        # Check the entry positions
        for symbol in symbols:
            if symbol not in tracker:
                tracker.append(symbol)
                alert.send_msg(msg="Entry: " + symbol)

        for trade in tracker:
            if trade not in symbols:
                tracker.remove(trade)
                alert.send_msg(msg= "Exit: " + trade)


    time.sleep(30)