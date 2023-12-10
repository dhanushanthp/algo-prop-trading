import MetaTrader5 as mt5
from slack_msg import Slack

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

class Monitor:
    def __init__(self) -> None:
        self.existing_positions = []
        self.alert = Slack()

    def update_positions_alert(self):
        existing_positions = mt5.positions_get()
        for position in existing_positions:
            position_id = position.position_id
            if position_id not in self.existing_positions:
                self.existing_positions.append(position_id)
                msg = f"{position.symbol} added."
                self.alert.send_msg(msg)
                
            
            # each existing position ID, check it has type -1 for exit,
            # So can alert on exist as well.