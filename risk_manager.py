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
        self.initial_risk = round(ACCOUNT_SIZE/100*config.risk_percentage) # Risk only 0.25%
        self.account_max_loss = self.initial_risk * config.stop_factor
        self.first_profit_factor = 1
        self.previous_time = None
        self.first_max_profit_check = True
        self.second_max_profit_check = True
        self.alert = slack_msg.Slack()

        # Initial Trail loss w.r.t to account size
        self.account_trail_loss = ACCOUNT_SIZE - self.account_max_loss
        self.previous_trail_loss = self.account_trail_loss
    
    def get_max_loss(self):
        return self.account_trail_loss

    def get_max_profit(self):
        return self.account_size + (self.account_max_loss * self.first_profit_factor)
    
    def trail_stop_account_level(self):
        # This update the account level exit plan
        _, equity, _,_ = ind.get_account_details()
        trail_loss = equity - self.account_max_loss
        # always move update with trail stop
        self.account_trail_loss = max(trail_loss, self.previous_trail_loss)
        self.previous_trail_loss = self.account_trail_loss
    
    def is_dly_max_risk_reached(self):
        _, equity, _,_ = ind.get_account_details()
        if equity < self.account_trail_loss:
            return True

        return False
    
    def is_dly_max_profit_reached(self, first_profit_factor, second_profit_factor):
        ACCOUNT_SIZE, equity, _,_ = ind.get_account_details()
        # Reduce the trail distance when the price cross first profit target
        self.first_profit_factor = first_profit_factor
        print(equity, ACCOUNT_SIZE + (self.account_max_loss * first_profit_factor), self.first_max_profit_check, "\n")
        if (equity > ACCOUNT_SIZE + (self.account_max_loss * first_profit_factor)) and self.first_max_profit_check:
            self.alert.send_msg(f"First target max triggered!")
            self.account_max_loss = self.account_max_loss/2
            self.first_max_profit_check = False
            return True

        # Reduce the trail distance when the price cross second profit target
        # We multiply by 2, since the max loss will be set as half from first profit target marker
        if equity > ACCOUNT_SIZE + (self.account_max_loss * 2 * second_profit_factor) and self.second_max_profit_check:
            self.alert.send_msg(f"Second target max triggered!")
            self.account_max_loss = self.account_max_loss/2
            self.second_max_profit_check = False
    
    def update_risk(self):
        return round(self.initial_risk, 2)
        

if __name__ == "__main__":
    obj = RiskManager()
    while True:
        print(f"Current Risk: {obj.update_risk()}")
        time.sleep(30)