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
        self.master_initial_account_size = self.risk_manager.account_size

        
        self.pnl = 0

        # Default
        self.trading_timeframes = [240]
        self.rr = [0.6, 0.3]

        self.profit_factor = 1
        self.enable_trail = False
        self.switchable_strategy = False
        self.incremental_risk = False

        self.trade_tracker = dict()
    
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
    
    def get_lot_size(self, symbol, entry_price, stop_price, adhoc_risk=None):
        dollor_value = mp.get_dollar_value(symbol)
        points_in_stop = abs(entry_price-stop_price)

        if adhoc_risk is None:
            adhoc_risk = self.risk_manager.risk_of_a_position

        lots = abs(adhoc_risk)/(points_in_stop * dollor_value)
        
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

    def long_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe, double_vol=1, reverse=1):
        entry_price = self.get_entry_price(symbol=symbol)

        if entry_price and mp.get_last_trades_position(symbol, self.trading_timeframes[0]):
            _, stop_price, _, _, optimal_distance = ind.get_stop_range(symbol=symbol, timeframe=self.trading_timeframes[0], buffer_ratio=3)
            entry_distance = optimal_distance*reverse
            
            # Shift Entries
            entry_price = self._round(symbol, entry_price) 

            stop_price = entry_price - optimal_distance
            stop_price = self._round(symbol, stop_price)
            
            order_type = mt.ORDER_TYPE_BUY_LIMIT
            if reverse < 0:
                order_type = mt.ORDER_TYPE_BUY_STOP

            if entry_price > stop_price:
                try:
                    print(f"{symbol.ljust(12)}: LONG")
                    points_in_stop, lots = self.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=stop_price)
                    
                    lots =  round(lots, 2)
                    
                    order_request = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": symbol,
                        "volume": lots*double_vol,
                        "type": order_type,
                        "price": entry_price,
                        "sl": self._round(symbol, entry_price - self.stop_ratio * points_in_stop),
                        "tp": self._round(symbol, entry_price + self.target_ratio * points_in_stop),
                        "comment": f"{r_s_timeframe}",
                        "magic":0,
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

    def short_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe, double_vol=1, reverse=1):
        entry_price = self.get_entry_price(symbol)
        
        if entry_price and mp.get_last_trades_position(symbol, self.trading_timeframes[0]):
            stop_price, _, _, _, optimal_distance = ind.get_stop_range(symbol=symbol, timeframe=self.trading_timeframes[0], buffer_ratio=3)
            entry_distance = optimal_distance*reverse
            
            # Shift Entries
            entry_price = self._round(symbol, entry_price) 

            stop_price = entry_price + optimal_distance
            stop_price = self._round(symbol, stop_price)

            order_type = mt.ORDER_TYPE_SELL_LIMIT
            if reverse < 0:
                order_type = mt.ORDER_TYPE_SELL_STOP

            if stop_price > entry_price:
                try:
                    print(f"{symbol.ljust(12)}: SHORT")      
                    points_in_stop, lots = self.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=stop_price)
                    
                    lots =  round(lots, 2)

                    order_request = {
                        "action": mt.TRADE_ACTION_PENDING,
                        "symbol": symbol,
                        "volume": lots*double_vol,
                        "type": order_type,
                        "price": entry_price,
                        "sl": self._round(symbol, entry_price + self.stop_ratio * points_in_stop),
                        "tp": self._round(symbol, entry_price - self.target_ratio * points_in_stop),
                        "comment": f"{r_s_timeframe}",
                        "magic":0,
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
            print(f"\n--##-- {config.local_ip} SNIPER  {self.strategy.upper()} @ {util.get_current_time().strftime('%H:%M:%S')} in {self.trading_timeframes} TFs, RR: {self.rr}, TRIL: {self.enable_trail} STR Swtich: {self.switchable_strategy} Risk Incre:{self.incremental_risk} --##--")
            is_market_open, is_market_close = util.get_market_status()
            print(f"{'Acc Trail Loss'.ljust(20)}: {self.risk_manager.account_risk_percentage}%")
            print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")

            if False:
                resis_level = 0.66156
                total_resistance_tf_long = [resis_level]
                self.short_real_entry(symbol="EURJPY",
                                                    comment="R>" + '|'.join(map(str, total_resistance_tf_long)), 
                                                    r_s_timeframe=resis_level, 
                                                    entry_timeframe=resis_level, reverse=1)
            
            if self.enable_trail:
                mp.adjust_positions_trailing_stops() # Each position trail stop

            # +3 is failed 3 tries, and -6 profit of 30% slot
            if self.pnl < -self.risk_manager.max_account_risk and not self.immidiate_exit:
                mp.cancel_all_pending_orders()
                mp.close_all_positions()
                time.sleep(30) # Take some time for the account to digest the positions
                current_account_size,_,_,_ = ind.get_account_details()

                self.pnl = (current_account_size - self.master_initial_account_size)
                self.alert.send_msg(f"{self.account_name}: Done for today! {round(self.pnl)}")
                self.immidiate_exit = True

            if is_market_close:
                print("Market Close!")
                # mp.cancel_all_pending_orders()
                mp.close_all_positions()
                
                # Reset account size for next day
                self.risk_manager = risk_manager.RiskManager(profit_split=1) # Reset the risk for the day
                self.fixed_initial_account_size = self.risk_manager.account_size
                self.master_initial_account_size = self.risk_manager.account_size
                self.immidiate_exit = False
                self.retries = 0
            

            if is_market_open and not is_market_close and not self.immidiate_exit:
                mp.cancel_all_pending_orders()

                _, equity, _, _ = ind.get_account_details()
                rr = (equity - self.fixed_initial_account_size)/self.risk_manager.risk_of_an_account
                self.pnl = (equity - self.master_initial_account_size)

                if self.pnl != 0:
                    with open(f'{config.local_ip}.csv', 'a') as file:
                        file.write(f"{util.get_current_time().strftime('%Y/%m/%d %H:%M:%S')},{self.strategy},{self.retries},{self.profit_factor},{round(rr, 3)},{round(self.pnl, 3)}\n")
                
                print(f"RR:{round(rr, 3)}, Pnl: {round(self.pnl, 2)}, Initial: {round(self.fixed_initial_account_size)}, Equity: {equity}")                    

                break_long_at_resistance = {}
                break_short_at_support = {}

                for symbol in selected_symbols:
                    break_long_at_resistance[symbol] = []
                    break_short_at_support[symbol] = []

                    for r_s_timeframe in self.trading_timeframes:
                        try:
                            # Incase if it failed to request the symbol price
                            levels = ind.support_resistance_levels(symbol, r_s_timeframe)
                        except Exception as e:
                            self.alert.send_msg(f"{self.account_name}: {symbol}: {e}")
                            break

                        resistances = levels["resistance"]
                        support = levels["support"]

                        current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(r_s_timeframe), 1, 1)[-1]
                        # print(symbol, current_candle)
                        
                        for resistance_level in resistances:
                            if (current_candle["open"] < resistance_level) and (current_candle["close"] > resistance_level):
                                break_long_at_resistance[symbol].append(resistance_level)
                        
                        for support_level in support:
                            if (current_candle["open"] > support_level) and (current_candle["close"] < support_level):
                                break_short_at_support[symbol].append(support_level)
                
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                if len(existing_positions) < config.num_positions_at_risk - 1:
                    for symbol in selected_symbols:
                        if symbol not in self.trade_tracker:
                            self.trade_tracker[symbol] = None

                        if (symbol not in existing_positions):
                            # Break Strategy
                            total_resistance_tf_long = break_long_at_resistance[symbol]
                            total_support_tf_short = break_short_at_support[symbol]

                            if self.strategy == "break":
                                if len(total_resistance_tf_long) >= 1:
                                    print(f"{symbol.ljust(12)} RL: {'|'.join(map(str, total_resistance_tf_long)).ljust(10)}")
                                    resis_level = min(total_resistance_tf_long)
                                    existing_order_level = mp.get_level(symbol)
                                    if existing_order_level != resis_level:
                                        mp.cancel_specific_pending_orders(symbol, "long", resis_level)
                                        self.long_real_entry(symbol=symbol,
                                                                comment="B>" + '|'.join(map(str, total_resistance_tf_long)), 
                                                                r_s_timeframe=resis_level, 
                                                                entry_timeframe=resis_level)
                                elif len(total_support_tf_short) >= 1:
                                    print(f"{symbol.ljust(12)} SS: {'|'.join(map(str, total_support_tf_short)).ljust(10)}")
                                    resis_level = max(total_support_tf_short)
                                    existing_order_level = mp.get_level(symbol)
                                    if existing_order_level != resis_level:
                                        mp.cancel_specific_pending_orders(symbol, "short",  resis_level)
                                        self.short_real_entry(symbol=symbol, 
                                                                comment="B>" + '|'.join(map(str, total_support_tf_short)), 
                                                                r_s_timeframe=resis_level, 
                                                                entry_timeframe=resis_level)
                            elif self.strategy == "reverse":
                                if len(total_resistance_tf_long) >= 1:
                                    print(f"{symbol.ljust(12)} RS: {'|'.join(map(str, total_resistance_tf_long)).ljust(10)}")
                                    resis_level = min(total_resistance_tf_long)
                                    existing_order_level = mp.get_level(symbol)
                                    if existing_order_level != resis_level:
                                        mp.cancel_specific_pending_orders(symbol, "short",  resis_level)
                                        self.short_real_entry(symbol=symbol,
                                                                comment="R>" + '|'.join(map(str, total_resistance_tf_long)), 
                                                                r_s_timeframe=resis_level, 
                                                                entry_timeframe=resis_level, reverse=1)
                                elif len(total_support_tf_short) >= 1:
                                    print(f"{symbol.ljust(12)} SL: {'|'.join(map(str, total_support_tf_short)).ljust(10)}")
                                    resis_level = max(total_support_tf_short)
                                    existing_order_level = mp.get_level(symbol)
                                    if existing_order_level != resis_level:
                                        mp.cancel_specific_pending_orders(symbol, "long",  resis_level)
                                        self.long_real_entry(symbol=symbol, 
                                                                comment="R>" + '|'.join(map(str, total_support_tf_short)), 
                                                                r_s_timeframe=resis_level, 
                                                                entry_timeframe=resis_level, reverse=1)
                            else:
                                raise Exception("Strategy not defined!")
                else:
                    mp.cancel_all_pending_orders()
            
            time.sleep(self.timer)
    
