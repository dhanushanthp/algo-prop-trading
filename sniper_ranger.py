import MetaTrader5 as mt
mt.initialize()
import time
import argparse

import modules.meta.util as util
import modules.meta.Currencies as curr
from modules.meta.RiskManager import RiskManager
from modules.common.slack_msg import Slack
from modules.common import logme
from modules.meta.Targets import Targets
from modules.common.Directions import Directions
from modules.meta.Prices import Prices
from modules.meta.Orders import Orders
from modules.meta.Account import Account
from modules.meta.Indicators import Indicators
from modules.meta.wrapper import Wrapper
from modules import config

"""
IP Address
Production: 172_16_27_130
Test: 172_16_27_128
"""

class SniperReloaded():
    def __init__(self, trading_timeframe:int, account_risk:float=1, each_position_risk:float=0.1, target_ratio:float=2.0):
        # Default values
        self.target_ratio = target_ratio  # Default 1:2.0 Ratio
        self.stop_ratio = 1.0
        self.immidiate_exit = False
        self.timer = 30
        self.retries = 0

        # External dependencies
        self.risk_manager = RiskManager(account_risk=account_risk, position_risk=each_position_risk, stop_ratio=self.stop_ratio, target_ratio=self.target_ratio)
        self.prices = Prices()
        self.orders = Orders(prices=self.prices, risk_manager=self.risk_manager)
        self.targets = Targets(risk_manager=self.risk_manager, timeframe=trading_timeframe)
        self.alert = Slack()
        self.account = Account()
        self.indicators = Indicators()
        self.wrapper = Wrapper()

        self.strategy:str = None

        # Account information
        self.account_name = self.account.get_account_name()

        # Expected reward for the day
        self.fixed_initial_account_size = self.risk_manager.account_size

        # Default
        self.trading_timeframe = trading_timeframe

        # Take the profit as specific RR ratio
        self.early_rr=1 # Default 1:1 Ratio

        self.selected_symbols = curr.get_ordered_symbols(without_index=True)

    def trade(self, direction:Directions, symbol:str, reference:str, break_level:float):
        """
        This will take the trade based on given strategy
        """
        method_name = None

        ratio = self.indicators.candle_move_ratio(symbol=symbol, timeframe=self.trading_timeframe)
        
        # When the candle is 1X later than the ATR, then it should be reverse, Since it moved too much from the general range
        if ratio > 1.5:
            strategy = "reverse"
        else:
            strategy = "break"
        
        _,hour,_ = util.get_current_day_hour_min()
        logme.logger.info(f"{hour}, {config.local_ip}, {symbol}, {strategy}, {ratio}")

        if strategy == "break":
            method_name = "long_entry" if direction == Directions.LONG else "short_entry"
        elif strategy == "reverse":
            method_name = "short_entry" if direction == Directions.LONG else "long_entry"
        
        method = getattr(self.orders, method_name, None)

        if method:
            method(symbol=symbol, reference=f"{strategy.upper()[0]}-{reference}", break_level=break_level, trading_timeframe=self.trading_timeframe)

    
    def main(self):
        while True:
            print(f"\n------- Status: {not self.immidiate_exit}, {self.trading_timeframe} TF {self.strategy.upper()}, Profit: {self.early_rr} RR -----------")
            is_market_open, is_market_close = util.get_market_status()
            equity = self.account.get_equity()
            rr = (equity - self.fixed_initial_account_size)/self.risk_manager.risk_of_an_account
            pnl = (equity - self.risk_manager.account_size)
            print(f"{'Max Account Risk'.ljust(20)}: {self.risk_manager.account_risk_percentage}%")
            print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")
            print(f"{'Risk:Reward'.ljust(20)}: {round(rr, 3)}")
            print(f"{'PnL'.ljust(20)}: ${round(pnl, 2)}")

            # Each position trail stop
            self.risk_manager.adjust_positions_trailing_stops(target_multiplier=self.target_ratio, trading_timeframe=self.trading_timeframe) 

            # Early Profit or Exit when account reach max loss, Close when US market time 8AM to avoid the spike stop at 8:30 AM
            if not self.immidiate_exit:
                
                # In addtion to exit plans
                if (rr > self.early_rr) or self.risk_manager.has_daily_maximum_risk_reached():
                    self.immidiate_exit = True
                    self.orders.cancel_all_pending_orders()
                    self.orders.close_all_positions()
                
            if is_market_close:
                print("Market Close!")
                self.orders.cancel_all_pending_orders()
                self.orders.close_all_positions()
                
                # Reset account size for next day
                self.risk_manager = RiskManager(account_risk=account_risk, position_risk=each_position_risk, stop_ratio=self.stop_ratio, target_ratio=self.target_ratio)
                self.fixed_initial_account_size = self.risk_manager.account_size
                self.immidiate_exit = False

            if is_market_open and (not is_market_close) and (not self.immidiate_exit):
                self.orders.cancel_all_pending_orders()
                existing_positions = self.wrapper.get_existing_symbols()

                for symbol in self.selected_symbols:
                    # If the positions is already in trade, then don't check for signal
                    if symbol in existing_positions:
                        continue

                    previous_candle = self.wrapper.get_previous_candle(symbol=symbol, timeframe=self.trading_timeframe)
                    
                    """
                    Levels such as High of the Day, Low of the day will be checked with previous bar close
                    """
                    king_of_levels = self.indicators.get_king_of_levels(symbol=symbol, timeframe=self.trading_timeframe)
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
                            break # Break the resistance loop
                    
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
                            break # Break the support loop

            time.sleep(self.timer)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Example script with named arguments.')

    parser.add_argument('--strategy', type=str, help='Selected strategy')
    parser.add_argument('--timeframe', type=int, help='Selected timeframe for trade')
    parser.add_argument('--account_risk', type=float, help='Total Account Risk for Trade Session')
    parser.add_argument('--early_rr', type=float, help='Early Profit RR')
    parser.add_argument('--target_ratio', type=float, help='Target ratio, assume stop is 1')
    parser.add_argument('--each_position_risk', type=float, help='Each Position risk percentage w.r.t account size') # Just Dummy
    
    args = parser.parse_args()
    
    trading_timeframe = int(args.timeframe)
    account_risk = float(args.account_risk)
    each_position_risk = account_risk/2 # float(args.each_position_risk)
    target_ratio = float(args.target_ratio)

    win = SniperReloaded(trading_timeframe=trading_timeframe, account_risk=account_risk, each_position_risk=each_position_risk, target_ratio=target_ratio)
    win.early_rr = float(args.early_rr)
    win.strategy = args.strategy

    win.main()