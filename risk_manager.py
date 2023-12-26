import indicators as ind
import config
import pytz
import datetime
import time
import MetaTrader5 as mt5
import mng_pos as mp
import slack_msg

class RiskManager:
    def __init__(self) -> None:
        ACCOUNT_SIZE,_, _,_ = ind.get_account_details()
        self.account_size  = ACCOUNT_SIZE
        self.initial_risk = round(ACCOUNT_SIZE/100*config.risk_percentage)
        self.account_max_loss = self.initial_risk * config.stop_factor
        self.first_profit_factor = 1
        self.previous_time = None
        self.first_max_profit_check = True
        self.second_max_profit_check = True
        self.alert = slack_msg.Slack()
        self.max_risk_hit_counter = 0

        # Initial Trail loss w.r.t to account size
        self.account_trail_loss = ACCOUNT_SIZE - self.account_max_loss
        self.account_name = ind.get_account_name()
    
    def get_max_loss(self):
        return self.account_trail_loss
    
    def profit_day_checker(self):
        account_size, equity, _, _ = ind.get_account_details()
        if equity > account_size + self.initial_risk:
            # Creates a new file
            with open('enabler.txt', 'w') as fp:
                pass

            return True

    def get_max_profit(self):
        return self.account_size + (self.account_max_loss * self.first_profit_factor)
    
    def has_daily_maximum_risk_reached(self):
        _, equity, _, _ = ind.get_account_details()

        # Calculate trail loss, The equtity will keep increase based on positive return
        trail_loss = equity - self.account_max_loss

        # Update account trail loss with the maximum value between current trail loss
        self.account_trail_loss = max(trail_loss, self.account_trail_loss)

        # Check if the daily maximum risk has been reached
        if equity < self.account_trail_loss:
            return True
        
        return False
    
    def update_to_half_trail(self, first_profit_factor=1):
        _, equity, _,_ = ind.get_account_details()
        # Reduce the trail distance when the price cross first profit target
        self.first_profit_factor = first_profit_factor
        print(f"{'Half trail at'.ljust(20)}: ${'{:,}'.format(round(self.account_size + (self.account_max_loss * first_profit_factor)))}", "\n")
        if (equity > self.account_size + (self.account_max_loss * first_profit_factor)) and self.first_max_profit_check:
            self.alert.send_msg(f"{self.account_name}: First target max triggered!")
            self.account_max_loss = self.account_max_loss/2
            self.first_max_profit_check = False
            return True


if __name__ == "__main__":
    obj = RiskManager()
    while True:
        print(f"Current Risk: {obj.initial_risk}")
        time.sleep(30)