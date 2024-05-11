import MetaTrader5 as mt
mt.initialize()
import time
import argparse

import modules.meta.util as util
import modules.meta.Currencies as curr
from modules.meta.RiskManager import RiskManager
from modules.common.slack_msg import Slack
from modules.common.Directions import Directions
from modules.meta.Prices import Prices
from modules.meta.Orders import Orders
from modules.meta.Account import Account
from modules.meta.Indicators import Indicators
from modules.meta.wrapper import Wrapper
from modules.meta.Strategies import Strategies

class SmartTrader():
    def __init__(self, security:str, trading_timeframe:int, account_risk:float=1, 
                 each_position_risk:float=0.1, target_ratio:float=2.0, 
                 trades_per_day:int=5, num_prev_cdl_for_stop:int=2,
                 enable_trail_stop:bool=False, enable_breakeven:bool=False, start_hour:int=10):
        
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

        self.indicators = Indicators(wrapper=self.wrapper, prices=self.prices)

        self.strategies = Strategies(wrapper=self.wrapper, indicators=self.indicators)

        self.orders = Orders(prices=self.prices, risk_manager=self.risk_manager,
                             wrapper = self.wrapper)
        
        self.alert = Slack()
        self.account = Account()
        
        self.systems:str = None
        self.strategy:str = None
        
        # Account information
        self.account_name = self.account.get_account_name()

        # Expected reward for the day
        self.fixed_initial_account_size = self.risk_manager.account_size

        # Default
        self.trading_timeframe = trading_timeframe
        self.trades_per_day = trades_per_day
        self.pause_trading = False
        self.trail_stop = enable_trail_stop
        self.enable_breakeven = enable_breakeven

        # Total number of candles considered for stop is (self.num_prev_cdl_for_stop + 1) including the current candle
        self.num_prev_cdl_for_stop = num_prev_cdl_for_stop
        self.start_hour = start_hour

        # Initiate the ticker
        curr.ticker_initiator(security=security)


    def trade(self, direction:Directions, symbol:str, reference:str, break_level:float) -> bool:
        """
        This will take the trade based on given strategy
        """

        match self.strategy:
            case "break":
                method_name = "long_entry" if direction == Directions.LONG else "short_entry"
            case "reverse":
                method_name = "short_entry" if direction == Directions.LONG else "long_entry"
            case _:
                raise Exception("Strategy is not added!")
        
        method = getattr(self.orders, method_name, None)

        if method:
            status = method(symbol=symbol, 
                            reference=f"{reference}", 
                            break_level=break_level, 
                            trading_timeframe=self.trading_timeframe,
                            num_cdl_for_stop=self.num_prev_cdl_for_stop)
            return status

    
    def main(self):
        while True:
            print(f"\n------- {self.security} {self.trading_timeframe} TF {self.strategy.upper()}-----------")
            is_market_open, is_market_close = util.get_market_status(start_hour=self.start_hour)

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
            
            # if self.trading_timeframe < 240:
            #     if rr > 1:
            #         self.orders.close_all_positions()
            #         self.pause_trading=True

            # Each position trail stop
            if self.trail_stop:
                self.risk_manager.trailing_stop_and_target(stop_multiplier=self.stop_ratio, 
                                                       target_multiplier=self.target_ratio, 
                                                       trading_timeframe=self.trading_timeframe,
                                                       num_cdl_for_stop=self.num_prev_cdl_for_stop)

            # Exit from the position when candle is ranging with long wicks
            # emerg_exist_symbols = self.risk_manager.emergency_exit(is_market_open=is_market_open, 
            #                                                     timeframe=self.trading_timeframe)
            # for position_object in emerg_exist_symbols:
            #     self.orders.close_single_position(obj=position_object)
            
            if self.enable_breakeven:
                self.risk_manager.breakeven(profit_factor=2)

            if is_market_close:
                print("Market Close!")
                
                # Don't close the trades if it's more than 4 hour time frame
                if self.trading_timeframe < 240:
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
            
            if is_market_open \
                  and (not is_market_close) \
                      and (not self.pause_trading) \
                        and self.wrapper.any_remaining_trades(max_trades=self.trades_per_day):
                
                existing_positions = self.wrapper.get_active_positions(today=True)

                for symbol in curr.get_major_symbols(security=self.security):
                    # If the positions is already in trade, then don't check for signal
                    if symbol in existing_positions:
                        continue
                    
                    for system in self.systems:
                        match system:
                            case "3CDL_STR":
                                trade_direction = self.strategies.get_three_candle_strike(symbol=symbol, 
                                                                                          timeframe=self.trading_timeframe)
                                
                            case "DAILY_HL":
                                trade_direction = self.strategies.daily_high_low_breakouts(symbol=symbol, 
                                                                                          timeframe=self.trading_timeframe,
                                                                                          min_gap=2)

                            case "DAILY_HL_DOUBLE_HIT":
                                trade_direction = self.strategies.daily_high_low_breakout_double_high_hit(symbol=symbol, 
                                                                                                         timeframe=self.trading_timeframe,
                                                                                                         min_gap=2)
                        
                            case "WEEKLY_HL":
                                trade_direction = self.strategies.weekly_high_low_breakouts(symbol=symbol, 
                                                                                           timeframe=self.trading_timeframe,
                                                                                           min_gap=2)
                        
                        is_valid_signal = self.risk_manager.check_signal_validity(symbol=symbol,
                                                                                  trade_direction=trade_direction)

                        if is_valid_signal:
                            if self.trade(direction=trade_direction, symbol=symbol, reference=system, break_level=-1):
                                break # Break the symbol loop

            time.sleep(self.timer)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trader Configuration')

    parser.add_argument('--systems', type=str, help='Select System 3CDL or HOD, LOD Break')
    parser.add_argument('--strategy', type=str, help='Selected Strategy')
    parser.add_argument('--security', type=str, help='Selected Type - Forex or Stock')
    parser.add_argument('--timeframe', type=int, help='Selected timeframe for trade')
    parser.add_argument('--trades_per_day', type=int, help='Number of trades per day')
    parser.add_argument('--account_risk', type=float, help='Total Account Risk for Trade Session')
    parser.add_argument('--target_ratio', type=float, help='Target ratio, assume stop is 1')
    parser.add_argument('--each_position_risk', type=float, help='Each Position risk percentage w.r.t account size') # Just Dummy
    parser.add_argument('--num_prev_cdl_for_stop', type=int, help='Number of previous candle for stops')
    parser.add_argument('--enable_trail_stop', type=str, help='Enable Trail stop')
    parser.add_argument('--enable_breakeven', type=str, help='Enable breakeven')
    parser.add_argument('--start_hour', type=int, help='Start Hour Of Trading')
    
    args = parser.parse_args()
    
    trading_timeframe = int(args.timeframe)
    account_risk = float(args.account_risk)
    each_position_risk = float(args.each_position_risk)
    target_ratio = float(args.target_ratio)
    security = str(args.security)
    trades_per_day = int(args.trades_per_day)
    num_prev_cdl_for_stop = int(args.num_prev_cdl_for_stop)
    enable_trail_stop = util.boolean(args.enable_trail_stop)
    enable_breakeven = util.boolean(args.enable_breakeven)
    start_hour = int(args.start_hour)


    win = SmartTrader(security=security, trading_timeframe=trading_timeframe, account_risk=account_risk, 
                      each_position_risk=each_position_risk, target_ratio=target_ratio, trades_per_day=trades_per_day,
                      num_prev_cdl_for_stop=num_prev_cdl_for_stop, enable_trail_stop=enable_trail_stop,
                      enable_breakeven=enable_breakeven, start_hour=start_hour)
    
    # On the system, Are we taking break or reverse
    win.strategy = args.strategy
    # Systems should be 3 candle strike or/and Daily Levels
    win.systems = args.systems.split(",")

    win.main()


"""
If CAD is new is pushing the price up, then , Employment related news
USDCAD - DOWN
CADJPY, CADCHF -  UP

USD Michigan Consumer Related News, Price Goes Up
It didn't effect much


"""