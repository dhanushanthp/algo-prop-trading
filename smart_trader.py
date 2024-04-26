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

class SmartTrader():
    def __init__(self, security:str, 
                 trading_timeframe:int, 
                 account_risk:float=1, 
                 each_position_risk:float=0.1, 
                 target_ratio:float=2.0, 
                 trades_per_day:int=5):
        
        # Default values
        self.target_ratio = target_ratio  # Default 1:2.0 Ratio
        self.stop_ratio = 1.0
        self.timer = 30
        self.retries = 0
        self.security:str = security

        # External dependencies
        self.risk_manager = RiskManager(account_risk=account_risk, 
                                        position_risk=each_position_risk, 
                                        stop_ratio=self.stop_ratio, 
                                        target_ratio=self.target_ratio)
        self.prices = Prices()
        self.wrapper = Wrapper()

        self.indicators = Indicators(wrapper=self.wrapper, 
                                     prices=self.prices)

        self.orders = Orders(prices=self.prices, 
                             risk_manager=self.risk_manager,
                             wrapper = self.wrapper)
        
        self.targets = Targets(risk_manager=self.risk_manager, 
                               timeframe=trading_timeframe)
        
        self.alert = Slack()
        self.account = Account()
        
        self.system:str = None
        self.strategy:str = None
        
        # Account information
        self.account_name = self.account.get_account_name()

        # Expected reward for the day
        self.fixed_initial_account_size = self.risk_manager.account_size

        # Default
        self.trading_timeframe = trading_timeframe
        self.trades_per_day = trades_per_day
        self.pause_trading = False

        # Initiate the ticker
        curr.ticker_initiator(security=security)

    def trade(self, direction:Directions, symbol:str, reference:str, break_level:float) -> bool:
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
            status = method(symbol=symbol, 
                            reference=f"{self.strategy.upper()[0]}-{reference}", 
                            break_level=break_level, 
                            trading_timeframe=self.trading_timeframe)
            return status

    
    def main(self):
        while True:
            print(f"\n------- {self.security} {self.trading_timeframe} TF {self.strategy.upper()}-----------")
            is_market_open, is_market_close = util.get_market_status()

            if self.security == "STOCK":
                is_market_open = is_market_open and util.is_us_activemarket_peroid()
                is_market_close = not util.is_us_activemarket_peroid()

            equity = self.account.get_equity()
            rr = (equity - self.fixed_initial_account_size)/self.risk_manager.risk_of_an_account
            pnl = (equity - self.risk_manager.account_size)
            print(f"{'Max Account Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage*self.trades_per_day}%")
            print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")
            print(f"{'PnL'.ljust(20)}: ${round(pnl, 2)}")
            print(f"{'RR'.ljust(20)}: {round(rr, 2)}")

            if rr > 1:
                self.orders.close_all_positions()
                self.pause_trading=True

            # Each position trail stop
            self.risk_manager.trailing_stop_and_target(is_market_open=is_market_open, 
                                                              stop_multiplier=2, 
                                                              target_multiplier=self.target_ratio, 
                                                              trading_timeframe=self.trading_timeframe)

            # Exit from the position when 1 hour candle is ranging with long wicks
            emerg_exist_symbols = self.risk_manager.emergency_exit(is_market_open=is_market_open, 
                                                                   timeframe=self.trading_timeframe)
            for position_object in emerg_exist_symbols:
                self.orders.close_single_position(obj=position_object)
                
            if is_market_close:
                print("Market Close!")
                self.orders.cancel_all_pending_orders()

                # Close the positions which has risk of lossing less than 0
                for risk_positions in self.risk_manager.get_positions_at_risk():
                    self.orders.close_single_position(obj=risk_positions)
                
                # Reset account size for next day
                self.risk_manager = RiskManager(account_risk=account_risk, 
                                                position_risk=each_position_risk, 
                                                stop_ratio=self.stop_ratio, 
                                                target_ratio=self.target_ratio)
                
                self.fixed_initial_account_size = self.risk_manager.account_size
                self.pause_trading = False

            self.orders.cancel_all_pending_orders()
            
            if is_market_open and (not is_market_close) and self.wrapper.any_remaining_trades(max_trades=self.trades_per_day) and (not self.pause_trading):
                existing_positions = self.wrapper.get_active_positions(today=True)

                for symbol in curr.get_major_symbols(security=self.security):
                    # If the positions is already in trade, then don't check for signal
                    if symbol in existing_positions:
                        continue

                    current_candle = self.wrapper.get_current_candle(symbol=symbol, 
                                                                     timeframe=self.trading_timeframe)
                    
                    upper_band, lower_band = self.indicators.bollinger_bands(symbol=symbol, 
                                                                             timeframe=self.trading_timeframe, 
                                                                             window_size=20, 
                                                                             num_std_dev=2)
                    
                    market_trend = self.indicators.sma_direction(symbol=symbol, 
                                                                 timeframe=self.trading_timeframe)

                    if self.system == "3CDL_STR":
                        candle_strike = self.indicators.get_three_candle_strike(symbol=symbol, 
                                                                                timeframe=self.trading_timeframe)
                        
                        if (candle_strike == market_trend == Directions.LONG) and (current_candle["high"] < upper_band):
                            is_valid_signal, _ = self.targets.check_signal_validity(symbol=symbol, 
                                                                                    past_break_index=0, 
                                                                                    timeframe=self.trading_timeframe,
                                                                                    shoot_direction=Directions.LONG, 
                                                                                    break_level=0, 
                                                                                    reference=self.system)

                            if is_valid_signal:
                                if self.trade(direction=Directions.LONG, symbol=symbol, reference=self.system, break_level=0):
                                    break # Break the symbol loop

                        elif (candle_strike == market_trend == Directions.SHORT) and (current_candle["low"] > lower_band):
                            is_valid_signal, _ = self.targets.check_signal_validity(symbol=symbol, 
                                                                                    past_break_index=0, 
                                                                                    timeframe=self.trading_timeframe,
                                                                                    shoot_direction=Directions.SHORT, 
                                                                                    break_level=0, 
                                                                                    reference=self.system)

                            if is_valid_signal:
                                if self.trade(direction=Directions.SHORT, symbol=symbol, reference=self.system, break_level=0):
                                    break # Break the symbol loop
                            
                    if self.system == "DAILY_HL":
                        """
                        Levels such as High of the Day, Low of the day will be checked with previous bar close
                        """
                        king_of_levels = self.indicators.get_king_of_levels(symbol=symbol, 
                                                                            timeframe=self.trading_timeframe)
                        
                        previous_candle = self.wrapper.get_previous_candle(symbol=symbol, 
                                                                           timeframe=self.trading_timeframe)

                        for resistance in king_of_levels["resistance"]:
                            if (previous_candle["low"] < resistance.level and previous_candle["close"] > resistance.level):
                                is_valid_signal, candle_gap = self.targets.check_signal_validity(symbol=symbol, 
                                                                                                past_break_index=resistance.break_bar_index, 
                                                                                                timeframe=self.trading_timeframe,
                                                                                                shoot_direction=Directions.LONG, 
                                                                                                break_level=resistance.level, 
                                                                                                reference=resistance.reference)

                                if (is_valid_signal and market_trend == Directions.LONG) and (current_candle["high"] < upper_band):
                                    if self.trade(direction=Directions.LONG, symbol=symbol, reference=resistance.reference, break_level=candle_gap):
                                        break # Break the resistance loop
                    
                        for support in king_of_levels["support"]:
                            if (previous_candle["high"] > support.level and previous_candle["close"] < support.level):
                                is_valid_signal, candle_gap = self.targets.check_signal_validity(symbol=symbol, 
                                                                                                past_break_index=support.break_bar_index, 
                                                                                                timeframe=self.trading_timeframe,
                                                                                                shoot_direction=Directions.SHORT, 
                                                                                                break_level=support.level, 
                                                                                                reference=support.reference)

                                if (is_valid_signal and market_trend == Directions.SHORT) and (current_candle["low"] > lower_band):
                                    if self.trade(direction=Directions.SHORT, symbol=symbol, reference=support.reference, break_level=candle_gap):
                                        break # Break the support loop

            time.sleep(self.timer)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trader Configuration')

    parser.add_argument('--system', type=str, help='Select System 3CDL or HOD, LOD Break')
    parser.add_argument('--strategy', type=str, help='Selected Strategy')
    parser.add_argument('--security', type=str, help='Selected Type - Forex or Stock')
    parser.add_argument('--timeframe', type=int, help='Selected timeframe for trade')
    parser.add_argument('--trades_per_day', type=int, help='Number of trades per day')
    parser.add_argument('--account_risk', type=float, help='Total Account Risk for Trade Session')
    parser.add_argument('--target_ratio', type=float, help='Target ratio, assume stop is 1')
    parser.add_argument('--each_position_risk', type=float, help='Each Position risk percentage w.r.t account size') # Just Dummy
    
    args = parser.parse_args()
    
    trading_timeframe = int(args.timeframe)
    account_risk = float(args.account_risk)
    each_position_risk = float(args.each_position_risk)
    target_ratio = float(args.target_ratio)
    security = str(args.security)
    trades_per_day = int(args.trades_per_day)

    win = SmartTrader(security=security, trading_timeframe=trading_timeframe, account_risk=account_risk, each_position_risk=each_position_risk, target_ratio=target_ratio, trades_per_day=trades_per_day)
    # On the system, Are we taking break or reverse
    win.strategy = args.strategy
    # Systems should be 3 candle strike or Daily Levels
    win.system = args.system if args.system in ["3CDL_STR", "DAILY_HL"] else None

    win.main()