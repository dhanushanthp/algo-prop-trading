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

class AlgoTrader():
    def __init__(self):
        mt.initialize()

        self.entry_timeframe = None # Default to 15 min
        self.target_ratio = 2.0 # Default 1:0.5 Ratio
        self.stop_ratio = 1.0
        self.risk_manager = risk_manager.RiskManager()
        self.updated_risk = self.risk_manager.initial_risk
        self.strategy = config.REVERSAL
        self.immidiate_exit = False
        self.account_type = "real"
        self.timer = 30
        self.alert = Slack()
        self.monitor = Monitor()
        self.retries = 0
        self.account_name = ind.get_account_name()
        self.file_util = FileUtils()
        self.previous_equity = None
    
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
    
    def get_lot_size(self, symbol, entry_price, stop_price, timeframe):
        
        stop_factor = 1 # Default

        # if timeframe in [5, 15, 30]:
        #     stop_factor = 1.5 # Give extra room for shorter timeframe

        dollor_value = mp.get_dollar_value(symbol)
        points_in_stop = abs(entry_price-stop_price) * stop_factor
        self.updated_risk = self.risk_manager.update_risk()
        lots = self.updated_risk/(points_in_stop * dollor_value)
        
        if symbol in curr.currencies:
            points_in_stop = round(points_in_stop, 5)
            lots = lots/10**5
        
        return points_in_stop, lots

   
    def print_order_log(self, result, request={}):
        if result:
            if result.retcode != mt.TRADE_RETCODE_DONE:
                error_string = f"Error: {result.comment}"
                print(error_string)
                print(request)
        else:
            print("Error with response!")

    def long_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe):
        entry_price = self.get_entry_price(symbol=symbol)

        if entry_price:
            _, stop_price, prev_can_dir = ind.get_stop_range(symbol, entry_timeframe)
            
            if prev_can_dir and mp.get_last_trades_position(symbol, entry_timeframe):
                stop_price = self._round(symbol, stop_price)
                
                if entry_price > stop_price:                
                    try:
                        print(f"{symbol.ljust(12)}: LONG")        
                        points_in_stop, lots = self.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=stop_price, timeframe=entry_timeframe)
                        
                        lots =  round(lots, 2)
                        
                        order_request = {
                            "action": mt.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt.ORDER_TYPE_BUY_LIMIT,
                            "price": entry_price,
                            "sl": self._round(symbol, entry_price - self.stop_ratio * points_in_stop),
                            "tp": self._round(symbol, entry_price + self.target_ratio * points_in_stop),
                            "comment": comment,
                            "magic":r_s_timeframe,
                            "type_time": mt.ORDER_TIME_GTC,
                            "type_filling": mt.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt.order_send(order_request)
                        self.print_order_log(request_log, order_request)
                        return True
                    except Exception as e:
                        print(f"Long entry exception: {e}")
            else:
                print(f"{symbol.ljust(12)}: Skipped!")
                return False

    def short_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe):
        entry_price = self.get_entry_price(symbol)
        
        if entry_price:
            stop_price, _, previous_candle = ind.get_stop_range(symbol, entry_timeframe)
            
            if previous_candle and mp.get_last_trades_position(symbol, entry_timeframe):
                stop_price = self._round(symbol, stop_price)

                if stop_price > entry_price:
                    try:
                        print(f"{symbol.ljust(12)}: SHORT")      
                        points_in_stop, lots = self.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=stop_price, timeframe=entry_timeframe)
                        
                        lots =  round(lots, 2)

                        order_request = {
                            "action": mt.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt.ORDER_TYPE_SELL_LIMIT,
                            "price": entry_price,
                            "sl": self._round(symbol, entry_price + self.stop_ratio * points_in_stop),
                            "tp": self._round(symbol, entry_price - self.target_ratio * points_in_stop),
                            "comment": comment,
                            "magic":r_s_timeframe,
                            "type_time": mt.ORDER_TIME_GTC,
                            "type_filling": mt.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt.order_send(order_request)
                        self.print_order_log(request_log, order_request)
                        return True
                    except Exception as e:
                        print(e)
            else:
                print(f"{symbol.ljust(12)}: Skipped!")
                return False
    
    def main(self):
        selected_symbols = ind.get_ordered_symbols()
        
        while True:
            print(f"\n-------  Executed @ {datetime.now().strftime('%H:%M:%S')}------------------")
            print(f"{'Current Risk'.ljust(20)}: ${self.updated_risk}")
            print(f"{'Max Loss'.ljust(20)}: ${round(self.risk_manager.get_max_loss())}, trail ${self.risk_manager.account_max_loss}")
            print(f"{'Trail Update at'.ljust(20)}: ${round(self.risk_manager.get_max_loss() + self.risk_manager.account_max_loss)}")
            
            is_market_open, is_market_close = util.get_market_status()
            mp.trail_stop_previous_candle(self.risk_manager.initial_risk) # Each position trail stop
            self.risk_manager.trail_stop_account_level() # Update the account level exit plan

            # Collect change in equity
            _, equity, _,_ = ind.get_account_details()
            if self.previous_equity != equity:
                self.previous_equity = equity
                self.file_util.equity_collector(self.account_name, 
                                                datetime.now().strftime('%H:%M:%S'),
                                                equity)

            # Max Accepted Trail Loss
            if self.account_type == "real":
                # 0, Reduce  Trail as soon as the entry has positive
                # 1, Reduce Trail as soon as the profit reach 1R
                if self.risk_manager.is_dly_max_profit_reached(0, 3):
                # Increase the checking frequency one the price pass the first target
                # so we can move with the pase rather 30 second delay
                    self.timer = 30
            
                if self.risk_manager.is_dly_max_risk_reached():
                    self.retries += 1
                    mp.close_all_positions()
                    # Re initiate the object
                    self.risk_manager = risk_manager.RiskManager()
                    self.updated_risk = self.risk_manager.initial_risk
                    self.alert.send_msg(f"{self.account_name}: Exit {self.retries}")
                    self.timer = 30
                    if self.retries >= 2:
                        self.alert.send_msg(f"{self.account_name}: Done for today!")
                        self.immidiate_exit = True
            else:
                # 1, Reduce Trail as soon as the profit reach 1R
                # 2, Reduce Trail as soon as the profit reach 2R
                if self.risk_manager.is_dly_max_profit_reached(1, 2):
                # Increase the checking frequency one the price pass the first target
                # so we can move with the pase rather 30 second delay
                    self.timer = 30

                if self.risk_manager.is_dly_max_risk_reached():
                    self.retries += 1
                    mp.close_all_positions()
                    # Re initiate the object
                    self.risk_manager = risk_manager.RiskManager()
                    self.updated_risk = self.risk_manager.initial_risk
                    self.alert.send_msg(f"{self.account_name}: Exit {self.retries}")
                    self.timer = 30
                    if self.retries >= 4:
                        self.alert.send_msg(f"{self.account_name}: Done for today!")
                        self.immidiate_exit = True


            if is_market_close:
                print("Market Close!")
                self.risk_manager = risk_manager.RiskManager() # Reset the risk for the day
                mp.close_all_positions()
                self.immidiate_exit = False
            
            if is_market_open and not is_market_close and not self.immidiate_exit:
                
                if self.account_type == "real":
                    # Sent heart beat every 30 minutes
                    if int(datetime.now().strftime('%M'))%30 == 0:
                        self.alert.send_msg(f"{self.account_name}: Heartbeat...")

                mp.cancel_all_pending_orders()

                combinbed_resistance_long = {}
                combined_support_long = {}

                combined_support_short = {}
                combinbed_resistance_short = {}
                for symbol in selected_symbols:
                    combinbed_resistance_long[symbol] = []
                    combined_support_long[symbol] = []
                    combined_support_short[symbol] = []
                    combinbed_resistance_short[symbol] = []

                    for r_s_timeframe in [240, 120, 60, 30, 15]:
                        try:
                            # Incase if it failed to request the symbol price
                            levels = ind.find_r_s(symbol, r_s_timeframe)
                        except Exception as e:
                            self.alert.send_msg(f"{self.account_name}: {symbol}: {e}")
                            break

                        resistances = levels["resistance"]
                        support = levels["support"]

                        for resistance_level in resistances:
                            short_entry_level = resistance_level + (3 * ind.get_spread(symbol))
                            long_entry_level = resistance_level - (3 * ind.get_spread(symbol))

                            current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(r_s_timeframe), 0, 1)[-1]
                            if current_candle["open"] > short_entry_level and current_candle["close"] < short_entry_level:
                                combinbed_resistance_short[symbol].append(r_s_timeframe)
                            elif current_candle["open"] < long_entry_level and current_candle["close"] > long_entry_level:
                                combinbed_resistance_long[symbol].append(r_s_timeframe)
                        
                        for support_level in support:
                            short_entry_level = support_level + (3 * ind.get_spread(symbol))
                            long_entry_level = support_level - (3 * ind.get_spread(symbol))
                            current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(r_s_timeframe), 0, 1)[-1]
                            if current_candle["open"] > short_entry_level and current_candle["close"] < short_entry_level:
                                combined_support_short[symbol].append(r_s_timeframe)
                            elif current_candle["open"] < long_entry_level and current_candle["close"] > long_entry_level:
                                combined_support_long[symbol].append(r_s_timeframe)
                
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                if len(existing_positions) < len(selected_symbols):
                    for symbol in selected_symbols:
                        active_orders = len(mt.orders_get())
                        #  and active_orders < 1
                        if (symbol not in existing_positions):

                            # Don't trade US500.cash before GMT -2 time 10, or 3AM US Time
                            # if current_hour <= 10 and symbol in ["US500.cash", "UK100.cash"]:
                            #     continue
                            
                            total_resistance_tf_long = set(combinbed_resistance_long[symbol])
                            total_support_tf_long = set(combined_support_long[symbol])

                            total_resistance_tf_short = set(combinbed_resistance_short[symbol])
                            total_support_tf_short = set(combined_support_short[symbol])

                            if self.entry_timeframe == "break":
                                print(f"{symbol.ljust(12)} RL: {'|'.join(map(str, total_resistance_tf_long)).ljust(10)} SS: {'|'.join(map(str, total_support_tf_short)).ljust(10)}")
                                if len(total_resistance_tf_long) >= 2:
                                    self.long_real_entry(symbol=symbol, 
                                                            comment='|'.join(map(str, total_resistance_tf_long)), 
                                                            r_s_timeframe=max(total_resistance_tf_long), 
                                                            entry_timeframe=max(total_resistance_tf_long))
                                elif len(total_support_tf_short) >= 2:
                                    self.short_real_entry(symbol=symbol, 
                                                            comment='|'.join(map(str, total_support_tf_short)), 
                                                            r_s_timeframe=max(total_support_tf_short), 
                                                            entry_timeframe=max(total_support_tf_short))
                            elif self.entry_timeframe == "reverse":
                                print(f"{symbol.ljust(12)} SL: {'|'.join(map(str, total_support_tf_long)).ljust(10)} RS: {'|'.join(map(str, total_resistance_tf_short)).ljust(10)}")
                                if len(total_resistance_tf_short) >= 2:
                                    self.short_real_entry(symbol=symbol, 
                                                            comment='|'.join(map(str, total_resistance_tf_short)), 
                                                            r_s_timeframe=max(total_resistance_tf_short), 
                                                            entry_timeframe=max(total_resistance_tf_short))
                                elif len(total_support_tf_long) >= 2:
                                    self.long_real_entry(symbol=symbol, 
                                                            comment='|'.join(map(str, total_support_tf_long)), 
                                                            r_s_timeframe=max(total_support_tf_long), 
                                                            entry_timeframe=max(total_support_tf_long))
                            else:
                                    raise Exception("Strategy not defined!")
            
            time.sleep(self.timer)
    
if __name__ == "__main__":
    win = AlgoTrader()
    
    if len(sys.argv) > 1:
        win.entry_timeframe = sys.argv[1]
        win.account_type = sys.argv[2]
        if win.entry_timeframe not in ["reverse", "break"]:
            raise Exception("Please enter fixed or auto entry time check!")
    else:
        # Mean the R&S levels and entry check will be based on the same selected timeframe. Default
        win.entry_timeframe = "auto"
        
    
    print("\n------------------------------------------------")
    print(f"SELECTED TIMEFRAME {win.entry_timeframe}" )
    print("------------------------------------------------")
    win.main()

