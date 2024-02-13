import MetaTrader5 as mt5
from objects.slack_msg import Slack

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
            ticket = position.ticket
            if ticket not in self.existing_positions:
                self.existing_positions.append(ticket)
                msg = f"{position.symbol} added."
                self.alert.send_msg(msg)
                
            
            # each existing position ID, check it has type -1 for exit,
            # So can alert on exist as well.


if __name__ == "__main__":
    obj = Monitor()
    obj.update_positions_alert()