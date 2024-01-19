from statistics import mean 
import math
import indicators as ind
import util as util
import currency_pairs as curr
import sys
import risk_manager

from datetime import datetime, timedelta
import config
import pytz
import time

import MetaTrader5 as mt
import mng_pos as mp
from slack_msg import Slack
from monitor import Monitor
from file_utils import FileUtils
import os
import phoenix_client as client

class AlgoTrader():
    def __init__(self):
        # MetaTrader initialization
        mt.initialize()

        # Default values
        self.strategy = None  # Default to 15 min
        self.target_ratio = 2.0  # Default 1:0.5 Ratio
        self.stop_ratio = 1.0
        self.immidiate_exit = False
        self.timer = 30
        self.retries = 0

        # External dependencies
        self.risk_manager = risk_manager.RiskManager(profit_split=1)
        self.alert = Slack()
        self.monitor = Monitor()
        self.file_util = FileUtils()

        self.trade_master = False

        # Account information
        self.account_name = ind.get_account_name()
        self.previous_equity = None

        # Expected reward for the day
        self.fixed_initial_account_size = self.risk_manager.account_size
        self.master_initial_account_size = self.risk_manager.account_size

        # Default
        self.trading_timeframes = [240]
    
    def _round(self, symbol, price):
        round_factor = 5 if symbol in curr.currencies else 2
        round_factor = 2 if symbol == "XAUUSD" else round_factor
        round_factor = 3 if symbol in curr.jpy_currencies else round_factor
        return round(price, round_factor)
            
    def get_entry_price(self, symbol):
        try:
            ask_price = mt.symbol_info_tick(symbol).ask
            bid_price = mt.symbol_info_tick(symbol).bid
            mid_price = (ask_price + bid_price)/2
            return self._round(symbol=symbol, price=mid_price)
        except Exception:
            return None
    
    def get_lot_size(self, symbol, entry_price, stop_price):
        dollor_value = mp.get_dollar_value(symbol)
        points_in_stop = abs(entry_price-stop_price)
        lots = self.risk_manager.risk_of_a_position/(points_in_stop * dollor_value)
        
        if symbol in curr.currencies:
            points_in_stop = round(points_in_stop, 5)
            lots = lots/10**5
        
        # This change made of fundedEngineer account!
        if symbol in ['ASX_raw', 'FTSE_raw', 'FTSE100']:
            lots = lots/10
        
        if symbol in ['SP_raw', "SPX500"]:
            lots = lots/40
        
        if symbol in ['HK50_raw']:
            lots = lots/100
        
        if symbol in ['NIKKEI_raw']:
            lots = lots/1000
        
        return points_in_stop, lots

   
    def error_logging(self, result, request_str={}):
        if result:
            if result.retcode != mt.TRADE_RETCODE_DONE:
                error_string = f"{result.comment}"
                # self.alert.send_msg(f"ERR: {self.account_name} <br> {error_string} <br> ```{request_str}```")
                print(error_string)

    def long_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe):
        entry_price = self.get_entry_price(symbol=symbol)

        if entry_price and mp.get_last_trades_position(symbol, entry_timeframe):
            _, stop_price, is_strong_candle, _, _ = ind.get_stop_range(symbol=symbol, timeframe=entry_timeframe, n_spreds=6)
            
            if is_strong_candle:
                stop_price = self._round(symbol, stop_price)
                
                if entry_price > stop_price:                
                    try:
                        print(f"{symbol.ljust(12)}: LONG")
                        points_in_stop, lots = self.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=stop_price)
                        
                        lots =  round(lots, 2)
                        
                        order_request = {
                            "action": mt.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt.ORDER_TYPE_BUY_LIMIT,
                            "price": entry_price,
                            "sl": self._round(symbol, entry_price - self.stop_ratio * points_in_stop),
                            "tp": self._round(symbol, entry_price + self.target_ratio * points_in_stop),
                            "comment": f"{comment}",
                            "magic":r_s_timeframe,
                            "type_time": mt.ORDER_TIME_GTC,
                            "type_filling": mt.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt.order_send(order_request)
                        self.error_logging(request_log, order_request)
                        return True
                    except Exception as e:
                        print(f"Long entry exception: {e}")
            else:
                print(f" Skipped!")
                return False

    def short_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe):
        entry_price = self.get_entry_price(symbol)
        
        if entry_price and mp.get_last_trades_position(symbol, entry_timeframe):
            stop_price, _, is_strong_candle, _, _ = ind.get_stop_range(symbol=symbol, timeframe=entry_timeframe, n_spreds=6)
            
            if is_strong_candle:
                stop_price = self._round(symbol, stop_price)

                if stop_price > entry_price:
                    try:
                        print(f"{symbol.ljust(12)}: SHORT")      
                        points_in_stop, lots = self.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=stop_price)
                        
                        lots =  round(lots, 2)

                        order_request = {
                            "action": mt.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt.ORDER_TYPE_SELL_LIMIT,
                            "price": entry_price,
                            "sl": self._round(symbol, entry_price + self.stop_ratio * points_in_stop),
                            "tp": self._round(symbol, entry_price - self.target_ratio * points_in_stop),
                            "comment": f"{comment}",
                            "magic":r_s_timeframe,
                            "type_time": mt.ORDER_TIME_GTC,
                            "type_filling": mt.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt.order_send(order_request)
                        self.error_logging(request_log, order_request)
                        return True
                    except Exception as e:
                        print(e)
            else:
                print(f" Skipped!")
                return False
    
    def main(self):
        selected_symbols = ind.get_ordered_symbols()
        
        while True:
            print(f"\n-------  PHOENIX {self.strategy.upper()} @ {datetime.now().strftime('%H:%M:%S')} in {self.trading_timeframes} TFs------------------")
            is_market_open, is_market_close = util.get_market_status()
            print(f"{'Acc Trail Loss'.ljust(20)}: {self.risk_manager.account_risk_percentage}%")
            print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")
            print(f"{'Acc at Risk'.ljust(20)}: {'{:,}'.format(round(((self.risk_manager.get_max_loss() - self.fixed_initial_account_size)/self.fixed_initial_account_size) * 100, 2))}%, ${self.risk_manager.get_max_loss()}")
            print(f"{'Next Trail at'.ljust(20)}: ${'{:,}'.format(round(self.risk_manager.get_max_loss() + self.risk_manager.risk_of_an_account))}")
            
            # mp.adjust_positions_trailing_stops() # Each position trail stop

            # +3 is failed 3 tries, and -6 profit of 30% slot
            if (self.retries >= 3 or self.retries < -6) and not self.immidiate_exit:
                mp.close_all_positions()
                time.sleep(30) # Take some time for the account to digest the positions
                current_account_size,_,_,_ = ind.get_account_details()

                pnl = (current_account_size - self.master_initial_account_size)
                self.alert.send_msg(f"{self.account_name}: Done for today! {round(pnl)}")
                self.immidiate_exit = True

            if is_market_close:
                print("Market Close!")
                self.risk_manager = risk_manager.RiskManager(profit_split=1) # Reset the risk for the day
                mp.close_all_positions()
                
                # Reset account size for next day
                self.fixed_initial_account_size = self.risk_manager.account_size
                self.master_initial_account_size = self.risk_manager.account_size
                self.immidiate_exit = False
                self.retries = 0
            

            if is_market_open and not is_market_close and not self.immidiate_exit:
                mp.cancel_all_pending_orders()

                master_positions = client.get_master_positions()
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                # Existing positions
                for symbol in master_positions.keys():
                    mapped_symbol = mp.get_symbol_mapping(symbol=symbol)
                    if mapped_symbol not in existing_positions:
                        direction = master_positions[symbol][0]
                        time_difference = util.get_time_difference(master_positions[symbol][1])
                        print(f"{symbol}: {time_difference}")
                        if time_difference < 15:
                            if direction == 0:
                                self.long_real_entry(symbol=mapped_symbol,
                                                    comment="RL>60", 
                                                    r_s_timeframe=60, 
                                                    entry_timeframe=60)
                            elif direction == 1:
                                self.short_real_entry(symbol=mapped_symbol,
                                                    comment="RL>60",
                                                    r_s_timeframe=60,
                                                    entry_timeframe=60)

                _, equity, _, _ = ind.get_account_details()
                rr = (equity - self.fixed_initial_account_size)/self.risk_manager.risk_of_an_account
                pnl = (equity - self.master_initial_account_size)
                
                print(f"RR:{round(rr, 2)}")
                
                if rr > 0.6 or rr < -0.3:
                    mp.close_all_positions()
                    time.sleep(30) # Take some time for the account to digest the positions
                    self.risk_manager = risk_manager.RiskManager(profit_split=1)
                    self.fixed_initial_account_size = self.risk_manager.account_size

                    if rr > 0.5:
                        self.retries -= 1
                    else:
                        self.retries += 1

                    self.alert.send_msg(f"`{self.account_name}`(`{self.retries}`), RR: {round(rr, 2)}, ${round(pnl)}")
            
            time.sleep(self.timer)
    
if __name__ == "__main__":
    win = AlgoTrader()
    
    if len(sys.argv) > 1:
        win.strategy = sys.argv[1]
        if win.strategy not in ["reverse", "break"]:
            raise Exception("Please enter fixed or auto entry time check!")
        
        win.trading_timeframes = [int(i) for i in sys.argv[2].split(",")]

        if len(sys.argv) > 3 and sys.argv[3] == "master":
            win.trade_master = True

    else:
        # Mean the R&S levels and entry check will be based on the same selected timeframe. Default
        win.strategy = "smart"

        # otherwise timeframe will be default to 4 hours

    win.main()

