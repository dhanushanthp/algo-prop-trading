from statistics import mean 
import math
import indicators as ind
import util as util
import currency_pairs as curr
import sys

from datetime import datetime, timedelta
import account as acc
import pytz
import time

import MetaTrader5 as mt
import mng_pos as mp

class AlgoTrader():
    def __init__(self):
        mt.initialize()

        # Value in USD
        ACCOUNT_SIZE,_, _,_ = ind.get_account_details()
        self.risk = ACCOUNT_SIZE/100*acc.risk_percentage_real # Risk only 0.25%
        self.account_1_percent = ACCOUNT_SIZE * 1/100
        self.account_2_percent = ACCOUNT_SIZE * 2/100
        self.currencies = curr.currencies
        self.indexes = curr.indexes
        self.tag_trial = "trial_entry"
        self.tag_real = "real_entry"
        self.r_r = 2
        self.num_of_parallel_trades = 3
    
    def get_exchange_price(self, exchange):
        ask_price = mt.symbol_info_tick(exchange).ask
        bid_price = mt.symbol_info_tick(exchange).bid
        exchange_rate = round((bid_price + ask_price)/2, 5)
        return exchange_rate
        
    def get_mid_price(self, symbol):
        try:
            ask_price = mt.symbol_info_tick(symbol).ask
            bid_price = mt.symbol_info_tick(symbol).bid
            mid_price = (ask_price + bid_price)/2
            
            if symbol in self.currencies:
                round_factor = 5
                
                if symbol in ["XAUUSD"]:
                    round_factor = 2
                
                entry_price = round((mid_price), round_factor)
            else:
                entry_price = round((mid_price) * 10)/10

            return entry_price
        except Exception:
            return None
    
    def calculate_lots(self, symbol, entry_price, stop_price):        
        dollor_value = mp.get_dollar_value(symbol)
        points_in_stop = abs(entry_price-stop_price)/2
        lots = self.risk/(points_in_stop * dollor_value)
        
        if symbol in self.currencies:
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

    def round_price_value(self, symbol, stop_price):
        if symbol in self.currencies:
            if symbol in curr.jpy_currencies:
                return round(stop_price, 3)
            return round(stop_price, 5)
        else:
            return round(stop_price, 2)
    
    def long_real_entry(self, symbol, comment="NA"):
        entry_price = self.get_mid_price(symbol=symbol)

        if entry_price:
            _, previous_bar_low, previous_candle = ind.get_stop_range(symbol)
            
            # The idea is reverse and quick profit!
            if previous_candle and previous_candle == "S":
                magic_number = 1 if previous_candle == "L" else 2
                stop_price = self.round_price_value(symbol, previous_bar_low)
                
                if entry_price > stop_price:                
                    try:
                        print(f"{symbol}: LONG")        
                        points_in_stop, lots = self.calculate_lots(symbol=symbol, entry_price=entry_price, stop_price=stop_price)
                        
                        lots =  round(lots, 2)
                        
                        # Re evaluate the stop distance
                        stop_price = self.round_price_value(symbol, stop_price + points_in_stop)
                        
                        order_request = {
                            "action": mt.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt.ORDER_TYPE_BUY_LIMIT,
                            "price": entry_price,
                            "sl": stop_price,
                            "tp": self.round_price_value(symbol, entry_price + points_in_stop),
                            "comment": comment,
                            "magic":magic_number,
                            "type_time": mt.ORDER_TIME_GTC,
                            "type_filling": mt.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt.order_send(order_request)
                        self.print_order_log(request_log, order_request)
                        return True
                    except Exception as e:
                        print(f"Long entry exception: {e}")
            else:
                print(f"{''.ljust(12)}: Skipped!")
                return False

    def short_real_entry(self, symbol, comment="NA"):
        entry_price = self.get_mid_price(symbol)
        
        if entry_price:
            previous_bar_high, _, previous_candle = ind.get_stop_range(symbol)
            
            if previous_candle and previous_candle == "L":
                magic_number = 1 if previous_candle == "L" else 2
                stop_price = self.round_price_value(symbol, previous_bar_high)

                if stop_price > entry_price:
                    try:            
                        print(f"{symbol}: SHORT")        
                        points_in_stop, lots = self.calculate_lots(symbol=symbol, entry_price=entry_price, stop_price=stop_price)
                        
                        # Re evaluate the stop distance
                        stop_price = self.round_price_value(symbol, stop_price-points_in_stop)
                        lots =  round(lots, 2)

                        order_request = {
                            "action": mt.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt.ORDER_TYPE_SELL_LIMIT,
                            "price": entry_price,
                            "sl": stop_price,
                            "tp": self.round_price_value(symbol, entry_price - points_in_stop),
                            "comment": comment,
                            "magic":magic_number,
                            "type_time": mt.ORDER_TIME_GTC,
                            "type_filling": mt.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt.order_send(order_request)
                        self.print_order_log(request_log, order_request)
                        return True
                    except Exception as e:
                        print(e)
            else:
                print(f"{''.ljust(12)}: Skipped!")
                return False
    
    def main(self):
        selected_symbols = list(set(self.currencies + self.indexes))
        
        while True:
            print(f"\n-------  Executed @ {datetime.now().strftime('%H:%M:%S')}------------------")
            
            is_market_open, is_market_close = util.get_market_status()            
            
            account_size, equity, _, total_active_profit = ind.get_account_details()

            # Fail Safe
            if equity <= account_size - self.account_2_percent:
                mp.close_all_positions()
                sys.exit()

            if is_market_close:
                print("Market Close!")
                mp.close_all_positions()
            
            if is_market_open and not is_market_close:
                    
                # If closed positions profit is more than 2% then exit the app. Done for today!
                # if util.get_today_profit() > self.account_2_percent:
                #     sys.exit()                

                # mp.exist_on_initial_plan_changed()
                mp.cancel_all_pending_orders()
                
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                print(f"Current Positions: {existing_positions}")
                
                _, current_hour, _ = util.get_gmt_time()
                # Only take 4 trades at a time. So we can track the performance of the startegy
                if len(existing_positions) < self.num_of_parallel_trades:
                    selected_strategy = mp.strategy_selector()
                    print(f"STRATEGY: {selected_strategy.upper()}")
                    
                    for symbol in selected_symbols:
                        # This helps to manage one order at a time rather sending bulk order to server
                        active_orders = len(mt.orders_get())
                        if symbol not in existing_positions:
                            # Don't trade US500.cash before GMT -2 time 10, or 3AM US Time
                            if current_hour <= 10 and symbol in ["US500.cash", "UK100.cash"]:
                                continue
                            
                            try:
                                signal = ind.get_candle_signal(symbol)
                                
                                # Only enter 1 order at a time along with the signal
                                if signal and active_orders < 1:
                                    if selected_strategy == "reverse":                                    
                                        if signal == "L":
                                            if self.short_real_entry(symbol=symbol, comment="reverse"):
                                                # Make sure we make only 1 trade at a time
                                                break 
                                        elif signal == "S":
                                            if self.long_real_entry(symbol=symbol, comment="reverse"):
                                                # Make sure we make only 1 trade at a time
                                                break
                                    elif selected_strategy == "trend":  
                                        if signal == "L":
                                            if self.long_real_entry(symbol=symbol, comment="trend"):
                                                # Make sure we make only 1 trade at a time
                                                break 
                                        elif signal == "S":
                                            if self.short_real_entry(symbol=symbol, comment="trend"):
                                                # Make sure we make only 1 trade at a time
                                                break
                                    else:
                                        print("No confirmation from trend!")
                            except Exception as e:
                                print(f"{symbol.ljust(12)} Error: {e}")
            
            time.sleep(30)
    
if __name__ == "__main__":
    win = AlgoTrader()
    win.main()
    # symbol = "AUDJPY"
    # win.long_trial_entry(symbol=symbol)
    # win.long_real_entry(symbol=symbol)
    # win.short_trial_entry(symbol=symbol)
    # win.short_real_entry(symbol=symbol)
    # win.update_symbol_parameters()
    # win.long_entry_test()
    # win.scale_out_positions()
    # print(win.calculate_slots(3.89)/100000)
    


