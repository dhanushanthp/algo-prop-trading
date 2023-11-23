import indicators as ind
import config
import pytz
import datetime
import time
import MetaTrader5 as mt5

class RiskManager:
    def __init__(self) -> None:
        ACCOUNT_SIZE,_, _,_ = ind.get_account_details()
        self.initial_risk = ACCOUNT_SIZE/100*config.risk_percentage # Risk only 0.25%
        
        self.updated_risk = self.initial_risk
        self.previous_time = None
    
    def update_risk(self):
        tm_zone = pytz.timezone('Etc/GMT-2')
        start_time = datetime.datetime.combine(datetime.datetime.now(tm_zone).date(), datetime.time()).replace(tzinfo=tm_zone)
        end_time = datetime.datetime.now(tm_zone) + datetime.timedelta(hours=4)
        traded_win_loss = [i for i in mt5.history_deals_get(start_time,  end_time) if i.entry==1]
        if len(traded_win_loss) > 0:
            last_traded_obj = traded_win_loss[-1]
            last_traded_time = last_traded_obj.time
            
            if self.previous_time is None:
                print("-------Set to Inital Risk!-----")
                self.previous_time = last_traded_time
                
            if last_traded_time > self.previous_time:
                print("-------Risk Updated!-----")
                # Set the last traded time as previous traded time
                self.previous_time = last_traded_time
            
                last_profit_loss = last_traded_obj.profit
                
                ACCOUNT_SIZE,_, _,_ = ind.get_account_details()
                risk_delta = ACCOUNT_SIZE/100*0.10 # Increase/Decrease by 0.1 Percentage
                 
                if last_profit_loss > 0:
                    # Increase the risk
                    self.updated_risk += risk_delta
                else:
                    # Decrease the risk
                    self.updated_risk -= risk_delta
            
            return round(self.updated_risk, 2)
            
        return round(self.updated_risk, 2)
        

if __name__ == "__main__":
    obj = RiskManager()
    while True:
        print(f"Current Risk: {obj.update_risk()}")
        time.sleep(30)