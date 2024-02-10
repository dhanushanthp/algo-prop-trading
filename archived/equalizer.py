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
import objects.Currencies as curr
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
        self.target_ratio = 1.0  # Default 1:0.5 Ratio
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
                # self.alert.send_msg(f"ERR: {self.account_name} <br> {error_string} <br> ```{request_str}```")

    def long_diffuser_entry(self, symbol, comment, stop_price, adhoc_risk):
        entry_price = self.get_entry_price(symbol=symbol)

        if entry_price:
            # _, stop_price, _, _, _ = ind.get_stop_range(symbol=symbol, timeframe=60, n_spreds=3)
            stop_price = self._round(symbol, stop_price)
            
            if entry_price > stop_price:                
                try:
                    print(f"{symbol.ljust(12)}: LONG, {adhoc_risk}")
                    points_in_stop, lots = self.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=stop_price, adhoc_risk=adhoc_risk)
                    
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
                        "magic": 0,
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }
                    
                    request_log = mt.order_send(order_request)
                    self.error_logging(request_log, order_request)
                    return True
                except Exception as e:
                    print(f"Long entry exception: {e}")

    def long_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe, double_vol=1):
        entry_price = self.get_entry_price(symbol=symbol)

        if entry_price and mp.get_last_trades_position(symbol, entry_timeframe):
            _, stop_price, is_strong_candle, _, _ = ind.get_stop_range(symbol=symbol, timeframe=entry_timeframe, buffer_ratio=6)
            
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
                            "volume": lots*double_vol,
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
                print(f" Skipped!")
                return False

    def short_diffuser_entry(self, symbol, comment, stop_price, adhoc_risk):
        entry_price = self.get_entry_price(symbol)
        
        if entry_price:
            # stop_price, _, _, _, _ = ind.get_stop_range(symbol=symbol, timeframe=60, n_spreds=3)
            stop_price = self._round(symbol, stop_price)

            if stop_price > entry_price:
                try:
                    print(f"{symbol.ljust(12)}: SHORT, {adhoc_risk}")      
                    points_in_stop, lots = self.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=stop_price, adhoc_risk=adhoc_risk)
                    
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
                        "magic":0,
                        "type_time": mt.ORDER_TIME_GTC,
                        "type_filling": mt.ORDER_FILLING_RETURN,
                    }
                    
                    request_log = mt.order_send(order_request)
                    self.error_logging(request_log, order_request)
                    return True
                except Exception as e:
                    print(e)

    def short_real_entry(self, symbol, comment, r_s_timeframe, entry_timeframe, double_vol=1):
        entry_price = self.get_entry_price(symbol)
        
        if entry_price and mp.get_last_trades_position(symbol, entry_timeframe):
            stop_price, _, is_strong_candle, _, _ = ind.get_stop_range(symbol=symbol, timeframe=entry_timeframe, buffer_ratio=6)
            
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
                            "volume": lots*double_vol,
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
                print(f" Skipped!")
                return False
    
    def main(self):
        selected_symbols = ind.get_ordered_symbols()
        
        while True:
            print(f"\n--##-- {config.local_ip} EQUALIZER {self.strategy.upper()} @ {util.get_current_time().strftime('%H:%M:%S')} in {self.trading_timeframes} TFs, RR: {self.rr}, TRIL: {self.enable_trail} STR Swtich: {self.switchable_strategy} Risk Incre:{self.incremental_risk} --##--")
            is_market_open, is_market_close = util.get_market_status()
            print(f"{'Acc Trail Loss'.ljust(20)}: {self.risk_manager.account_risk_percentage}%")
            print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")
            # print(f"{'Acc at Risk'.ljust(20)}: {'{:,}'.format(round(((self.risk_manager.get_max_loss() - self.fixed_initial_account_size)/self.fixed_initial_account_size) * 100, 2))}%, ${self.risk_manager.get_max_loss()}")
            # print(f"{'Next Trail at'.ljust(20)}: ${'{:,}'.format(round(self.risk_manager.get_max_loss() + self.risk_manager.risk_of_an_account))}")
            
            if self.enable_trail:
                mp.adjust_positions_trailing_stops() # Each position trail stop

            # +3 is failed 3 tries, and -6 profit of 30% slot
            if self.pnl < -self.risk_manager.max_account_risk and not self.immidiate_exit:
                mp.close_all_positions()
                time.sleep(30) # Take some time for the account to digest the positions
                current_account_size,_,_,_ = ind.get_account_details()

                self.pnl = (current_account_size - self.master_initial_account_size)
                self.alert.send_msg(f"{self.account_name}: Done for today! {round(self.pnl)}")
                self.immidiate_exit = True

            if is_market_close:
                print("Market Close!")
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
                            _, _, _, _, optimal_distance = ind.get_stop_range(symbol=symbol, timeframe=r_s_timeframe, buffer_ratio=3)
                        except Exception as e:
                            self.alert.send_msg(f"{self.account_name}: {symbol}: {e}")
                            break

                        resistances = levels["resistance"]
                        support = levels["support"]

                        current_candle = mt.copy_rates_from_pos(symbol, ind.match_timeframe(r_s_timeframe), 0, 1)[-1]

                        for resistance_level in resistances:
                            if (current_candle["open"] < resistance_level) and (resistance_level + 3*ind.get_spread(symbol) > current_candle["close"] > resistance_level):
                                break_long_at_resistance[symbol].append(r_s_timeframe)
                        
                        for support_level in support:
                            if (current_candle["open"] > support_level) and (support_level - 3*ind.get_spread(symbol) < current_candle["close"] < support_level):
                                break_short_at_support[symbol].append(r_s_timeframe)
                
                existing_positions = list(set([i.symbol for i in mt.positions_get()]))
                existing_main_positions = list(set([i.symbol for i in mt.positions_get() if i.comment == "R>60"]))
                if len(existing_main_positions) < 5:
                    for symbol in selected_symbols:
                        if (symbol not in existing_positions):
                            # Break Strategy
                            total_resistance_tf_long = set(break_long_at_resistance[symbol])
                            total_support_tf_short = set(break_short_at_support[symbol])

                            if self.strategy == "break":
                                if len(total_resistance_tf_long) >= 1:
                                    print(f"{symbol.ljust(12)} RL: {'|'.join(map(str, total_resistance_tf_long)).ljust(10)}")
                                    max_timeframe = max(total_resistance_tf_long)
                                    self.long_real_entry(symbol=symbol,
                                                            comment="B>" + '|'.join(map(str, total_resistance_tf_long)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                                elif len(total_support_tf_short) >= 1:
                                    print(f"{symbol.ljust(12)} SS: {'|'.join(map(str, total_support_tf_short)).ljust(10)}")
                                    max_timeframe = max(total_support_tf_short)
                                    self.short_real_entry(symbol=symbol, 
                                                            comment="B>" + '|'.join(map(str, total_support_tf_short)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                            elif self.strategy == "reverse":
                                if len(total_resistance_tf_long) >= 1:
                                    print(f"{symbol.ljust(12)} RS: {'|'.join(map(str, total_resistance_tf_long)).ljust(10)}")
                                    max_timeframe = max(total_resistance_tf_long)
                                    self.short_real_entry(symbol=symbol,
                                                            comment="R>" + '|'.join(map(str, total_resistance_tf_long)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                                elif len(total_support_tf_short) >= 1:
                                    print(f"{symbol.ljust(12)} SL: {'|'.join(map(str, total_support_tf_short)).ljust(10)}")
                                    max_timeframe = max(total_support_tf_short)
                                    self.long_real_entry(symbol=symbol, 
                                                            comment="R>" + '|'.join(map(str, total_support_tf_short)), 
                                                            r_s_timeframe=max_timeframe, 
                                                            entry_timeframe=max_timeframe)
                            else:
                                raise Exception("Strategy not defined!")
                
                need_action = self.risk_manager.risk_diffusers()
                max_timeframe = 60
                for symbol in need_action.keys():
                    risk_diff_obj = need_action[symbol]
                    action = risk_diff_obj.direction
                    if action == "long":
                        self.long_diffuser_entry(symbol=symbol, comment="defuser", stop_price=risk_diff_obj.stop_price, adhoc_risk=risk_diff_obj.position_risk)
                    elif action == "short":
                        self.short_diffuser_entry(symbol=symbol, comment="defuser", stop_price=risk_diff_obj.stop_price, adhoc_risk=risk_diff_obj.position_risk)
            
            time.sleep(self.timer)
    
if __name__ == "__main__":
    win = AlgoTrader()

    parser = argparse.ArgumentParser(description='Example script with named arguments.')


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
        win.enable_trail = util.boolean(args.enable_trail)
        win.switchable_strategy = util.boolean(args.enable_str_switch)
        win.incremental_risk = util.boolean(args.incremental_risk)

    else:
        # Mean the R&S levels and entry check will be based on the same selected timeframe. Default
        win.strategy = "smart"

        # otherwise timeframe will be default to 4 hours

    win.main()

