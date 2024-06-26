import MetaTrader5 as mt
mt.initialize()
import time
import argparse

import modules.meta.util as util
import modules.meta.Currencies as curr
from modules.meta.RiskManager import RiskManager
from modules.common.slack_msg import Slack
from modules.common.Directions import Directions
from modules.common import files_util
from modules.meta.Prices import Prices
from modules.meta.Orders import Orders
from modules.meta.Account import Account
from modules.meta.Indicators import Indicators
from modules.meta.wrapper import Wrapper
from modules.meta.Strategies import Strategies

class SmartTrader():
    def __init__(self, **kwargs):
        self.timer = 15 # In Seconds
        self.retries = 0
        self.stop_ratio = 1.0
        self.immidiate_exit = False
        self.sent_result:bool = True
        self.is_initial_run:bool= True # This helps to avoid message and pnl write while market is closed.

        # Key Arguments, Below values will be override when the risk is dynamic
        self.systems:list = kwargs["systems"]
        self.strategy:str = kwargs["strategy"]
        self.account_risk = kwargs["account_risk"]
        self.each_position_risk = kwargs["each_position_risk"]
        self.enable_dynamic_position_risk = kwargs["enable_dynamic_position_risk"]
        self.multiple_positions = kwargs["multiple_positions"]
            
        # Default values
        self.target_ratio = kwargs["target_ratio"]  # Default 1:2.0 Ratio
        self.security = kwargs["security"]
        self.trading_timeframe = kwargs["trading_timeframe"]
        self.trades_per_day = kwargs["trades_per_day"]
        self.enable_trail_stop = kwargs["enable_trail_stop"]
        self.enable_breakeven = kwargs["enable_breakeven"]
        self.enable_neutralizer = kwargs["enable_neutralizer"]
        self.max_loss_exit = kwargs["max_loss_exit"]
        self.max_target_exit = kwargs["max_target_exit"]
        # Total number of candles considered for stop is (self.num_prev_cdl_for_stop + 1) including the current candle
        self.num_prev_cdl_for_stop = kwargs["num_prev_cdl_for_stop"]
        self.start_hour = kwargs["start_hour"]
        self.record_pnl = kwargs["record_pnl"]
        

        # External dependencies
        self.risk_manager = RiskManager(account_risk=self.account_risk, 
                                        position_risk=self.each_position_risk, 
                                        stop_ratio=self.stop_ratio, 
                                        target_ratio=self.target_ratio,
                                        dynamic_postional_risk=self.enable_dynamic_position_risk,
                                        strategy=self.strategy)
        self.alert = Slack()
        self.prices = Prices()
        self.wrapper = Wrapper()
        self.account = Account()
        self.indicators = Indicators(wrapper=self.wrapper, prices=self.prices)
        self.strategies = Strategies(wrapper=self.wrapper, indicators=self.indicators)
        self.orders = Orders(prices=self.prices, risk_manager=self.risk_manager, wrapper = self.wrapper)
        
        # Account information
        self.account_name = self.account.get_account_name()

        # Expected reward for the day
        self.closed_pnl = self.wrapper.get_closed_pnl() # Only when starting the process first time

        # Initiate the ticker
        curr.ticker_initiator(security=self.security)


    def trade(self, direction:Directions, symbol:str, reference:str, break_level:float, market_entry:bool=False) -> bool:
        """
        Executes a trade based on the given strategy and direction.

        Parameters:
        - direction (Directions): The trade direction, either LONG or SHORT.
        - symbol (str): The trading symbol for the asset.
        - reference (str): A reference string to annotate the trade.
        - break_level (float): The price level at which the trade should be executed.
        - market_entry (bool, optional): Flag indicating whether to enter the market immediately or use another entry method. Default is False.

        Returns:
        - bool: True if the trade was successfully executed, False otherwise.

        Raises:
        - Exception: If the strategy is not defined in the system.
        - Exception: If the direction is not specified.

        This method decides the appropriate trading method (`long_entry` or `short_entry`) based on the strategy 
        (either BREAK or REVERSE) and the direction (LONG or SHORT). It then attempts to execute the trade using 
        the corresponding method from the `orders` object. If the method is not found, the trade is not executed.
        """
        if direction:
            match self.risk_manager.strategy:
                case Directions.BREAK.name:
                    method_name = "long_entry" if direction == Directions.LONG else "short_entry"
                case Directions.REVERSE.name:
                    method_name = "short_entry" if direction == Directions.LONG else "long_entry"
                case _:
                    raise Exception("Strategy is not added!")
            
            method = getattr(self.orders, method_name, None)

            if method:
                status = method(symbol=symbol, 
                                reference=f"{reference}_{self.risk_manager.strategy}", 
                                break_level=break_level, 
                                trading_timeframe=self.trading_timeframe,
                                num_cdl_for_stop=self.num_prev_cdl_for_stop,
                                market_entry=market_entry)
                return status
        else:
            raise Exception("Direction for Order is not defined!")

    
    def main(self):
        while True:
            print(f"\n---{self.security} {self.trading_timeframe} TF {self.risk_manager.strategy.upper()} {self.systems}---")
            is_market_open, is_market_close = util.get_market_status(start_hour=self.start_hour)

            if self.security == "STOCK":
                is_market_open = is_market_open and util.is_us_activemarket_peroid()
                is_market_close = not util.is_us_activemarket_peroid()

            equity = self.account.get_equity()

            PnL = (equity - self.risk_manager.account_size)
            rr = PnL/self.risk_manager.risk_of_an_account

            print(f"{'Max Account Risk'.ljust(20)}: {self.risk_manager.account_risk_percentage}%")
            print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")
            print(f"{'PnL'.ljust(20)}: ${round(PnL, 2)}")
            print(f"{'RR'.ljust(20)}: {round(rr, 2)}")
            print(f"{'Risk Config'.ljust(20)}: [BE: {util.cl(self.enable_breakeven)}] [Trail: {util.cl(self.enable_trail_stop)}] [DynRisk: {util.cl(self.enable_dynamic_position_risk)}]")
            print(f"{'Early Exit'.ljust(20)}: [Loss Exit: {util.cl(self.max_loss_exit)}] [Target Exit: {util.cl(self.max_target_exit)}] [Neutraliser: {util.cl(self.enable_neutralizer)}]")

            self.orders.cancel_all_pending_orders()

            # Early Exit
            if  ((rr <= -1 and self.max_loss_exit) or (rr > 1.1 and self.max_target_exit)) and (not self.immidiate_exit) and self.sent_result:
                self.immidiate_exit = True
                self.orders.close_all_positions()
                self.risk_manager.alert.send_msg(f"Early Close: {self.trading_timeframe} : {self.risk_manager.strategy}-{'|'.join(self.systems)}: ($ {round(PnL, 2)})  {round(rr, 2)}")

                # Write the pnl to a file
                files_util.update_pnl(file_name=util.get_server_ip(), system='|'.join(self.systems), strategy=self.risk_manager.strategy, pnl=PnL, rr=rr, each_pos_percentage=self.risk_manager.position_risk_percentage)
                
                # Reset account size for next day
                self.risk_manager = RiskManager(account_risk=self.account_risk, 
                                                position_risk=self.each_position_risk, 
                                                stop_ratio=self.stop_ratio, 
                                                target_ratio=self.target_ratio,
                                                dynamic_postional_risk=self.enable_dynamic_position_risk,
                                                strategy=self.strategy)
                
                self.sent_result = False # Once sent, Disable
            
            if self.record_pnl:
                pass

            # Each position trail stop
            if self.enable_trail_stop:
                self.risk_manager.trailing_stop_and_target(stop_multiplier=self.stop_ratio, 
                                                           target_multiplier=self.target_ratio, 
                                                           trading_timeframe=self.trading_timeframe,
                                                           num_cdl_for_stop=self.num_prev_cdl_for_stop)
            
            if self.enable_neutralizer:
                list_of_positions = self.risk_manager.neutralizer(enable_ratio=0.6, timeframe=self.trading_timeframe)
                for symbol, direction in list_of_positions:

                    # This helps to neutralize the reverse option while trading, It's like we take squared for us to to the squreroot
                    if self.risk_manager.strategy==Directions.REVERSE.name:
                        direction = Directions.LONG if direction == Directions.SHORT else Directions.SHORT

                    if self.trade(direction=direction, symbol=symbol, reference=f"NEUTRAL", break_level=-1, market_entry=True):
                        break
            
            if self.enable_breakeven:
                self.risk_manager.breakeven(profit_factor=1)

            if is_market_close:
                print("Market Close!")
                
                # Don't close the trades if it's more than 4 hour time frame
                if self.trading_timeframe < 240:
                    self.orders.close_all_positions()
                
                # Update the result in Slack
                if self.sent_result and not self.is_initial_run:
                    self.risk_manager.alert.send_msg(f"{self.trading_timeframe} : {self.risk_manager.strategy}-{'|'.join(self.systems)}: ($ {round(PnL, 2)})  {round(rr, 2)}")
                    
                    # Write the pnl to a file
                    files_util.update_pnl(file_name=util.get_server_ip(), system='|'.join(self.systems), strategy=self.risk_manager.strategy, pnl=PnL, rr=rr, each_pos_percentage=self.risk_manager.position_risk_percentage)
                
                # Reset account size for next day
                self.risk_manager = RiskManager(account_risk=self.account_risk, 
                                                position_risk=self.each_position_risk, 
                                                stop_ratio=self.stop_ratio, 
                                                target_ratio=self.target_ratio,
                                                dynamic_postional_risk=self.enable_dynamic_position_risk,
                                                strategy=self.strategy)

                self.sent_result = False # Once sent, Disable
                self.immidiate_exit = False # Reset the Immidiate exit
            
            if is_market_open and (not self.immidiate_exit) \
                  and (not is_market_close) \
                    and self.wrapper.any_remaining_trades(max_trades=self.trades_per_day):
                
                # Enable again once market active
                self.sent_result = True
                
                # Once it's active in market then the initial run become deactive
                self.is_initial_run = False 

                for symbol in curr.get_major_symbols(security=self.security):
                    # Check is the market has resonable spread
                    if not self.wrapper.is_reasonable_spread(symbol=symbol, pips_threshold=15):
                        continue

                    for system in self.systems:
                        # Reset trade direction for each system
                        trade_direction = None

                        match system:
                            case "3CDL_STR":
                                trade_direction = self.strategies.get_three_candle_strike(symbol=symbol, 
                                                                                          timeframe=self.trading_timeframe)
                            
                            case "4CDL_PULLBACK":
                                trade_direction = self.strategies.get_four_candle_pullback(symbol=symbol, 
                                                                                          timeframe=self.trading_timeframe)
                            
                            case "4CDL_PULLBACK_EXT":
                                trade_direction = self.strategies.get_four_candle_pullback(symbol=symbol, 
                                                                                          timeframe=self.trading_timeframe,
                                                                                          extrame=True)
                                
                            case "DAILY_HL":
                                min_gap = 2 if self.trading_timeframe==60 else 4
                                trade_direction = self.strategies.daily_high_low_breakouts(symbol=symbol, 
                                                                                          timeframe=self.trading_timeframe,
                                                                                          min_gap=min_gap)

                            case "DAILY_HL_DOUBLE_HIT":
                                min_gap = 2 if self.trading_timeframe==60 else 4
                                trade_direction = self.strategies.daily_high_low_breakout_double_high_hit(symbol=symbol, 
                                                                                                         timeframe=self.trading_timeframe,
                                                                                                         min_gap=4)
                        
                            case "WEEKLY_HL":
                                trade_direction = self.strategies.weekly_high_low_breakouts(symbol=symbol, 
                                                                                           timeframe=self.trading_timeframe,
                                                                                           min_gap=2)
                            case "D_TOP_BOTTOM":
                                trade_direction = self.strategies.get_dtop_dbottom(symbol=symbol, 
                                                                                   timeframe=self.trading_timeframe)
                            
                            case "HEIKIN_ASHI":
                                trade_direction = self.strategies.get_heikin_ashi_reversal(symbol=symbol, 
                                                                                           timeframe=self.trading_timeframe)
                            case "HEIKIN_ASHI_PRE":
                                trade_direction = self.strategies.get_heikin_ashi_pre_entry(symbol=symbol, 
                                                                                           timeframe=self.trading_timeframe)
                                
                        if trade_direction:
                            is_valid_signal = self.risk_manager.check_signal_validity(symbol=symbol,
                                                                                      timeframe=self.trading_timeframe,
                                                                                      trade_direction=trade_direction,
                                                                                      strategy=self.risk_manager.strategy,
                                                                                      multiple_positions=self.multiple_positions)
                            
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
    parser.add_argument('--enable_neutralizer', type=str, help='Enable neutralizer')
    parser.add_argument('--max_loss_exit', type=str, help='Enable Account Protect')
    parser.add_argument('--max_target_exit', type=str, help='Enable Early Profit')
    parser.add_argument('--enable_dynamic_position_risk', type=str, help='Enable dynamic risk based on past history')
    parser.add_argument('--start_hour', type=int, help='Start Hour Of Trading')
    parser.add_argument('--multiple_positions', type=str, help='How to handle multiple trades at a time: [by_trades, by_active, by_open]')
    
    
    args = parser.parse_args()
    
    trading_timeframe = int(args.timeframe)
    each_position_risk = float(args.each_position_risk)
    account_risk =  float(args.account_risk) # each_position_risk * 10
    target_ratio = float(args.target_ratio)
    security = str(args.security)
    trades_per_day = int(args.trades_per_day)
    num_prev_cdl_for_stop = int(args.num_prev_cdl_for_stop)
    enable_trail_stop = util.boolean(args.enable_trail_stop)
    enable_breakeven = util.boolean(args.enable_breakeven)
    enable_neutralizer = util.boolean(args.enable_neutralizer)
    enable_dynamic_position_risk = util.boolean(args.enable_dynamic_position_risk)
    start_hour = int(args.start_hour)
    max_loss_exit = util.boolean(args.max_loss_exit)
    max_target_exit = util.boolean(args.max_target_exit)
    strategy = args.strategy
    systems = args.systems.split(",")
    multiple_positions = args.multiple_positions
    record_pnl = util.boolean(args.record_pnl)

    win = SmartTrader(security=security, trading_timeframe=trading_timeframe, account_risk=account_risk, 
                      each_position_risk=each_position_risk, target_ratio=target_ratio, trades_per_day=trades_per_day,
                      num_prev_cdl_for_stop=num_prev_cdl_for_stop, enable_trail_stop=enable_trail_stop,
                      enable_breakeven=enable_breakeven, enable_neutralizer=enable_neutralizer, max_loss_exit=max_loss_exit,
                      start_hour=start_hour, enable_dynamic_position_risk=enable_dynamic_position_risk, strategy=strategy,
                      systems=systems, multiple_positions=multiple_positions, max_target_exit=max_target_exit, record_pnl=record_pnl)

    win.main()


"""
If CAD is new is pushing the price up, then , Employment related news
USDCAD - DOWN
CADJPY, CADCHF -  UP

USD Michigan Consumer Related News, Price Goes Up
It didn't effect much


"""