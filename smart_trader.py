import os
from statistics import mean 
import math
import sys
import MetaTrader5 as mt
from datetime import datetime, timedelta
import pytz
import time
import argparse

import modules.indicators as ind
import modules.util as util
import modules.currency_pairs as curr
import modules.risk_manager as risk_manager
import modules.config as config
import modules.mng_pos as mp
from modules.slack_msg import Slack
from modules.monitor import Monitor
from modules.file_utils import FileUtils

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

        # Account information
        self.account_name = ind.get_account_name()
        self.previous_equity = None

        # Expected reward for the day
        self.fixed_initial_account_size = self.risk_manager.account_size

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

    def long_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe):
        entry_price = self.get_entry_price(symbol=symbol)

        if entry_price and mp.get_last_trades_position(symbol, entry_timeframe):
            _, stop_price, is_strong_candle, _, _ = ind.get_stop_range(symbol=symbol, timeframe=entry_timeframe)
            
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
                print(f" Candle not strong!")
                return False

    def short_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe):
        entry_price = self.get_entry_price(symbol)
        
        if entry_price and mp.get_last_trades_position(symbol, entry_timeframe):
            stop_price, _, is_strong_candle, _, _ = ind.get_stop_range(symbol=symbol, timeframe=entry_timeframe)
            
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
                print(f" Candle not strong!")
                return False
    
    def main(self):
        selected_symbols = ind.get_ordered_symbols()
        
        while True:
            print(f"\n-------  {self.strategy.upper()} @ {datetime.now().strftime('%H:%M:%S')} in {self.trading_timeframes} TFs------------------")
            is_market_open, is_market_close = util.get_market_status()
            print(f"{'Acc Trail Loss'.ljust(20)}: {self.risk_manager.account_risk_percentage}%")
            print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")
            print(f"{'Acc at Risk'.ljust(20)}: {'{:,}'.format(round(((self.risk_manager.get_max_loss() - self.fixed_initial_account_size)/self.fixed_initial_account_size) * 100, 2))}%, ${self.risk_manager.get_max_loss()}")
            print(f"{'Next Trail at'.ljust(20)}: ${'{:,}'.format(round(self.risk_manager.get_max_loss() + self.risk_manager.risk_of_an_account))}")
            
            mp.adjust_positions_trailing_stops() # Each position trail stop

            if self.risk_manager.has_daily_maximum_risk_reached():
                self.retries += 1
                mp.close_all_with_condition()
                time.sleep(30) # Take some time for the account to digest the positions
                current_account_size,_,_,_ = ind.get_account_details()

                # The risk reward calclualted based on initial risk
                rr = (current_account_size - self.fixed_initial_account_size)/self.risk_manager.risk_of_an_account
                self.alert.send_msg(f"{self.account_name}: Exit {self.retries}, RR: {round(rr, 2)}")
                
                # if rr >= 2 or rr <= -1:
                if rr <= 0:
                    self.alert.send_msg(f"{self.account_name}: Done for today!, Account RR: {round(rr, 2)}")
                    self.immidiate_exit = True
                
                # Re initiate the object
                self.risk_manager = risk_manager.RiskManager(profit_split=0.5)
                self.fixed_initial_account_size = self.risk_manager.account_size

            if is_market_close:
                print("Market Close!")
                self.risk_manager = risk_manager.RiskManager(profit_split=1) # Reset the risk for the day
                mp.close_all_positions()
                
                # Reset account size for next day
                self.fixed_initial_account_size = self.risk_manager.account_size
                self.immidiate_exit = False
            
            num_existing_positions = len(mt.positions_get())
            if is_market_open and (not is_market_close) and (not self.immidiate_exit) and (num_existing_positions <= config.position_split_of_account_risk):
                mp.cancel_all_pending_orders()

                break_long_at_resistance = {}
                reverse_long_at_support = {}
                reverse_long_at_support_v2 = {}

                break_short_at_support = {}
                reverse_short_at_resistance = {}
                reverse_short_at_resistance_v2 = {}

                for symbol in selected_symbols:

                    break_long_at_resistance[symbol] = []
                    break_short_at_support[symbol] = []

                    reverse_long_at_support[symbol] = []
                    reverse_short_at_resistance[symbol] = []

                    reverse_long_at_support_v2[symbol] = []
                    reverse_short_at_resistance_v2[symbol] = []

                    for r_s_timeframe in self.trading_timeframes:
                        try:
                            # Incase if it failed to request the symbol price
                            levels = ind.support_resistance_levels(symbol, r_s_timeframe)
                            _, _, _, _, optimal_distance = ind.get_stop_range(symbol=symbol, timeframe=r_s_timeframe)
                            optimal_distance = optimal_distance/2
                        except Exception as e:
                            self.alert.send_msg(f"{self.account_name}: {symbol}: {e}")
                            break

                        resistances = levels["resistance"]
                        support = levels["support"]

                        current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(r_s_timeframe), 0, 1)[-1]

                        for resistance_level in resistances:
                            if (current_candle["open"] < resistance_level) and current_candle["close"] > resistance_level:
                                reverse_short_at_resistance[symbol].append(r_s_timeframe)
                            
                            if (current_candle["open"] < resistance_level) and (resistance_level + 3*ind.get_spread(symbol) > current_candle["close"] > resistance_level):
                                break_long_at_resistance[symbol].append(r_s_timeframe)

                            if (current_candle["open"] > resistance_level) and (resistance_level - 3*ind.get_spread(symbol) < current_candle["close"] < resistance_level):
                                reverse_short_at_resistance_v2[symbol].append(r_s_timeframe)
                        
                        for support_level in support:                            
                            if (current_candle["open"] > support_level) and (support_level - 3*ind.get_spread(symbol) < current_candle["close"] < support_level):
                                break_short_at_support[symbol].append(r_s_timeframe)
                            
                            if (current_candle["open"] > support_level) and current_candle["close"] < support_level:
                                reverse_long_at_support[symbol].append(r_s_timeframe)
                            
                            if (current_candle["open"] < support_level) and (support_level + 3*ind.get_spread(symbol) > current_candle["close"] > support_level):
                                reverse_long_at_support_v2[symbol].append(r_s_timeframe)
                
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
                            
                            # Reverse V2
                            total_support_tf_long_v2 = set(reverse_long_at_support_v2[symbol])
                            total_resistance_tf_short_v2 = set(reverse_short_at_resistance_v2[symbol])

                            if self.strategy == "break":
                                if len(total_resistance_tf_long) >= 1:
                                    print(f"{symbol.ljust(12)} RL: {'|'.join(map(str, total_resistance_tf_long)).ljust(10)}")
                                    max_timeframe = max(total_resistance_tf_long)
                                    self.long_real_entry(symbol=symbol,
                                                            comment="RL>" + '|'.join(map(str, total_resistance_tf_long)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                                elif len(total_support_tf_short) >= 1:
                                    print(f"{symbol.ljust(12)} SS: {'|'.join(map(str, total_support_tf_short)).ljust(10)}")
                                    max_timeframe = max(total_support_tf_short)
                                    self.short_real_entry(symbol=symbol, 
                                                            comment="SS>" + '|'.join(map(str, total_support_tf_short)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                                # elif len(total_resistance_tf_short_v2) >= 1:
                                #     print(f"{symbol.ljust(12)} RS: {'|'.join(map(str, total_resistance_tf_short_v2)).ljust(10)}")
                                #     max_timeframe = max(total_resistance_tf_short_v2)
                                #     self.short_real_entry(symbol=symbol, 
                                #                             comment="RS>" + '|'.join(map(str, total_resistance_tf_short_v2)), 
                                #                             r_s_timeframe=max_timeframe, 
                                #                             entry_timeframe=max_timeframe)
                                # elif len(total_support_tf_long_v2) >= 1:
                                #     print(f"{symbol.ljust(12)} SL: {'|'.join(map(str, total_support_tf_long_v2)).ljust(10)}")
                                #     max_timeframe = max(total_support_tf_long_v2)
                                #     self.long_real_entry(symbol=symbol, 
                                #                             comment="SL>" + '|'.join(map(str, total_support_tf_long_v2)), 
                                #                             r_s_timeframe=max_timeframe, 
                                #                             entry_timeframe=max_timeframe)
                            elif self.strategy == "reverse":
                                if len(total_resistance_tf_short) >= 1:
                                    print(f"{symbol.ljust(12)} RS: {'|'.join(map(str, total_resistance_tf_short)).ljust(10)}")
                                    max_timeframe = max(total_resistance_tf_short)
                                    self.short_real_entry(symbol=symbol, 
                                                            comment="RS>" + '|'.join(map(str, total_resistance_tf_short)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                                elif len(total_support_tf_long) >= 1:
                                    print(f"{symbol.ljust(12)} SL: {'|'.join(map(str, total_support_tf_long)).ljust(10)}")
                                    max_timeframe = max(total_support_tf_long)
                                    self.long_real_entry(symbol=symbol, 
                                                            comment="SL>" + '|'.join(map(str, total_support_tf_long)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                            elif self.strategy == "auto":
                                timeframe_seperator = [5, 15, 30]
                                # Breakout should have less than 30 and 15 and 5
                                total_resistance_tf_long = [i for i in total_resistance_tf_long if i in timeframe_seperator]
                                total_support_tf_short = [i for i in total_support_tf_short if i in timeframe_seperator]


                                # Reverse should have more than 30 min
                                total_support_tf_long = [i for i in total_support_tf_long if i not in timeframe_seperator]
                                total_resistance_tf_short = [i for i in total_resistance_tf_short if i not in timeframe_seperator]

                                if len(total_resistance_tf_long) >= 2:
                                    print(f"{symbol.ljust(12)} RL: {'|'.join(map(str, total_resistance_tf_long)).ljust(10)}")
                                    self.long_real_entry(symbol=symbol, 
                                                            comment="B>" + '|'.join(map(str, total_resistance_tf_long)), 
                                                            r_s_timeframe=max(total_resistance_tf_long), 
                                                            entry_timeframe=max(total_resistance_tf_long))
                                elif len(total_support_tf_short) >= 2:
                                    print(f"{symbol.ljust(12)} SS: {'|'.join(map(str, total_support_tf_short)).ljust(10)}")
                                    self.short_real_entry(symbol=symbol, 
                                                            comment="B>" + '|'.join(map(str, total_support_tf_short)), 
                                                            r_s_timeframe=max(total_support_tf_short), 
                                                            entry_timeframe=max(total_support_tf_short))
                                elif len(total_resistance_tf_short) >= 2:
                                    print(f"{symbol.ljust(12)} RS: {'|'.join(map(str, total_resistance_tf_short)).ljust(10)}")
                                    self.short_real_entry(symbol=symbol, 
                                                            comment="R>" + '|'.join(map(str, total_resistance_tf_short)), 
                                                            r_s_timeframe=max(total_resistance_tf_short), 
                                                            entry_timeframe=max(total_resistance_tf_short))
                                elif len(total_support_tf_long) >= 2:
                                    print(f"{symbol.ljust(12)} SL: {'|'.join(map(str, total_support_tf_long)).ljust(10)}")
                                    self.long_real_entry(symbol=symbol, 
                                                            comment="R>" + '|'.join(map(str, total_support_tf_long)), 
                                                            r_s_timeframe=max(total_support_tf_long), 
                                                            entry_timeframe=max(total_support_tf_long))
                            elif self.strategy == "ema":
                                if len(total_resistance_tf_long) >= 2:
                                    print(f"{symbol.ljust(12)} RL: {'|'.join(map(str, total_resistance_tf_long)).ljust(10)}")
                                    if ind.ema_direction(symbol, total_resistance_tf_long) == "L":
                                        self.long_real_entry(symbol=symbol, 
                                                            comment="LB>" + '|'.join(map(str, total_resistance_tf_long)), 
                                                            r_s_timeframe=max(total_resistance_tf_long), 
                                                            entry_timeframe=max(total_resistance_tf_long))
                                elif len(total_support_tf_short) >= 2:
                                    print(f"{symbol.ljust(12)} SS: {'|'.join(map(str, total_support_tf_short)).ljust(10)}")
                                    if ind.ema_direction(symbol, total_support_tf_short) == "S":
                                        self.short_real_entry(symbol=symbol, 
                                                            comment="SB>" + '|'.join(map(str, total_support_tf_short)), 
                                                            r_s_timeframe=max(total_support_tf_short), 
                                                            entry_timeframe=max(total_support_tf_short))
                                elif len(total_resistance_tf_short) >= 2:
                                    print(f"{symbol.ljust(12)} RS: {'|'.join(map(str, total_resistance_tf_short)).ljust(10)}")
                                    if ind.ema_direction(symbol, total_resistance_tf_short) == "S":
                                        self.short_real_entry(symbol=symbol, 
                                                            comment="SR>" + '|'.join(map(str, total_resistance_tf_short)), 
                                                            r_s_timeframe=max(total_resistance_tf_short), 
                                                            entry_timeframe=max(total_resistance_tf_short))
                                elif len(total_support_tf_long) >= 2: 
                                    print(f"{symbol.ljust(12)} SL: {'|'.join(map(str, total_support_tf_long)).ljust(10)}")
                                    if ind.ema_direction(symbol, total_support_tf_long) == "L":
                                        self.long_real_entry(symbol=symbol, 
                                                            comment="LR>" + '|'.join(map(str, total_support_tf_long)), 
                                                            r_s_timeframe=max(total_support_tf_long), 
                                                            entry_timeframe=max(total_support_tf_long))
                            elif self.strategy == "smart":
                                level_price = ind.get_mid_price(symbol)
                                if len(total_resistance_tf_long) >= 1:
                                    print(f"{symbol.ljust(12)} RL: {'|'.join(map(str, total_resistance_tf_long)).ljust(10)}")
                                    max_timeframe = max(total_resistance_tf_long)
                                    if ind.understand_direction(symbol, max_timeframe, level_price) is not None:
                                        self.long_real_entry(symbol=symbol, 
                                                            comment="RL>" + '|'.join(map(str, total_resistance_tf_long)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                                elif len(total_support_tf_short) >= 1:
                                    print(f"{symbol.ljust(12)} SS: {'|'.join(map(str, total_support_tf_short)).ljust(10)}")
                                    max_timeframe = max(total_support_tf_short)
                                    if ind.understand_direction(symbol, max_timeframe, level_price) is not None:
                                        self.short_real_entry(symbol=symbol, 
                                                            comment="SS>" + '|'.join(map(str, total_support_tf_short)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                                elif len(total_resistance_tf_short) >= 1:
                                    print(f"{symbol.ljust(12)} RS: {'|'.join(map(str, total_resistance_tf_short)).ljust(10)}")
                                    max_timeframe = max(total_resistance_tf_short)
                                    if ind.understand_direction(symbol, max_timeframe, level_price) is None:
                                        self.short_real_entry(symbol=symbol, 
                                                            comment="RS>" + '|'.join(map(str, total_resistance_tf_short)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                                elif len(total_support_tf_long) >= 1: 
                                    print(f"{symbol.ljust(12)} SL: {'|'.join(map(str, total_support_tf_long)).ljust(10)}")
                                    max_timeframe = max(total_support_tf_long)
                                    if ind.understand_direction(symbol, max_timeframe, level_price) is None:
                                        self.long_real_entry(symbol=symbol, 
                                                            comment="SL>" + '|'.join(map(str, total_support_tf_long)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                            else:
                                raise Exception("Strategy not defined!")
            
            time.sleep(self.timer)
    
if __name__ == "__main__":
    win = AlgoTrader()
    
    if len(sys.argv) > 1:
        win.strategy = sys.argv[1]
        if win.strategy not in ["reverse", "break", "auto", "ema","smart"]:
            raise Exception("Please enter fixed or auto entry time check!")
        
        win.trading_timeframes = [int(i) for i in sys.argv[2].split(",")]

    else:
        # Mean the R&S levels and entry check will be based on the same selected timeframe. Default
        win.strategy = "smart"

        # otherwise timeframe will be default to 4 hours

    win.main()

