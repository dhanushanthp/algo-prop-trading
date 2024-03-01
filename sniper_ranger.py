import MetaTrader5 as mt
mt.initialize()
import time
import sys
import argparse

import objects.util as util
import objects.Currencies as curr
from objects.RiskManager import RiskManager
import modules.config as config
from objects.slack_msg import Slack
from objects.Targets import Targets
from objects.Directions import Directions
from objects.Prices import Prices
from objects.Orders import Orders
from objects.Account import Account
from objects.Indicators import Indicators
from objects.wrapper import Wrapper
from modules import indicators

class SniperReloaded():
    def __init__(self, trading_timeframe:int, account_risk:float=1, each_position_risk:float=0.1, target_ratio:float=2.0):
        # Default values
        self.target_ratio = target_ratio  # Default 1:0.5 Ratio
        self.stop_ratio = 1.0
        self.immidiate_exit = False
        self.timer = 30
        self.retries = 0
        self.persist_data = False
        self.trace_exit = False

        # External dependencies
        self.risk_manager = RiskManager(account_risk=account_risk, position_risk=each_position_risk, stop_ratio=self.stop_ratio, target_ratio=self.target_ratio)
        self.prices = Prices()
        self.orders = Orders(prices=self.prices, risk_manager=self.risk_manager)
        self.targets = Targets(risk_manager=self.risk_manager, timeframe=trading_timeframe)
        self.alert = Slack()
        self.account = Account()
        self.indicators = Indicators()
        self.wrapper = Wrapper()
        self.addtional_levels = False

        self.strategy:str = None

        # Account information
        self.account_name = self.account.get_account_name()

        # Expected reward for the day
        self.fixed_initial_account_size = self.risk_manager.account_size

        # Default
        self.trading_timeframe = trading_timeframe

        # Take the profit as specific RR ratio
        self.early_profit = False
        self.early_rr=self.risk_manager.account_risk_percentage # Default

    def trade(self, direction:Directions, symbol:str, reference:str, break_level:float):
        """
        This will take the trade based on given strategy
        """
        method_name = None
        if self.strategy == "break":
            method_name = "long_entry" if direction == Directions.LONG else "short_entry"
        elif self.strategy == "reverse":
            method_name = "short_entry" if direction == Directions.LONG else "long_entry"
        
        method = getattr(self.orders, method_name, None)

        if method:
            method(symbol=symbol, reference=f"{self.strategy.upper()[0]}-{reference}", break_level=break_level, trading_timeframe=self.trading_timeframe)

    
    def main(self):
        selected_symbols = curr.get_ordered_symbols()
        
        while True:
            print(f"\n------- {config.local_ip.replace('_', '.')} @ {util.get_current_time().strftime('%H:%M:%S')} in {self.trading_timeframe} TF {self.strategy.upper()}, Pivot: {self.addtional_levels}, Trace Exit:{self.trace_exit}, Early Profit:{self.early_profit} ({self.early_rr} RR) -----------")
            is_market_open, is_market_close = util.get_market_status()
            equity = self.account.get_equity()
            rr = (equity - self.fixed_initial_account_size)/self.risk_manager.risk_of_an_account
            pnl = (equity - self.risk_manager.account_size)
            print(f"{'Acc Trail Loss'.ljust(20)}: {self.risk_manager.account_risk_percentage}%")
            print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")
            print(f"{'Acc at Risk'.ljust(20)}: {'{:,}'.format(round(((self.risk_manager.get_max_loss() - self.fixed_initial_account_size)/self.fixed_initial_account_size) * 100, 2))}%, ${self.risk_manager.get_max_loss()}")
            print(f"{'Next Trail at'.ljust(20)}: ${'{:,}'.format(round(self.risk_manager.get_max_loss() + self.risk_manager.risk_of_an_account))}")
            print(f"{'Risk:Reward'.ljust(20)}: {round(rr, 3)}")
            print(f"{'PnL'.ljust(20)}: ${round(pnl, 2)}")

            # Record PnL, understand combined price movement on winning and lossing days
            if pnl != 0:
                with open(f'{config.local_ip}_{util.get_current_time().strftime("%Y%m%d")}.csv', 'a') as file:
                    file.write(f"{util.get_current_time().strftime('%Y/%m/%d %H:%M:%S')},break,{self.retries},{round(rr, 3)},{round(pnl, 3)}\n")

            # Each position trail stop
            self.risk_manager.adjust_positions_trailing_stops(target_multiplier=self.target_ratio, trading_timeframe=self.trading_timeframe) 

            if self.early_profit and (not self.immidiate_exit):
                if rr > self.early_rr:
                    # self.immidiate_exit = True
                    self.orders.close_all_positions()
                    # Reset account size for next round
                    time.sleep(30)
                    self.risk_manager = RiskManager(account_risk=account_risk, position_risk=each_position_risk, stop_ratio=self.stop_ratio, target_ratio=self.target_ratio)
                    self.fixed_initial_account_size = self.risk_manager.account_size
                    if self.trace_exit:
                        sys.exit()

            if self.risk_manager.has_daily_maximum_risk_reached():
                self.immidiate_exit = True
                self.orders.close_all_positions()
                sys.exit()
                # time.sleep(30) # Take some time for the account to digest the positions                
                # self.alert.send_msg(f"{self.account_name}: Done for today!, Account RR: {round(rr, 2)}")

            if is_market_close:
                print("Market Close!")
                self.risk_manager = RiskManager(account_risk=account_risk, position_risk=each_position_risk, stop_ratio=self.stop_ratio, target_ratio=self.target_ratio)
                self.orders.close_all_positions()
                
                # Reset account size for next day
                self.fixed_initial_account_size = self.risk_manager.account_size
                self.immidiate_exit = False
            
            if is_market_open and (not is_market_close) and (not self.immidiate_exit):
                self.orders.cancel_all_pending_orders()
                existing_positions = self.wrapper.get_existing_symbols()

                for symbol in selected_symbols:
                    # If the positions is already in trade, then don't check for signal
                    if symbol in existing_positions:
                        continue

                    king_of_levels = self.indicators.get_king_of_levels(symbol=symbol, timeframe=self.trading_timeframe)
                    previous_candle = self.wrapper.get_previous_candle(symbol=symbol, timeframe=self.trading_timeframe)

                    if self.addtional_levels:
                        pivot_levels = indicators.support_resistance_levels(symbol=symbol, timeframe=self.trading_timeframe)

                    for resistance in king_of_levels["resistance"]:
                        if previous_candle["low"] < resistance.level and previous_candle["close"] > resistance.level:
                            is_valid_signal, candle_gap = self.targets.check_signal_validity(symbol=symbol, 
                                                                                             past_break_index=resistance.break_bar_index, 
                                                                                             timeframe=self.trading_timeframe,
                                                                                             shoot_direction=Directions.LONG, 
                                                                                             break_level=resistance.level, 
                                                                                             reference=resistance.reference)

                            if is_valid_signal:
                                self.trade(direction=Directions.LONG, symbol=symbol, reference=resistance.reference, break_level=candle_gap)
                            elif self.addtional_levels:
                                for resistance_level in pivot_levels["resistance"]:
                                    if previous_candle["low"] < resistance_level and previous_candle["close"] > resistance_level:
                                        self.trade(direction=Directions.LONG, symbol=symbol, reference="PIV", break_level=0)
                                        break
                            break
                    
                    for support in king_of_levels["support"]:
                        if previous_candle["high"] > support.level and previous_candle["close"] < support.level:
                            is_valid_signal, candle_gap = self.targets.check_signal_validity(symbol=symbol, 
                                                                                             past_break_index=support.break_bar_index, 
                                                                                             timeframe=self.trading_timeframe,
                                                                                             shoot_direction=Directions.SHORT, 
                                                                                             break_level=support.level, 
                                                                                             reference=support.reference)

                            if is_valid_signal:
                                self.trade(direction=Directions.SHORT, symbol=symbol, reference=support.reference, break_level=candle_gap)
                            elif self.addtional_levels:
                                for support_level in pivot_levels["support"]:
                                    if previous_candle["high"] > support_level and previous_candle["close"] < support_level:
                                        self.trade(direction=Directions.SHORT, symbol=symbol, reference="PIV", break_level=0)
                                        break
                            break
                
                self.targets.show_targets(persist=self.persist_data)

            time.sleep(self.timer)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Example script with named arguments.')

    parser.add_argument('--early_profit', type=str, help='Enable/Disable Early Profit')
    parser.add_argument('--early_rr', type=float, help='Early Profit RR')
    parser.add_argument('--target_ratio', type=float, help='Target ratio, assume stop is 1')
    parser.add_argument('--timeframe', type=int, help='Selected timeframe for trade')
    parser.add_argument('--account_risk', type=float, help='Total Account Risk for Trade Session')
    parser.add_argument('--each_position_risk', type=float, help='Each Position risk percentage w.r.t account size')
    parser.add_argument('--persist_data', type=str, help='Do we store data on backend')
    parser.add_argument('--trace_exit', type=str, help='Trade the profit and exit when it hit the traced stop')
    parser.add_argument('--strategy', type=str, help='Selected strategy')
    parser.add_argument('--addtional_levels', type=str, help='Selected strategy')
    args = parser.parse_args()
    
    
    trading_timeframe = int(args.timeframe)
    account_risk = float(args.account_risk)
    target_ratio = float(args.target_ratio)
    each_position_risk = float(args.each_position_risk)
    win = SniperReloaded(trading_timeframe=trading_timeframe, account_risk=account_risk, each_position_risk=each_position_risk, target_ratio=target_ratio)

    win.early_profit = util.boolean(args.early_profit)
    win.early_rr = float(args.early_rr)

    win.persist_data = util.boolean(args.persist_data)
    win.trace_exit = util.boolean(args.trace_exit)
    win.strategy = args.strategy

    win.addtional_levels = util.boolean(args.addtional_levels)

    win.main()

