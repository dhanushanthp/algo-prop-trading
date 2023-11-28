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

        self.trading_timeframe = 15 # Default to 15 min
        self.target_ratio = 0.5 # Default 1:0.5 Ratio
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

    def long_real_entry(self, symbol, comment="NA"):
        entry_price = self.get_entry_price(symbol=symbol)

        if entry_price:
            _, stop_price, prev_can_dir = ind.get_stop_range(symbol, self.trading_timeframe)
            
            # and prev_can_dir == "S"
            if prev_can_dir and mp.get_last_trades_position(symbol, self.trading_timeframe):
                magic_number = 1 if prev_can_dir == "L" else 2
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
        entry_price = self.get_entry_price(symbol)
        
        if entry_price:
            stop_price, _, previous_candle = ind.get_stop_range(symbol, self.trading_timeframe)
            
            # and previous_candle == "L"
            if previous_candle and mp.get_last_trades_position(symbol, self.trading_timeframe):
                magic_number = 1 if previous_candle == "L" else 2
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
        selected_symbols = ind.get_ordered_symbols()
        
        while True:
            print(f"\n-------  Executed @ {datetime.now().strftime('%H:%M:%S')}------------------")
            print(f"{'Current Risk'.ljust(20)}: ${self.updated_risk}")
            
            is_market_open, is_market_close = util.get_market_status()

            # Max profit or loss
            if self.risk_manager.is_dly_max_risk_reached() or self.risk_manager.is_dly_max_profit_reached():
                print("Max loss/profit reached! Closing all positions!")
                mp.close_all_positions()
                sys.exit()

            if is_market_close:
                print("Market Close!")
                # Reset the risk for the day
                self.risk_manager.reset_risk()
                mp.close_all_positions()
            
            if is_market_open and not is_market_close:
                mp.cancel_all_pending_orders()
                mp.exit_one_r()               
                
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                parallel_trades = mp.num_of_parallel_tickers()
                print(f"{'Available Slots'.ljust(20)}: {parallel_trades - len(existing_positions)}")
                
                _, current_hour, _ = util.get_gmt_time()
                
                if len(existing_positions) < parallel_trades:
                    # self.strategy = mp.get_recommended_strategy()
                    
                    for symbol in selected_symbols:
                        # This helps to manage one order at a time rather sending bulk order to server
                        active_orders = len(mt.orders_get())
                        if symbol not in existing_positions:
                            # Don't trade US500.cash before GMT -2 time 10, or 3AM US Time
                            if current_hour <= 10 and symbol in ["US500.cash", "UK100.cash"]:
                                continue
                            
                            try:
                                signal = ind.get_candle_signal(symbol, verb=True)
                                
                                # Only enter 1 order at a time along with the signal
                                if signal and active_orders < 1:
                                    
                                    if self.strategy == config.AUTO:
                                        check_resistance = ind.find_resistance_support(symbol=symbol, timeframe=self.trading_timeframe)
                                        # This check is there any support or resistance
                                        if check_resistance:
                                            strategy = config.REVERSAL
                                        else:
                                            strategy = config.TREND
                                    else:
                                        # Other wise choose the default strategy given the application
                                        strategy = self.strategy

                                    if strategy == config.REVERSAL:                                    
                                        if signal == "L":
                                            if self.short_real_entry(symbol=symbol, comment=strategy):
                                                # Make sure we make only 1 trade at a time
                                                break 
                                        elif signal == "S":
                                            if self.long_real_entry(symbol=symbol, comment=strategy):
                                                # Make sure we make only 1 trade at a time
                                                break
                                    elif strategy == config.TREND:  
                                        if signal == "L":
                                            if self.long_real_entry(symbol=symbol, comment=strategy):
                                                # Make sure we make only 1 trade at a time
                                                break 
                                        elif signal == "S":
                                            if self.short_real_entry(symbol=symbol, comment=strategy):
                                                # Make sure we make only 1 trade at a time
                                                break
                                    else:
                                        print("No confirmation from trend!")
                            except Exception as e:
                                print(f"{symbol.ljust(12)} Error: {e}")
            
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
        win.trading_timeframe = int(sys.argv[1])
        win.stop_ratio = float(sys.argv[2])
        win.target_ratio = float(sys.argv[3])
        win.strategy =sys.argv[4]
    
    print("\n------------------------------------------------")
    print(f"SELECTED TIMEFRAME {win.trading_timeframe} & Risk:Reward : {win.stop_ratio}:{win.target_ratio} & Strategy: {win.strategy}" )
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
    


