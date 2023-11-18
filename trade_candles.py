from statistics import mean 
import math
import indicators as ind
import util as util
import currency_pairs as curr
import sys

from datetime import datetime, timedelta
import pytz
import time

import MetaTrader5 as mt
import mng_pos as mp

class AlgoTrader():
    def __init__(self):
        mt.initialize()
        
        """
        ########################
        Login Credentials 
        #######################
        """
        # Value in USD
        ACCOUNT_SIZE,_, _,_ = ind.get_account_details()
        self.trial_risk = 4 # $4 as trial risk
        self.ratio = 1
        self.risk = ACCOUNT_SIZE/100*0.16 # Risk only 0.25%
        self.half_risk = self.risk/2/2
        self.first_target = 1
        self.second_target = 2 # 1: 2, Ratio
        self.currencies = curr.currencies
        self.indexes = curr.indexes
        self.tag_trial = "trial_entry"
        self.tag_real = "real_entry"
    
    def get_exchange_price(self, exchange):
        ask_price = mt.symbol_info_tick(exchange).ask
        bid_price = mt.symbol_info_tick(exchange).bid
        exchange_rate = round((bid_price + ask_price)/2, 5)
        return exchange_rate
    
    def get_spread(self):
        ask_price = mt.symbol_info_tick(self.symbol).ask
        bid_price = mt.symbol_info_tick(self.symbol).bid
        spread = (ask_price - bid_price)
        return spread
    
    def update_symbol_parameters(self):
        # Check which radio button is selected
        if self.symbol == "US500.cash":
            self.dollor_value = 1.0
            self.spread = round(self.get_spread(), 2)
        elif self.symbol == "UK100.cash":
            self.dollor_value = self.get_exchange_price("GBPUSD")
            self.spread = round(self.get_spread(), 2)
        elif self.symbol == "HK50.cash":
            # self.dollor_value = round(1/self.get_exchange_price("USDHKD"), 4)
            self.dollor_value = round(1/7.8, 4) # Generally 7.8
            self.spread = round(self.get_spread(), 2)
        elif self.symbol == "JP225.cash":
            self.dollor_value = round(1/self.get_exchange_price("USDJPY"), 5)
            self.spread = round(self.get_spread(), 2)
        elif self.symbol == "AUS200.cash":
            self.dollor_value = self.get_exchange_price("AUDUSD")
            self.spread = round(self.get_spread(), 2)
        elif self.symbol == "AUDNZD":
            self.dollor_value = (1/self.get_exchange_price("AUDNZD")) * self.get_exchange_price("AUDUSD")
            self.spread = round(self.get_spread(), 5)
        elif self.symbol == "EURCAD":
            self.dollor_value = (1/self.get_exchange_price("EURCAD")) * self.get_exchange_price("EURUSD")
            self.spread = round(self.get_spread(), 5)
        elif self.symbol == "NZDCAD":
            self.dollor_value = (1/self.get_exchange_price("NZDCAD")) * self.get_exchange_price("NZDUSD")
            self.spread = round(self.get_spread(), 5)
        elif self.symbol == "USDJPY":
            self.dollor_value = 1/self.get_exchange_price("USDJPY")
            self.spread = round(self.get_spread(), 3)
        elif self.symbol == "USDCHF":
            self.dollor_value = 1/self.get_exchange_price("USDCHF")
            self.spread = round(self.get_spread(), 5)
        elif self.symbol == "AUDJPY":
            self.dollor_value = (1/self.get_exchange_price("AUDJPY")) * self.get_exchange_price("AUDUSD")
            self.spread = round(self.get_spread(), 3)
        elif self.symbol == "NZDJPY":
            self.dollor_value = (1/self.get_exchange_price("NZDJPY")) * self.get_exchange_price("NZDUSD")
            self.spread = round(self.get_spread(), 3)
        elif self.symbol == "EURJPY":
            self.dollor_value = (1/self.get_exchange_price("EURJPY")) * self.get_exchange_price("EURUSD")
            self.spread = round(self.get_spread(), 3)
        elif self.symbol == "GBPJPY":
            self.dollor_value = (1/self.get_exchange_price("GBPJPY")) * self.get_exchange_price("GBPUSD")
            self.spread = round(self.get_spread(), 3)
        elif self.symbol == "XAUUSD":
            # Added 2, Since it was picking the whole value
            self.dollor_value = 2/self.get_exchange_price("XAUUSD")
            self.spread = round(self.get_spread(), 5)
        elif self.symbol == "EURUSD":
            self.dollor_value = self.get_exchange_price("EURUSD")
            self.spread = round(self.get_spread(), 5)
        elif self.symbol == "USDCAD":
            self.dollor_value = 1/self.get_exchange_price("USDCAD")
            self.spread = round(self.get_spread(), 5)
        elif self.symbol == "AUDUSD": 
            self.dollor_value = 1.6 * self.get_exchange_price("AUDUSD")# TODO the 1.6 factor has to be changed dynamically
            self.spread = round(self.get_spread(), 5)
        elif self.symbol == "GBPUSD":
            self.dollor_value = self.get_exchange_price("GBPUSD")
            self.spread = round(self.get_spread(), 5)
        elif self.symbol == "EURNZD":
            self.dollor_value = (1/self.get_exchange_price("EURNZD")) * self.get_exchange_price("EURUSD")
            self.spread = round(self.get_spread(), 5)
        elif self.symbol == "CHFJPY":
            self.dollor_value = 1/self.get_exchange_price("CHFJPY")/ self.get_exchange_price("USDCHF")
            self.spread = round(self.get_spread(), 3)
        else:
            raise Exception(f"{self.symbol} don't have conditions")
        
    def get_mid_price(self):
        try:
            ask_price = mt.symbol_info_tick(self.symbol).ask
            bid_price = mt.symbol_info_tick(self.symbol).bid
            mid_price = (ask_price + bid_price)/2
            
            if self.symbol in self.currencies:
                round_factor = 5
                
                if self.symbol in ["XAUUSD"]:
                    round_factor = 2
                
                entry_price = round((mid_price), round_factor)
            else:
                entry_price = round((mid_price) * 10)/10

            return entry_price
        except Exception:
            return None
    
    def calculate_slots(self, points_in_stop):
        positions = self.risk/(points_in_stop * self.dollor_value)
        return float(positions) 
    
    def calculate_trial_slots(self, points_in_stop):
        # We are having seperate lot calculator to have trail risk seperate from real risk
        positions = self.trial_risk/(points_in_stop * self.dollor_value)
        return float(positions)

   
    def print_order_log(self, result, request={}):
        if result:
            if result.retcode != mt.TRADE_RETCODE_DONE:
                error_string = f"Error: {result.comment}"
                print(error_string)
                print(request)
        else:
            print("Error with response!")

    def round_price_value(self, stop_price):
        if self.symbol in self.currencies:
            if self.symbol in curr.jpy_currencies:
                return round(stop_price, 3)
            return round(stop_price, 5)
        else:
            return round(stop_price, 2)

    def long_trial_entry(self):
        entry_price = self.get_mid_price()
            
        if entry_price:
            _, previous_bar_low, _ = ind.get_stop_range(self.symbol)
            stop_price = self.round_price_value(previous_bar_low)
            
            if entry_price > stop_price:                
                try:
                    if self.symbol in self.currencies:
                        points_in_stop = round(entry_price - stop_price, 5)
                        position_size = self.calculate_trial_slots(points_in_stop)/100000
                    else:
                        points_in_stop = round(entry_price - stop_price)
                        position_size = self.calculate_trial_slots(points_in_stop)
                    
                    lots =  round(position_size, 2)

                    target_price = self.round_price_value(entry_price +  2 * points_in_stop)
                    
                    order_request = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": lots,
                        "type": mt.ORDER_TYPE_BUY_LIMIT,
                        "price": entry_price,
                        "sl": stop_price,
                        "tp": target_price,
                        "comment": self.tag_trial,
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }
                    
                    request_log = mt.order_send(order_request)
                    self.print_order_log(request_log, order_request)
                except Exception as e:
                    print(e)
    
    def long_real_entry(self):
        entry_price = self.get_mid_price()
            
        if entry_price:
            _, previous_bar_low, _ = ind.get_stop_range(self.symbol)
            stop_price = self.round_price_value(previous_bar_low)
            
            if entry_price > stop_price:                
                try:
                    if self.symbol in self.currencies:
                        points_in_stop = round(entry_price - stop_price, 5)
                        position_size = self.calculate_slots(points_in_stop)/100000
                    else:
                        points_in_stop = round(entry_price - stop_price)
                        position_size = self.calculate_slots(points_in_stop)
                    
                    target_price1 = self.round_price_value(entry_price + self.first_target * points_in_stop)
                    target_price2 = self.round_price_value(entry_price + self.second_target * points_in_stop)
                    
                    lots =  round(position_size/2, 2)

                    request1 = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": lots,
                        "type": mt.ORDER_TYPE_BUY_LIMIT,
                        "price": entry_price,
                        "sl": stop_price,
                        "tp": target_price1, # FLOAT
                        "comment": self.tag_real,
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }

                    request2 = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": lots,
                        "type": mt.ORDER_TYPE_BUY_LIMIT,
                        "price": entry_price,
                        "sl": stop_price,
                        "tp": target_price2,
                        "comment": self.tag_real,
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }
                    
                    
                    res1 = mt.order_send(request1)
                    self.print_order_log(res1, request1)
                    res2 = mt.order_send(request2)
                    self.print_order_log(res2, request2)
                except Exception as e:
                    print(f"Long entry exception: {e}")
            
    def short_trial_entry(self):
        entry_price = self.get_mid_price()
        
        if entry_price:
            previous_bar_high, _, _ = ind.get_stop_range(self.symbol)
            stop_price = self.round_price_value(previous_bar_high)

            if stop_price > entry_price:
                try:
                    if self.symbol in self.currencies:
                        points_in_stop = round(stop_price - entry_price, 5)
                        position_size = self.calculate_trial_slots(points_in_stop)/100000
                    else:
                        points_in_stop = round(stop_price - entry_price)
                        position_size = self.calculate_trial_slots(points_in_stop)
                    
                    
                    target_price = self.round_price_value(entry_price -  2 * points_in_stop)

                    lots =  round(position_size, 2)

                    order_request = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": lots,
                        "type": mt.ORDER_TYPE_SELL_LIMIT,
                        "price": entry_price,
                        "sl": stop_price,
                        "tp": target_price,
                        "comment": self.tag_trial,
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }
                    
                    request_log = mt.order_send(order_request)
                    self.print_order_log(request_log, order_request)
                except Exception as e:
                    print(e)

    def short_real_entry(self):
        entry_price = self.get_mid_price()
        
        if entry_price:
            previous_bar_high, _, _ = ind.get_stop_range(self.symbol)
            stop_price = self.round_price_value(previous_bar_high)

            if stop_price > entry_price:
                
                try:
                    # print(f"ENTRY: {entry_price} STOP: {stop_price}")
                    
                    if self.symbol in self.currencies:
                        points_in_stop = round(stop_price - entry_price, 5)
                        position_size = self.calculate_slots(points_in_stop)/100000
                    else:
                        points_in_stop = round(stop_price - entry_price)
                        position_size = self.calculate_slots(points_in_stop)
                    
                    
                    target_price1 = self.round_price_value(entry_price - self.first_target * points_in_stop)
                    target_price2 = self.round_price_value(entry_price - self.second_target * points_in_stop)

                    lots =  round(position_size/2, 2)

                    request1 = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": lots,
                        "type": mt.ORDER_TYPE_SELL_LIMIT,
                        "price": entry_price,
                        "sl": stop_price,
                        "tp": target_price1,
                        "comment": self.tag_real,
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }
                    
                    request2 = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": lots,
                        "type": mt.ORDER_TYPE_SELL_LIMIT,
                        "price": entry_price,
                        "sl": stop_price,
                        "tp": target_price2,
                        "comment": self.tag_real,
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }

                    res1 = mt.order_send(request1)
                    self.print_order_log(res1, request1)
                    res2 = mt.order_send(request2)
                    self.print_order_log(res2, request2)
                except Exception as e:
                    print(e)

    def real_trade_entry(self):
        print(f"\n-------  Real entry check -------------")
        
        positions = mt.positions_get()
        # check existing real orders
        existing_real_orders = list(set([i.symbol for i in mt.positions_get() if i.comment == self.tag_real]))
        
        for obj in positions:
            # If the current position size is less than the half of the stop, Also once after the 1R hit, If the initial plan changed! exit!
            # Also check the current one don't have any real orders
            if (obj.comment == self.tag_trial) and (obj.symbol not in existing_real_orders):
                # If profit pass 1/2 of the stop or 0.5R, considered as valid entry
                if obj.profit > self.trial_risk/2:        
                    try:
                        # Set trade symbol object
                        self.symbol = obj.symbol
                        self.enable_symbol()
                        self.update_symbol_parameters()
                        if obj.type == 0:
                            self.long_real_entry()
                        if obj.type == 1:
                            self.short_real_entry()
                    except Exception as e:
                        print(f"Validated entry Error: {obj.symbol} {e}")
                        
                
    def enable_symbol(self):
        if not mt.symbol_select(self.symbol,True):
            print("symbol_select({}}) failed, exit", self.symbol)

    def main(self):
        selected_symbols = list(set(self.currencies + self.indexes))
        
        while True:
            print(f"\n-------  Executed @ {datetime.now().strftime('%H:%M:%S')}------------------")
            
            is_market_open, is_market_close = util.get_market_status()            
            
            
            account_size, equity, free_margin, total_active_profit = ind.get_account_details()
            account_1_percent = account_size * 1/100
            account_2_percent = account_size * 2/100

            # We need to take the 2% of the balance as daily max loss
            # Fail Safe
            # if equity <= account_size + (account_2_percent):
            #     mp.close_positions()
            #     sys.exit()

            if is_market_close:
                print("Market Close!")
                mp.close_positions()

            if is_market_open and not is_market_close:                
                # Close all the position, If current profit reach more than 1% and re evaluate
                if total_active_profit > account_1_percent:
                    mp.close_positions()
                    
                    # If closed positions profit is more than 2% then exit the app. Done for today!
                    if util.get_today_profit() > account_2_percent:
                        sys.exit()
                
                mp.exist_on_initial_plan_changed()
                mp.cancel_all_pending_orders()
                mp.breakeven_1R_positions()
                
                """
                Check all the existing positions
                1. Case 1: Only initial trial trade exist
                2. Case 2: Only real trade exist
                3. Case 3: Both trail and real trade exist
                Exist considered as symbols which are not exist in trail or real (any)
                """
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                
                _, current_hour, _ = util.get_gmt_time()
                
                for symbol in selected_symbols:
                    if symbol not in existing_positions:
                
                        # Don't trade US500.cash before GMT -2 time 10, or 3AM US Time
                        if current_hour <= 10 and symbol in ["US500.cash", "UK100.cash"]:
                            continue

                        self.symbol = symbol
                        self.enable_symbol()
                        
                        try:
                            self.update_symbol_parameters()
                            signal = ind.get_candle_signal(self.symbol)
                            
                            if signal:
                                if signal == "L":
                                    self.long_trial_entry()
                                elif signal == "S":
                                    self.short_trial_entry()
                        except Exception as e:
                            print(f"{symbol} Error: {e}")

                self.real_trade_entry()
            
            time.sleep(2*60)
    
if __name__ == "__main__":
    win = AlgoTrader()
    win.main()
    # win.symbol = "AUDJPY"
    # win.update_symbol_parameters()
    # win.long_entry_test()
    # win.scale_out_positions()
    # print(win.calculate_slots(3.89)/100000)
    


