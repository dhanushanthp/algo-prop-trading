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
        self.risk_manager = risk_manager.RiskManager()
        self.alert = Slack()
        self.monitor = Monitor()
        self.file_util = FileUtils()

        # Account information
        self.account_name = ind.get_account_name()
        self.previous_equity = None

        # Expected reward for the day
        self.fixed_initial_account_size = self.risk_manager.account_size
    
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
        lots = self.risk_manager.initial_risk/(points_in_stop * dollor_value)
        
        if symbol in curr.currencies:
            points_in_stop = round(points_in_stop, 5)
            lots = lots/10**5
        
        return points_in_stop, lots

   
    def error_logging(self, result, request_str={}):
        if result:
            if result.retcode != mt.TRADE_RETCODE_DONE:
                error_string = f"{result.comment}"
                # self.alert.send_msg(f"ERR: {self.account_name} <br> {error_string} <br> ```{request_str}```")

    def long_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe):
        entry_price = self.get_entry_price(symbol=symbol)

        if entry_price:
            _, stop_price, is_strong_candle, is_long_c = ind.get_stop_range(symbol, entry_timeframe)
            
            if is_strong_candle and mp.get_last_trades_position(symbol, entry_timeframe):
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
                            "comment": f"{is_long_c}>{comment}",
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
            stop_price, _, is_strong_candle, is_long_c = ind.get_stop_range(symbol, entry_timeframe)
            
            if is_strong_candle and mp.get_last_trades_position(symbol, entry_timeframe):
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
                            "comment": f"{is_long_c}>{comment}",
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
            print(f"\n-------  {self.strategy.upper()} @ {datetime.now().strftime('%H:%M:%S')}------------------")
            print(f"{'Current Risk'.ljust(20)}: ${round(self.risk_manager.initial_risk, 2)}, Account Max Loss: ${self.risk_manager.account_max_loss}")
            print(f"{'Max Loss'.ljust(20)}: ${round(self.risk_manager.get_max_loss())}, trail ${self.risk_manager.account_max_loss}")
            print(f"{'Trail Update at'.ljust(20)}: ${round(self.risk_manager.get_max_loss() + self.risk_manager.account_max_loss)}")
            
            is_market_open, is_market_close = util.get_market_status()
            mp.adjust_positions_trailing_stops(self.risk_manager.initial_risk) # Each position trail stop
            self.risk_manager.update_to_half_trail(first_profit_factor=2)

            if self.risk_manager.has_daily_maximum_risk_reached():
                self.retries += 1
                mp.close_all_positions()
                # Re initiate the object
                self.risk_manager = risk_manager.RiskManager()

                time.sleep(30) # Take some time for the account to digest the positions
                current_account_size,_,_,_ = ind.get_account_details()
                
                # The risk reward calclualted based on initial risk
                rr = round((current_account_size - self.fixed_initial_account_size)/self.risk_manager.initial_risk, 2)
                self.alert.send_msg(f"{self.account_name}: Exit {self.retries}, RR: {rr}")

                if rr >= 4 or rr <= -4:
                    self.alert.send_msg(f"{self.account_name}: Done for today!, RR: {rr}")
                    self.immidiate_exit = True

            if is_market_close:
                print("Market Close!")
                self.risk_manager = risk_manager.RiskManager() # Reset the risk for the day
                mp.close_all_positions()
                
                # Reset account size for next day
                self.fixed_initial_account_size = self.risk_manager.account_size
                self.immidiate_exit = False
            
            if is_market_open and not is_market_close and not self.immidiate_exit:
                mp.cancel_all_pending_orders()

                break_long_at_resistance = {}
                reverse_long_at_support = {}

                break_short_at_support = {}
                reverse_short_at_resistance = {}
                for symbol in selected_symbols:
                    break_long_at_resistance[symbol] = []
                    break_short_at_support[symbol] = []

                    reverse_long_at_support[symbol] = []
                    reverse_short_at_resistance[symbol] = []

                    for r_s_timeframe in [1440, 480, 240, 120, 60, 30, 15, 5]:
                        try:
                            # Incase if it failed to request the symbol price
                            levels = ind.find_r_s(symbol, r_s_timeframe)
                        except Exception as e:
                            self.alert.send_msg(f"{self.account_name}: {symbol}: {e}")
                            break

                        resistances = levels["resistance"]
                        support = levels["support"]

                        for resistance_level in resistances:
                            current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(r_s_timeframe), 0, 1)[-1]
                            if (current_candle["open"] > resistance_level) and (resistance_level - 3*ind.get_spread(symbol) < current_candle["close"] < resistance_level):
                                reverse_short_at_resistance[symbol].append(r_s_timeframe)
                            elif (current_candle["open"] < resistance_level) and (resistance_level + 3*ind.get_spread(symbol) > current_candle["close"] > resistance_level):
                                break_long_at_resistance[symbol].append(r_s_timeframe)
                        
                        for support_level in support:
                            current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(r_s_timeframe), 0, 1)[-1]
                            if (current_candle["open"] > support_level) and (support_level - 3*ind.get_spread(symbol) < current_candle["close"] < support_level):
                                break_short_at_support[symbol].append(r_s_timeframe)
                            elif (current_candle["open"] < support_level) and (support_level + 3*ind.get_spread(symbol) > current_candle["close"] > support_level):
                                reverse_long_at_support[symbol].append(r_s_timeframe)
                
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                if len(existing_positions) < len(selected_symbols):
                    for symbol in selected_symbols:
                        if (symbol not in existing_positions):
                            # Break Strategy
                            total_resistance_tf_long = set(break_long_at_resistance[symbol])
                            total_support_tf_short = set(break_short_at_support[symbol])

                            # Reverse Strategy
                            total_support_tf_long = set(reverse_long_at_support[symbol])
                            total_resistance_tf_short = set(reverse_short_at_resistance[symbol])
                            
                            if self.strategy == "break":
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
                            elif self.strategy == "reverse":
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
        win.strategy = sys.argv[1]
        if win.strategy not in ["reverse", "break"]:
            raise Exception("Please enter fixed or auto entry time check!")
    else:
        # Mean the R&S levels and entry check will be based on the same selected timeframe. Default
        win.strategy = "reverse"
        
    
    print("\n------------------------------------------------")
    print(f"SELECTED STRATEGY {win.strategy}" )
    print("------------------------------------------------")
    win.main()