if __name__ == "__main__":
    win = AlgoTrader()

    parser = argparse.ArgumentParser(description='Example script with named arguments')


    # Define your named arguments
    parser.add_argument('--strategy', type=str, help='Strategy Selection')
    parser.add_argument('--timeframe', type=str, help='Selected timeframe for trade')
    parser.add_argument('--rr', type=str, help='Risk and reward ratio')
    parser.add_argument('--incremental_risk', type=str, help='Do you need to increase the risk on winning?')
    parser.add_argument('--enable_trail', type=str, help='Do u enable trail stop')
    parser.add_argument('--enable_str_switch', type=str, help='Switch break or reverse based on winning')

    args = parser.parse_args()
    
    if len(sys.argv) > 1:
        win.strategy = args.strategy
        if win.strategy not in ["reverse", "break"]:
            raise Exception("Please enter fixed or auto entry time check!")
        
        win.trading_timeframes = [int(i) for i in args.timeframe.split(",")]
        win.rr = [float(i) for i in args.rr.split(",")]
        win.stop_ratio = win.rr[0]
        win.target_ratio = win.rr[1]
        win.enable_trail = util.boolean(args.enable_trail)
        win.switchable_strategy = util.boolean(args.enable_str_switch)
        win.incremental_risk = util.boolean(args.incremental_risk)

    else:
        # Mean the R&S levels and entry check will be based on the same selected timeframe. Default
        win.strategy = "smart"

        # otherwise timeframe will be default to 4 hours

    win.main()

