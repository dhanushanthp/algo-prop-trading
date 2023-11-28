from statistics import mean 
import math
import indicators as ind
import util as util
import currency_pairs as curr
import sys
import risk_manager


import config
import pytz
import datetime
import time

import MetaTrader5 as mt
import mng_pos as mp

import client

class AlgoTrader():
    def __init__(self):
        mt.initialize()
        self.previous_time = None
    
    def trade(self, symbol, direction, profit_loss):
        tag = "WIN" if profit_loss > 0 else "LOSS"

        # if tag == "WIN":
        #     direction = "L" if direction == "S" else "S"

        print(f"Entry Trade with : {symbol}, {direction}, {tag}")
        client.async_trigger_order_entry(symbol, direction, tag)
            
    
    def main(self):
        while True:
            print(f"\n-------  Executed @ {datetime.datetime.now().strftime('%H:%M:%S')}------------------")
            
            tm_zone = pytz.timezone('Etc/GMT-2')
            start_time = datetime.datetime.combine(datetime.datetime.now(tm_zone).date(), datetime.time()).replace(tzinfo=tm_zone)
            end_time = datetime.datetime.now(tm_zone) + datetime.timedelta(hours=4)
            traded_win_loss = [i for i in mt.history_deals_get(start_time,  end_time) if i.entry==1]

            if len(traded_win_loss) > 0:
                # Get the last one
                last_traded_obj = traded_win_loss[-1]
                last_traded_time = last_traded_obj.time
                direction = "S" if last_traded_obj.type == 1 else "L"
                symbol = last_traded_obj.symbol
                profit_loss = last_traded_obj.profit
                
                if self.previous_time is None:
                    print("------- Initial Time Set -----")
                    self.previous_time = last_traded_time
                    # self.trade(symbol, direction, profit_loss)
                    
                if last_traded_time > self.previous_time:
                    print("------- New Order Found -----")
                    # Set the last traded time as previous traded time
                    self.previous_time = last_traded_time
                    self.trade(symbol, direction, profit_loss)
        
            time.sleep(30)
    
if __name__ == "__main__":
    win = AlgoTrader()
    win.main()
    
    


