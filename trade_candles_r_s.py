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

class AlgoTrader():
    def __init__(self):
        mt.initialize()

        self.entry_timeframe = None # Default to 15 min
        self.target_ratio = 1.0 # Default 1:0.5 Ratio
        self.stop_ratio = 1.0
        self.risk_manager = risk_manager.RiskManager()
        self.updated_risk = self.risk_manager.initial_risk
        self.strategy = config.REVERSAL
    
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
                        print(f"{''.ljust(12)}: LONG")        
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
                        print(f"{''.ljust(12)}: SHORT")      
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
            
            is_market_open, is_market_close = util.get_market_status()

            # Max profit or loss
            # if self.risk_manager.is_dly_max_risk_reached() or self.risk_manager.is_dly_max_profit_reached():
            #     print("Max loss/profit reached! Closing all positions!")
            #     mp.close_all_positions()
            #     sys.exit()

            if is_market_close:
                print("Market Close!")
                # Reset the risk for the day
                self.risk_manager.reset_risk()
                mp.close_all_positions()
            
            if is_market_open and not is_market_close:
                mp.cancel_all_pending_orders()
                mp.exit_one_r()               
                
                parallel_trades = len(selected_symbols) # mp.num_of_parallel_tickers()
                                
                _, current_hour, _ = util.get_gmt_time()
                
                for r_s_timeframe in [60, 30, 15]:
                    existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                    print(f"{f'{r_s_timeframe}: Available Slots'.ljust(20)}: {parallel_trades - len(existing_positions)}")
                    if len(existing_positions) < len(selected_symbols):
                        for symbol in selected_symbols:
                            
                            active_orders = len(mt.orders_get())

                            if  (symbol not in existing_positions) and active_orders < 1:
                                
                                # Don't trade US500.cash before GMT -2 time 10, or 3AM US Time
                                if current_hour <= 10 and symbol in ["US500.cash", "UK100.cash"]:
                                    continue

                                levels = ind.find_r_s(symbol, r_s_timeframe)
                                # print(f"{symbol.ljust(12)}:", levels)
                                resistances = levels["resistance"]
                                support = levels["support"]


                                """
                                If it's a fixed timeframe, then the 15 minute candle will be checked for entry along with higer timeframe.
                                Also the stop will be decided based on 15 minutes time frame.

                                If it's auto then all the levels check and trade entry will be in same time frame
                                """
                                entry_check_timeframe = r_s_timeframe if self.entry_timeframe == "auto" else 15
                                
                                for resistance_level in resistances:
                                    current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(entry_check_timeframe), 0, 1)[-1]
                                    if current_candle["open"] > resistance_level and current_candle["close"] < resistance_level:
                                        if self.short_real_entry(symbol=symbol, 
                                                                 comment=f"RES>{self.entry_timeframe}>{entry_check_timeframe}>{resistance_level}", 
                                                                 r_s_timeframe=r_s_timeframe, 
                                                                 entry_timeframe=entry_check_timeframe):
                                            break

                                for support_level in support:
                                    current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(entry_check_timeframe), 0, 1)[-1]
                                    if current_candle["open"] < support_level and current_candle["close"] > support_level:
                                        if self.long_real_entry(symbol=symbol, 
                                                                comment=f"SUP>{self.entry_timeframe}>{entry_check_timeframe}>{support_level}", 
                                                                r_s_timeframe=r_s_timeframe, 
                                                                entry_timeframe=entry_check_timeframe):
                                            break
            
            time.sleep(30)
    

    def parse_cmd_args(self):
        import argparse
        parser = argparse.ArgumentParser(description='Process some command line arguments')
        parser.add_argument('--timeframe', type=str, help='Description of arg1')
        parser.add_argument('--stopratio', type=int, help='Description of arg2')
        parser.add_argument('--targetratio', type=float, help='Description of arg3')
        parser.add_argument('--strategy', type=float, help='Description of arg3')
        # Add more arguments as needed

        args = parser.parse_args()

        # Convert argparse.Namespace to dictionary
        args_dict = vars(args)

        return args_dict
    
if __name__ == "__main__":
    win = AlgoTrader()
    
    if len(sys.argv) > 1:
        win.entry_timeframe = sys.argv[1]
        if win.entry_timeframe not in ["fixed", "auto"]:
            raise Exception("Please enter fixed or auto entry time check!")
    else:
        # Mean the R&S levels and entry check will be based on the same selected timeframe. Default
        win.entry_timeframe = "auto"
        
    
    print("\n------------------------------------------------")
    print(f"SELECTED TIMEFRAME {win.entry_timeframe}" )
    print("------------------------------------------------")
    win.main()
    
    
    """
    ENTRY PRICE TEST
    """
    # for i in (curr.currencies + curr.indexes):
    #     entry_price = win.get_entry_price(symbol=i)
    #     print(f"{i}: {entry_price}")
        
        
    # win.long_trial_entry(symbol=symbol)
    # win.long_real_entry(symbol=symbol)
    # win.short_trial_entry(symbol=symbol)
    # win.short_real_entry(symbol=symbol)
    # win.update_symbol_parameters()
    # win.long_entry_test()
    # win.scale_out_positions()
    # print(win.calculate_slots(3.89)/100000)
    


