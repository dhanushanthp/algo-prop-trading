from statistics import mean 
import math
import indicators as ind
import util as util
import currency_pairs as curr
import sys
import client

from datetime import datetime, timedelta
import pytz
import time

import MetaTrader5 as mt
import mng_pos as mp

class AlgoTrader():
    def __init__(self):
        mt.initialize()

        # Value in USD
        ACCOUNT_SIZE,_, _,_ = ind.get_account_details()
        self.trial_risk = 4 # $4 as trial risk
        # self.ratio = 1
        self.risk = ACCOUNT_SIZE/100*0.16 # Risk only 0.25%
        self.account_1_percent = ACCOUNT_SIZE * 1/100
        self.account_2_percent = ACCOUNT_SIZE * 2/100
        self.half_risk = self.risk/2/2
        # self.first_target = 1
        # self.second_target = 2 # 1: 2, Ratio
        self.currencies = curr.currencies
        self.indexes = curr.indexes
        self.tag_trial = "trial_entry"
        self.tag_real = "real_entry"
        self.r_r = 2
    
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
    
    def calculate_lots(self, symbol, entry_price, stop_price, real=True):
        risk = self.risk if real else self.trial_risk
        dollor_value = mp.get_dollar_value(symbol)
        
        points_in_stop = abs(entry_price-stop_price)
        
        lots = risk/(points_in_stop * dollor_value)
        
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

    def long_trial_entry(self, symbol):
        entry_price = self.get_mid_price(symbol)
            
        if entry_price:
            _, previous_bar_low, _ = ind.get_stop_range(symbol)
            stop_price = self.round_price_value(symbol, previous_bar_low)
            
            if entry_price > stop_price:                
                try:
                                            
                    points_in_stop, lots = self.calculate_lots(symbol= symbol, entry_price=entry_price, stop_price=stop_price, real=False)
                    target_price = self.round_price_value(symbol, entry_price +  2 * points_in_stop)
                    
                    # any lots in 2 decimal value
                    lots = round(lots, 2)
                    
                    order_request = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": symbol,
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
    
    def long_real_entry(self, symbol):
        entry_price = self.get_mid_price(symbol=symbol)
            
        if entry_price:
            _, previous_bar_low, _ = ind.get_stop_range(symbol)
            stop_price = self.round_price_value(symbol, previous_bar_low)
            
            if entry_price > stop_price:                
                try:
                                      
                    points_in_stop, lots = self.calculate_lots(symbol=symbol, entry_price=entry_price, stop_price=stop_price, real=True)
                    
                    # target_price1 = self.round_price_value(entry_price + self.first_target * points_in_stop)
                    # target_price2 = self.round_price_value(entry_price + self.second_target * points_in_stop)
                    
                    lots =  round(lots/self.r_r, 2)
                    
                    for r_r in range(1, self.r_r + 1):
                        order_request = {
                            "action": mt.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt.ORDER_TYPE_BUY_LIMIT,
                            "price": entry_price,
                            "sl": stop_price,
                            "tp": self.round_price_value(symbol, entry_price + r_r * points_in_stop),
                            "comment": self.tag_real,
                            "type_time": mt.ORDER_TIME_GTC,
                            "type_filling": mt.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt.order_send(order_request)
                        self.print_order_log(request_log, order_request)
                except Exception as e:
                    print(f"Long entry exception: {e}")
            
    def short_trial_entry(self, symbol):
        entry_price = self.get_mid_price(symbol)
        
        if entry_price:
            previous_bar_high, _, _ = ind.get_stop_range(symbol)
            stop_price = self.round_price_value(symbol, previous_bar_high)

            if stop_price > entry_price:
                try:                 
                    points_in_stop, lots = self.calculate_lots(symbol=symbol, entry_price=entry_price, stop_price=stop_price, real=False)
                    # any lots in 2 decimal value
                    lots = round(lots, 2)
                    
                    target_price = self.round_price_value(symbol, entry_price -  2 * points_in_stop)
                    
                    order_request = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": symbol,
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

    def short_real_entry(self, symbol):
        entry_price = self.get_mid_price(symbol)
        
        if entry_price:
            previous_bar_high, _, _ = ind.get_stop_range(symbol)
            stop_price = self.round_price_value(symbol, previous_bar_high)

            if stop_price > entry_price:
                try:                    
                    points_in_stop, lots = self.calculate_lots(symbol=symbol, entry_price=entry_price, stop_price=stop_price, real=True)
                    
                    # target_price1 = self.round_price_value(entry_price - self.first_target * points_in_stop)
                    # target_price2 = self.round_price_value(entry_price - self.second_target * points_in_stop)

                    lots =  round(lots/self.r_r, 2)

                    for r_r in range(1, self.r_r + 1):
                        order_request = {
                            "action": mt.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt.ORDER_TYPE_SELL_LIMIT,
                            "price": entry_price,
                            "sl": stop_price,
                            "tp": self.round_price_value(symbol, entry_price - r_r * points_in_stop),
                            "comment": self.tag_real,
                            "type_time": mt.ORDER_TIME_GTC,
                            "type_filling": mt.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt.order_send(order_request)
                        self.print_order_log(request_log, order_request)
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
                        if obj.type == 0:
                            self.long_real_entry(symbol=obj.symbol)
                        if obj.type == 1:
                            self.short_real_entry(symbol=obj.symbol)
                    except Exception as e:
                        print(f"Validated entry Error: {obj.symbol} {e}")

    def main(self):
        selected_symbols = list(set(self.currencies + self.indexes))
        
        while True:
            print(f"\n-------  Executed @ {datetime.now().strftime('%H:%M:%S')}------------------")
            
            is_market_open, is_market_close = util.get_market_status()            
            
            account_size, equity, free_margin, total_active_profit = ind.get_account_details()

            # Fail Safe
            if equity <= account_size - self.account_2_percent:
                mp.close_all_positions()
                sys.exit()

            if is_market_close:
                print("Market Close!")
                mp.close_all_positions()

            if is_market_open and not is_market_close:                
                # Close all the position, If current profit reach more than 1% and re evaluate
                if total_active_profit > self.account_1_percent:
                    mp.close_all_positions()
                    
                    # If closed positions profit is more than 2% then exit the app. Done for today!
                    if util.get_today_profit() > self.account_2_percent:
                        sys.exit()
                
                mp.exist_on_initial_plan_changed()
                mp.cancel_all_pending_orders()
                mp.breakeven_1R_positions()
                mp.close_slave_positions()
                
                """
                Check all the existing positions
                1. Case 1: Only initial trial trade exist
                2. Case 2: Only real trade exist
                3. Case 3: Both trail and real trade exist
                Exist considered as symbols which are not exist in trail or real (any)
                """
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                server_positions = client.get_active_positions()
                
                _, current_hour, _ = util.get_gmt_time()
                
                for symbol in selected_symbols:
                    if symbol not in (existing_positions + server_positions):
                
                        # Don't trade US500.cash before GMT -2 time 10, or 3AM US Time
                        if current_hour <= 10 and symbol in ["US500.cash", "UK100.cash"]:
                            continue
                        
                        try:
                            signal = ind.get_candle_signal(symbol)
                            
                            if signal and (symbol not in client.get_all_positions()):
                                if signal == "L":
                                    # self.long_trial_entry(symbol=symbol)
                                    client.async_trigger_order_entry(symbol=symbol, direction="L")
                                elif signal == "S":
                                    # self.short_trial_entry(symbol=symbol)
                                    client.async_trigger_order_entry(symbol=symbol, direction="S")
                        except Exception as e:
                            print(f"{symbol} Error: {e}")

                self.real_trade_entry()
            
            time.sleep(2*60)
    
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
    


