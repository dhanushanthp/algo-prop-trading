import modules.indicators as ind
import modules.config as config
import pytz
import datetime
import time
import MetaTrader5 as mt5
import modules.mng_pos as mp
import modules.slack_msg as slack_msg
from collections import Counter

class RiskManager:
    def __init__(self, profit_split=1) -> None:
        ACCOUNT_SIZE,_, _,_ = ind.get_account_details()
        self.account_size  = ACCOUNT_SIZE
        self.account_risk_percentage = config.account_risk_percentage * profit_split
        self.risk_of_an_account = round(ACCOUNT_SIZE/100*self.account_risk_percentage)
        self.position_risk_percentage = self.account_risk_percentage/config.position_split_of_account_risk
        self.risk_of_a_position = round(ACCOUNT_SIZE/100*self.position_risk_percentage)
        self.previous_time = None
        self.first_max_profit_check = True
        self.second_max_profit_check = True
        self.alert = slack_msg.Slack()
        self.max_risk_hit_counter = 0
        self.enable_half_trail = self.risk_of_an_account + round(ACCOUNT_SIZE/100*0.25) # Add addtional 0.25 to cover commision
        self.max_account_risk = round(ACCOUNT_SIZE/100)

        # Initial Trail loss w.r.t to account size
        self.account_trail_loss = ACCOUNT_SIZE - self.risk_of_an_account
        self.account_name = ind.get_account_name()

        # The max profit split is 100% of risking the account
        # assert profit_split <= 1
    
    def get_max_loss(self):
        return self.account_trail_loss
    
    def profit_day_checker(self):
        account_size, equity, _, _ = ind.get_account_details()
        if equity > account_size + self.risk_of_a_position:
            # Creates a new file
            with open('enabler.txt', 'w') as fp:
                pass

            return True

    def get_max_profit(self):
        return self.account_size + self.risk_of_an_account
    
    def diffuser_profits(self):
        existing_positions = mt5.positions_get()
        counter = Counter([i.symbol for i in existing_positions])
        diffuser_positions = {item: count for item, count in counter.items() if count >= 2}
        for symbol in diffuser_positions.keys():
            print(symbol)

    def risk_diffusers(self):
        internal_existing_positions = mt5.positions_get()
        counter = Counter([i.symbol for i in internal_existing_positions])
        orders = {}
        for position in internal_existing_positions:
            pos_symbol = position.symbol
            if counter[pos_symbol] < 2 and position.comment == "R>60" and position.comment != "defuser":
                order_type = position.type
                entry_price = position.price_open
                stop_price = position.sl
                bid, ask = ind.get_bid_ask(pos_symbol)
                if order_type == 0:
                    current_price = bid
                else:
                    current_price = ask

                volume = position.volume
                points_in_stop = abs(entry_price - stop_price)/2

                if order_type == 0:
                    decision_point = entry_price-points_in_stop
                    if current_price < decision_point:
                        orders[pos_symbol] = "short"
                else:
                    decision_point = entry_price+points_in_stop
                    if current_price > decision_point:
                        orders[pos_symbol] = "long"
        
        return orders
    
    def has_daily_maximum_risk_reached(self):
        """
        Check if the daily maximum risk has been reached based on the account's equity and trail loss.

        Returns:
        bool: True if the daily maximum risk has been reached, False otherwise.
        """

        # Retrieve account details including equity
        _, equity, _, _ = ind.get_account_details()

        # Calculate trail loss, where equity will increase based on positive returns
        trail_loss = equity - self.risk_of_an_account

        # Update account trail loss with the maximum value between current trail loss and previous maximum
        self.account_trail_loss = max(trail_loss, self.account_trail_loss)

        # Check if the daily maximum risk has been reached by comparing equity with account trail loss
        if equity < self.account_trail_loss:
            # Return True if daily maximum risk has been reached
            return True
        
        # Return False if daily maximum risk has not been reached
        return False

    
    def update_to_half_trail(self):
        _, equity, _,_ = ind.get_account_details()
        # Reduce the trail distance when the price cross first profit target
        print(f"{'Half trail at'.ljust(20)}: ${'{:,}'.format(round(self.account_size + self.enable_half_trail))}", "\n")
        if (equity > self.account_size + self.enable_half_trail) and self.first_max_profit_check:
            self.alert.send_msg(f"{self.account_name}: First target max triggered!")
            self.risk_of_an_account = self.risk_of_a_position
            self.first_max_profit_check = False
            return True


if __name__ == "__main__":
    obj = RiskManager(profit_split=0.5)
    while True:
        print(f"Current Risk: {obj.risk_of_a_position}")
        time.sleep(30)