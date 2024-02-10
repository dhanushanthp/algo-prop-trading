import os
from statistics import mean 
import math
import sys
import MetaTrader5 as mt
import pandas as pd
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
from objects.Magazine import Magazine
from objects.Directions import Directions

class SniperReloaded():
    def __init__(self):
        # MetaTrader initialization
        mt.initialize()

        # Default values
        self.target_ratio = 3.0  # Default 1:0.5 Ratio
        self.stop_ratio = 1.0
        self.immidiate_exit = False
        self.timer = 30
        self.retries = 0

        # External dependencies
        self.risk_manager = risk_manager.RiskManager(profit_split=1)
        self.magazine = Magazine()
        self.alert = Slack()
        self.monitor = Monitor()
        self.file_util = FileUtils()

        # Account information
        self.account_name = ind.get_account_name()
        self.previous_equity = None

        # Expected reward for the day
        self.fixed_initial_account_size = self.risk_manager.account_size

        # Default
        self.trading_timeframe = 60

        # Take the profit as specific RR ratio
        self.partial_profit_rr = False
        self.partial_live_actual = False
        self.partial_rr=0.1

        self.snipper_levels = {}
   
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
                print(error_string)
                # self.alert.send_msg(f"ERR: {self.account_name} <br> {error_string} <br> ```{request_str}```")

    def long_real_entry(self, symbol, break_level):
        entry_price = self.get_entry_price(symbol=symbol)

        if entry_price :
            _, stop_price, is_strong_candle, _, _ = ind.get_stop_range(symbol=symbol, timeframe=self.trading_timeframe)
            
            stop_price = self._round(symbol, stop_price)

            if is_strong_candle:    
                if entry_price > stop_price:
                    try:
                        print(f"{symbol.ljust(12)}: {Directions.LONG}")        
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
                            "comment": f"{break_level}",
                            "magic": self.trading_timeframe,
                            "type_time": mt.ORDER_TIME_GTC,
                            "type_filling": mt.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt.order_send(order_request)
                        self.error_logging(request_log, order_request)
                        return True
                    except Exception as e:
                        print(f"Long entry exception: {e}")
            else:
                return False

    def short_real_entry(self, symbol, break_level):
        entry_price = self.get_entry_price(symbol)
        
        if entry_price:
            stop_price, _, is_strong_candle, _, _ = ind.get_stop_range(symbol=symbol, timeframe=self.trading_timeframe)
            stop_price = self._round(symbol, stop_price)

            if is_strong_candle:
                if stop_price > entry_price:
                    try:
                        print(f"{symbol.ljust(12)}: {Directions.SHORT}")      
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
                            "comment": f"{break_level}",
                            "magic":self.trading_timeframe,
                            "type_time": mt.ORDER_TIME_GTC,
                            "type_filling": mt.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt.order_send(order_request)
                        self.error_logging(request_log, order_request)
                        return True
                    except Exception as e:
                        print(e)
            else:
                return False
    
    def main(self):
        selected_symbols = ind.get_ordered_symbols()
        
        while True:
            print(f"\n------- {config.local_ip} {util.get_current_time().strftime('%H:%M:%S')} in {self.trading_timeframe} TFs & PartialProfit ({self.partial_rr} RR): {self.partial_profit_rr} {self.partial_live_actual}------------------")
            is_market_open, is_market_close = util.get_market_status()
            _,equity,_,profit = ind.get_account_details()
            rr = (equity - self.fixed_initial_account_size)/self.risk_manager.risk_of_an_account
            pnl = (equity - self.risk_manager.account_size)
            print(f"{'Acc Trail Loss'.ljust(20)}: {self.risk_manager.account_risk_percentage}%")
            print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")
            print(f"{'Acc at Risk'.ljust(20)}: {'{:,}'.format(round(((self.risk_manager.get_max_loss() - self.fixed_initial_account_size)/self.fixed_initial_account_size) * 100, 2))}%, ${self.risk_manager.get_max_loss()}")
            print(f"{'Next Trail at'.ljust(20)}: ${'{:,}'.format(round(self.risk_manager.get_max_loss() + self.risk_manager.risk_of_an_account))}")
            print(f"{'Risk:Reward'.ljust(20)}: {round(rr, 3)}")
            print(f"{'PnL'.ljust(20)}: ${round(pnl, 2)}")

            # Record PnL
            if pnl != 0:
                with open(f'{config.local_ip}_{util.get_current_time().strftime("%Y%m%d")}.csv', 'a') as file:
                    file.write(f"{util.get_current_time().strftime('%Y/%m/%d %H:%M:%S')},break,{self.retries},{round(rr, 3)},{round(pnl, 3)}\n")

            # Each position trail stop
            mp.adjust_positions_trailing_stops(self.target_ratio) 

            if self.partial_live_actual:
                if rr > 1.2:
                    self.immidiate_exit = True
                    mp.close_all_positions()
                    time.sleep(30) # Take some time for the account to digest the positions
                    current_account_size,_,_,_ = ind.get_account_details()
                    self.alert.send_msg(f"{self.account_name} Early Exit with {current_account_size}")


            # Phoenix Strategy
            if self.partial_profit_rr:
                if rr > self.partial_rr:
                    self.alert.send_msg(f"{self.account_name} RR triggered, {pnl}")
                    mp.close_all_positions()
                    time.sleep(30) # Take some time for the account to digest the positions
                    current_account_size,_,_,_ = ind.get_account_details()
                    # Set the balance as current account size, This will reset the RR
                    self.fixed_initial_account_size = current_account_size
                    # Don't change the risk of an account. Until next day, So we don't need to reinitialize risk manager
                    self.retries += 1


            if self.risk_manager.has_daily_maximum_risk_reached():
                self.retries += 1
                mp.close_all_with_condition()
                time.sleep(30) # Take some time for the account to digest the positions

                # The risk reward calclualted based on initial risk                
                self.alert.send_msg(f"{self.account_name}: Exit {self.retries}, RR: {round(rr, 2)}, PnL: {round(pnl, 2)}")
                
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
            

            #  and (num_existing_positions <= config.position_split_of_account_risk)
            if is_market_open and (not is_market_close) and (not self.immidiate_exit):
                mp.cancel_all_pending_orders()
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))

                break_long_at_resistance = {}
                break_short_at_support = {}

                for symbol in selected_symbols:
                    break_long_at_resistance[symbol] = []
                    break_short_at_support[symbol] = []

                    king_of_levels = ind.get_king_of_levels(symbol=symbol)

                    resistances = king_of_levels[0]
                    support = king_of_levels[1]

                    current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(self.trading_timeframe), 0, 1)[-1]

                    for resistance_level in resistances:
                        if current_candle["open"] < resistance_level and current_candle["close"] > resistance_level:
                            print(f"{symbol.ljust(12)} Resistance: {resistance_level}")
                            _, stop_price, _, _, _ = ind.get_stop_range(symbol=symbol, timeframe=self.trading_timeframe)
                            stop_price = self._round(symbol, stop_price)
                            self.magazine.load_magazine(target=symbol, sniper_trigger_level=resistance_level, sniper_level=stop_price, shoot_direction=Directions.LONG)
                            break
                    
                    for support_level in support:               
                        if current_candle["open"] > support_level and current_candle["close"] < support_level:
                            print(f"{symbol.ljust(12)} Support: {support_level}")
                            stop_price, _, _, _, _ = ind.get_stop_range(symbol=symbol, timeframe=self.trading_timeframe)
                            stop_price = self._round(symbol, stop_price)
                            self.magazine.load_magazine(target=symbol, sniper_trigger_level=support_level, sniper_level=stop_price, shoot_direction=Directions.SHORT)
                            break

                self.magazine.show_magazine()
                symbols_to_remove = []

                for symbol in self.magazine.get_magazine():
                    if symbol not in existing_positions:
                        bullet = self.magazine.get_magazine()[symbol]
                        break_level = bullet.sniper_trigger_level
                        direction = bullet.shoot_direction

                        # Get current candle OHLC
                        current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(self.trading_timeframe), 0, 1)[-1]

                        # Trade Decision
                        if (current_candle["open"] > break_level and current_candle["close"] < break_level) or (current_candle["open"] < break_level and current_candle["close"] > break_level):
                            if direction == "long":
                                self.long_real_entry(symbol=symbol, break_level=break_level)
                            else:
                                self.short_real_entry(symbol=symbol, break_level=break_level)
                    else:
                        symbols_to_remove.append(symbol)

                #Remove the exisiting positions
                for symbol in symbols_to_remove:
                    self.magazine.unload_magazine(symbol)

            time.sleep(self.timer)
    
if __name__ == "__main__":
    win = SniperReloaded()

    parser = argparse.ArgumentParser(description='Example script with named arguments.')

    parser.add_argument('--partial_profit_rr', type=str, help='Partial Profit RR')
    parser.add_argument('--partial_live_actual', type=str, help='Partial Profit RR')
    parser.add_argument('--partial_rr', type=float, help='Partial Profit RR')
    parser.add_argument('--timeframe', type=str, help='Selected timeframe for trade')
    args = parser.parse_args()
    
    win.trading_timeframe = int(args.timeframe)
    win.partial_profit_rr = util.boolean(args.partial_profit_rr)
    win.partial_rr = args.partial_rr 
    win.partial_live_actual = util.boolean(args.partial_live_actual)

    win.main()

