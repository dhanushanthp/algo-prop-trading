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
        self.max_loss = self.initial_risk * 2 # 4 times the initial risk
        self.first_profit_factor = 1
        self.updated_risk = self.initial_risk
        self.previous_time = None
        self.first_max_profit_check = True
        self.second_max_profit_check = True
        self.alert = slack_msg.Slack()

        # Initial Trail loss w.r.t to account size
        self.trail_loss = ACCOUNT_SIZE - self.max_loss
        self.previous_trail_loss = self.trail_loss
    
    def get_max_loss(self):
        return self.trail_loss

    def get_max_profit(self):
        return self.account_size + (self.max_loss * self.first_profit_factor)
    
    def trail_stop_account_level(self):
        # This update the account level exit plan
        _, equity, _,_ = ind.get_account_details()
        trail_loss = equity - self.max_loss
        # always move update with trail stop
        self.trail_loss = max(trail_loss, self.previous_trail_loss)
        self.previous_trail_loss = self.trail_loss

    def reset_risk(self):
        print("-------Reset to initial risk!-----")
        ACCOUNT_SIZE,_, _,_ = ind.get_account_details()
        self.updated_risk = ACCOUNT_SIZE/100*config.risk_percentage
        self.max_loss = self.updated_risk * 2 # 4 times the initial risk
        self.trail_loss = ACCOUNT_SIZE - self.max_loss

        # Reset max trail loss parameters
        self.first_max_profit_check = True
        self.second_max_profit_check = True
    
    def is_dly_max_risk_reached(self):
        _, equity, _,_ = ind.get_account_details()
        if equity < self.trail_loss:
            return True

        return False
    
    def is_dly_max_profit_reached(self, first_profit_factor, second_profit_factor):
        ACCOUNT_SIZE, equity, _,_ = ind.get_account_details()
        # Reduce the trail distance when the price cross first profit target
        self.first_profit_factor = first_profit_factor
        print(equity, ACCOUNT_SIZE + (self.max_loss * first_profit_factor), self.first_max_profit_check, "\n")
        if (equity > ACCOUNT_SIZE + (self.max_loss * first_profit_factor)) and self.first_max_profit_check:
            self.alert.send_msg(f"First target max triggered!")
            self.max_loss = self.max_loss/2
            self.first_max_profit_check = False
            return True

        # Reduce the trail distance when the price cross second profit target
        # We multiply by 2, since the max loss will be set as half from first profit target marker
        if equity > ACCOUNT_SIZE + (self.max_loss * 2 * second_profit_factor) and self.second_max_profit_check:
            self.alert.send_msg(f"Second target max triggered!")
            self.max_loss = self.max_loss/2
            self.second_max_profit_check = False
    
    def update_risk(self):
        return round(self.initial_risk, 2)

    def update_risk_old(self):
        tm_zone = pytz.timezone('Etc/GMT-2')
        start_time = datetime.datetime.combine(datetime.datetime.now(tm_zone).date(), datetime.time()).replace(tzinfo=tm_zone)
        end_time = datetime.datetime.now(tm_zone) + datetime.timedelta(hours=4)
        traded_win_loss = [i for i in mt5.history_deals_get(start_time,  end_time) if i.entry==1]

        if len(traded_win_loss) > 0:
            last_traded_obj = traded_win_loss[-1]
            last_traded_time = last_traded_obj.time
            
            if self.previous_time is None:
                print("------- Set to inital Risk! -----")
                self.previous_time = last_traded_time
                
            if last_traded_time > self.previous_time:
                print("------- Risk updated! -----")
                # Set the last traded time as previous traded time
                self.previous_time = last_traded_time
            
                last_profit_loss = last_traded_obj.profit

                continues_wins = mp.get_continues_wins()
                
                ACCOUNT_SIZE,_, _,_ = ind.get_account_details()
                risk_delta = ACCOUNT_SIZE/100*0.10 # Increase/Decrease by 0.1 Percentage
                
                max_risk = ACCOUNT_SIZE/100*0.5 # Max 1% of risk at anytime.
                
                # If 2 or more wins in parallel, then increase the risk
                if continues_wins >= 4:
                    # Increase the risk
                    self.updated_risk += risk_delta
                    self.updated_risk = min(max_risk, self.updated_risk)
                else:
                    # Decrease the risk
                    self.updated_risk -= risk_delta
                    self.updated_risk = max(self.initial_risk, self.updated_risk)
            
            return round(self.updated_risk, 2)
            
        return round(self.updated_risk, 2)
        

if __name__ == "__main__":
    obj = RiskManager()
    while True:
        print(f"Current Risk: {obj.update_risk()}")
        time.sleep(30)