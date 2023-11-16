from statistics import mean 
import math
import indicators as ind
import util as util
import currency_pairs as curr

from datetime import datetime, timedelta
import pytz
import time

import MetaTrader5 as mt
import mng_pos as mp

class TradeCandle():
    def __init__(self):
        mt.initialize()
        
        """
        ########################
        Login Credentials 
        #######################
        """
        # Value in USD
        ACCOUNT_SIZE, _,_ = ind.get_account_details()
        self.ratio = 1
        self.risk = ACCOUNT_SIZE/100*0.25 # Risk only 0.25%
        self.first_target = 1
        self.second_target = 2 # 1: 2, Ratio
        self.currencies = curr.currencies
        self.indexes = curr.indexes
    
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
    
    def get_lstop_price(self):
        limit_price = float(self.entry_price_txt.text())
        return limit_price
    
    def get_sstop_price(self):
        stop_price = round(float(self.stop_price_txt.text()), 4)
        return stop_price
    
    def calculate_slots(self, points_in_stop):
        positions = self.risk/(points_in_stop * self.dollor_value)
        return float(positions)        
    
    def split_positions(self, x):
        # if self.symbol in self.currencies:
        split = round(x/2, 2)
        # print(float(split), float(split))
        return float(split), float(split)
        # else:
        #     # Round x since we need round numbers
        #     x = round(x)
        #     remaining = x%2
        #     if remaining == 0:
        #         split = x/2
        #         print(float(split), float(split))
        #         return float(split), float(split)
        #     if remaining == 1:
        #         split = math.floor(x/2)
        #         print(float(split), float(split+1))
        #         return float(split), float(split+1)

   
    def order_log(self, result, request={}):
        if result:
            if result.retcode != mt.TRADE_RETCODE_DONE:
                error_string = f"Error: {result.comment}"
                print(error_string)
                print(request)
            # else:
            #     print(f"Order placed successfully!")
        else:
            print("Error with response!")

    def trade_algo(self):
        
        selected_symbols = list(set(self.currencies + self.indexes))
        
        while True:
            print(f"\n-------  Executed @ {datetime.now().strftime('%H:%M:%S')}------------------")
            
            is_market_open, is_market_close = util.get_market_status()

            if is_market_close:
                print("Market Close!")
                self.close_positions()

            if is_market_open and not is_market_close:
                account_size, free_margin, total_profit = ind.get_account_details()
                
                # Close all the position, If current profit reach more than 1% and re evaluate
                if total_profit > account_size * 1/100:
                    self.close_positions()
                
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                self.cancel_all_active_orders()
                mp.breakeven_1R_positions()

                if (free_margin > 0.1 * account_size):
                    for symbol in selected_symbols:
                        if symbol not in existing_positions:

                            if util.get_gmt_time()[1] <= 10 and symbol in ["US500.cash", "UK100.cash"]:
                                # Don't trade US500.cash before GMT -2 time 10, or 3AM US Time
                                continue

                            self.symbol = symbol
                            self.enable_symbol()
                            try:
                                self.update_symbol_parameters()
                                signal = ind.get_candle_signal(self.symbol)
                                if signal:
                                    if signal == "L":
                                        self.direction = "long"
                                        self.long_entry()
                                    elif signal == "S":
                                        self.direction = "short"
                                        self.short_entry()
                            except Exception as e:
                                print(f"{symbol} Error: {e}")
                                        
                else:
                    print("Not enough equity for new positions!")
            
            time.sleep(30)

    def stop_round(self, stop_price):
        if self.symbol in self.currencies:
            if self.symbol in ["USDJPY", "AUDJPY", "EURJPY"]:
                return round(stop_price, 3)
            return round(stop_price, 5)
        else:
            return round(stop_price, 2)

    def long_entry(self):
        entry_price = self.get_mid_price()
            
        if entry_price:
            # stop_price = self.get_lstop_price() - self.spread
            # one_r = self.spread + ind.get_stop_range(self.symbol)
            _, previous_bar_low, _ = ind.get_stop_range(self.symbol)
            # stop_price = entry_price - one_r
            # stop_entry = entry_price - one_r*self.ratio
            stop_price = self.stop_round(previous_bar_low)
            
            
            if entry_price > stop_price:
                # print(f"ENTRY: {entry_price} STOP: {stop_price}")
                
                try:
                    if self.symbol in self.currencies:
                        points_in_stop = round(entry_price - stop_price, 5)
                        position_size = self.calculate_slots(points_in_stop)/100000
                    else:
                        points_in_stop = round(entry_price - stop_price)
                        position_size = self.calculate_slots(points_in_stop)
                    
                    target_price1 = self.stop_round(entry_price + self.first_target * points_in_stop)
                    target_price2 = self.stop_round(entry_price + self.second_target * points_in_stop)
                    
                    # TODO this can be uncomment when we go for higher margin
                    position1, position2 = self.split_positions(position_size)
                    # position1, position2 = position_size, 0.0

                    request1 = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": position1,
                        "type": mt.ORDER_TYPE_BUY_LIMIT,
                        "price": entry_price,
                        "sl": stop_price,
                        "tp": target_price1, # FLOAT
                        "comment": "python script open",
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }

                    request2 = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": position2,
                        "type": mt.ORDER_TYPE_BUY_LIMIT,
                        "price": entry_price,
                        "sl": stop_price,
                        "tp": target_price2,
                        "comment": "python script open",
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }
                    
                    
                    res1 = mt.order_send(request1)
                    self.order_log(res1, request1)
                    res2 = mt.order_send(request2)
                    self.order_log(res2, request2)
                except Exception as e:
                    print(e)
            

    def short_entry(self):
        entry_price = self.get_mid_price()
        
        if entry_price:
            # stop_price = self.get_sstop_price() + self.spread
            previous_bar_high, previous_bar_low, previous_bar_length = ind.get_stop_range(self.symbol)
            # one_r = self.spread + ind.get_stop_range(self.symbol)
            # stop_price = entry_price + one_r
            # stop_entry = entry_price + one_r  *self.ratio
            stop_price = self.stop_round(previous_bar_high)

            if stop_price > entry_price:
                
                try:
                    # print(f"ENTRY: {entry_price} STOP: {stop_price}")
                    
                    if self.symbol in self.currencies:
                        points_in_stop = round(stop_price - entry_price, 5)
                        position_size = self.calculate_slots(points_in_stop)/100000
                    else:
                        points_in_stop = round(stop_price - entry_price)
                        position_size = self.calculate_slots(points_in_stop)
                    
                    target_price1 = self.stop_round(entry_price - self.first_target * points_in_stop)
                    target_price2 = self.stop_round(entry_price - self.second_target * points_in_stop)

                    # TODO this can be uncomment when we go for higher margin
                    position1, position2 = self.split_positions(position_size)
                    # position1, position2 = position_size, 0.0

                    request1 = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": position1,
                        "type": mt.ORDER_TYPE_SELL_LIMIT,
                        "price": entry_price,
                        "sl": stop_price,
                        "tp": target_price1,
                        "comment": "python script open",
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }
                    
                    request2 = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": self.symbol,
                        "volume": position2,
                        "type": mt.ORDER_TYPE_SELL_LIMIT,
                        "price": entry_price,
                        "sl": stop_price,
                        "tp": target_price2,
                        "comment": "python script open",
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }

                    res1 = mt.order_send(request1)
                    self.order_log(res1, request1)
                    res2 = mt.order_send(request2)
                    self.order_log(res2, request2)
                except Exception as e:
                    print(e)
    
    def cancel_all_active_orders(self):
        active_orders = mt.orders_get()

        for active_order in active_orders:
            request = {
                "action": mt.TRADE_ACTION_REMOVE,
                "order": active_order.ticket,
            }

            result = mt.order_send(request)

            if result.retcode != mt.TRADE_RETCODE_DONE:
                print(f"Failed to cancel order {active_order.ticket}, error code: {result.retcode}, reason: {result.comment}")

    
    def close_positions(self):
        positions = mt.positions_get()

        for obj in positions: 
            if obj.type == 1: 
                order_type = mt.ORDER_TYPE_BUY
                price = mt.symbol_info_tick(obj.symbol).bid
            else:
                order_type = mt.ORDER_TYPE_SELL
                price = mt.symbol_info_tick(obj.symbol).ask
            
            close_request = {
                "action": mt.TRADE_ACTION_DEAL,
                "symbol": obj.symbol,
                "volume": obj.volume,
                "type": order_type,
                "position": obj.ticket,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": 'Close trade',
                "type_time": mt.ORDER_TIME_GTC,
                "type_filling": mt.ORDER_FILLING_IOC, # also tried with ORDER_FILLING_RETURN
            }
            
            result = mt.order_send(close_request) # send order to close a position
            
            if result.retcode != mt.TRADE_RETCODE_DONE:
                print("Close Order "+obj.symbol+" failed!!...comment Code: "+str(result.comment))

    def enable_symbol(self):
        if not mt.symbol_select(self.symbol,True):
            print("symbol_select({}}) failed, exit", self.symbol)

def window():
    win = TradeCandle()
    win.trade_algo()
    # win.symbol = "AUDUSD"
    # win.update_symbol_parameters()
    # win.short_entry()


window()
