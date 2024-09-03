import MetaTrader5 as mt
mt.initialize()
import time
import argparse
import traceback

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
from modules.common.logme import log_it

class SmartTrader():
    def __init__(self, **kwargs):
        self.timer = 15 # In Seconds
        self.stop_ratio = 1.0
        self.exited_by_pnl:bool = False
        self.notify_pnl:bool = True
        self.is_initial_run:bool= True # This helps to avoid message and pnl write while market is closed.
        self.account_trail_enabler:bool=False
        self.PnL:float = 0
        self.rr:float = 0

        # Key Arguments, Below values will be override when the risk is dynamic
        self.systems:list = kwargs["systems"]
        self.strategy:str = kwargs["strategy"] # files_util.get_strategy()
        self.account_risk = kwargs["account_risk"]
        self.each_position_risk = kwargs["each_position_risk"]
        self.enable_dynamic_position_risk = kwargs["enable_dynamic_position_risk"]
        self.multiple_positions = kwargs["multiple_positions"]
            
        # Default values
        self.target_ratio = kwargs["target_ratio"]  # Default 1:2.0 Ratio
        self.account_target_ratio = kwargs["account_target_ratio"]
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
        self.close_by_time = kwargs["close_by_time"]
        self.close_by_solid_cdl = kwargs["close_by_solid_cdl"]

        self.symbol_selection = kwargs["primary_symbols"]
        self.stop_selection = kwargs["stop_selection"]
        self.secondary_stop_selection = kwargs["secondary_stop_selection"] 
        self.enable_sec_stop_selection = kwargs["enable_sec_stop_selection"] # Even it might be TRUE, But only activate after a first trade of a symbol.

        # Applies only for 
        self.atr_check_timeframe = kwargs["atr_check_timeframe"]
        self.max_trades_on_same_direction = kwargs["max_trades_on_same_direction"]
        
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
        self.orders = Orders(prices=self.prices, risk_manager=self.risk_manager, wrapper=self.wrapper)
        
        # Account information
        self.account_name = self.account.get_account_name()

        # Expected reward for the day
        self.closed_pnl = self.wrapper.get_closed_pnl() # Only when starting the process first time

        # Initiate the ticker
        curr.ticker_initiator(security=self.security)


    def trade(self, direction:Directions, symbol:str, comment:str, break_level:float, market_entry:bool=False, stop_selection:str="ATR4H") -> bool:
        """
        Executes a trade based on the given strategy and direction.

        Parameters:
        - direction (Directions): The trade direction, either LONG or SHORT.
        - symbol (str): The trading symbol for the asset.
        - reference (str): A reference string to annotate the trade.
        - break_level (float): The price level at which the trade should be executed.
        - market_entry (bool, optional): Flag indicating whether to enter the market immediately or use another entry method. Default is False.
        - stop_selection (str, optional): Defaults to ATR4H

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
                                reference=f"{comment}", 
                                break_level=break_level, 
                                trading_timeframe=self.trading_timeframe,
                                num_cdl_for_stop=self.num_prev_cdl_for_stop,
                                market_entry=market_entry,
                                stop_selection=stop_selection)
                return status


    def close_trades_early_on_pnl(self, exit_statement="Early Close"):
        """
        Handle the closing of all active trades based on the provided Profit and Loss (PnL) and risk-reward (rr) values.

        This function performs the following actions:
        1. Closes all open trading positions using the `close_all_positions` method from the `orders` attribute.
        2. Sends an alert message via the `risk_manager`'s alert system, including the provided exit statement, trading timeframe,
        strategy name, system identifiers, PnL, and risk-reward values.
        3. Writes the PnL information to a file using `files_util.update_pnl`, which records data such as the server IP, system names,
        strategy, PnL, risk-reward ratio, and each position's risk percentage.
        4. If `record_pnl` is enabled, logs the PnL details using `files_util.record_pnl`, capturing the iteration number, PnL, rr,
        risk per position, strategy, and system names.
        5. Resets the `risk_manager` with updated risk management parameters, preparing for the next trading day.
        6. Disables the result-sending mechanism by setting `sent_result` to False.
        7. Sets `immidiate_exit` to True, indicating that the process has completed an immediate exit.

        Parameters:
        ----------
        exist_statement : str, optional
            A statement indicating the reason for early closure, by default "Early Close".
        """
        self.orders.close_all_positions()
        self.risk_manager.alert.send_msg(f"{exit_statement} : {self.trading_timeframe} : {self.risk_manager.strategy}-{'|'.join(self.systems)}: ($ {round(self.PnL, 2)})  {round(self.rr, 2)}, ${round(self.equity)}")

        # Write the pnl to a file
        files_util.update_pnl(file_name=util.get_server_ip(), system='|'.join(self.systems), strategy=self.risk_manager.strategy, pnl=self.PnL, rr=self.rr, each_pos_percentage=self.risk_manager.position_risk_percentage)
        # Update the strategy
        # self.strategy:str = files_util.get_strategy()

        if self.record_pnl:
            files_util.record_pnl(iteration=1, pnl=self.PnL, rr=self.rr, risk_per=self.risk_manager.position_risk_percentage, strategy=self.strategy, system='|'.join(self.systems))
                
        # Reset account size for next day
        self.risk_manager = RiskManager(account_risk=self.account_risk, position_risk=self.each_position_risk, stop_ratio=self.stop_ratio, 
                                        target_ratio=self.target_ratio, dynamic_postional_risk=self.enable_dynamic_position_risk,
                                        strategy=self.strategy)
                
        self.notify_pnl = False # Once sent, Disable
        self.exited_by_pnl = True


    def verbose(self):
        """
        Print the configuration and Pnl parameters in console for monitoring purposes
        """
        day, hour, minute = util.get_current_day_hour_min()
        market_status_string = util.cl_status("Inactive: ", color="red") if self.is_market_close else util.cl_status("Active: ", color="green")
        print(f"\n--- {market_status_string}{self.security} {self.trading_timeframe} TF {self.risk_manager.strategy.upper()} ---")
        print(f"{'Strategy'.ljust(20)}: {self.systems}")
        print(f"{'Day & Time'.ljust(20)}: {day}: {str(hour).zfill(2)}:{str(minute).zfill(2)}")
        print(f"{'Max Account Risk'.ljust(20)}: {self.risk_manager.account_risk_percentage}%")
        print(f"{'Positional Risk'.ljust(20)}: {self.risk_manager.position_risk_percentage}%")
        print(f"{'Max Loss'.ljust(20)}: {self.max_possible_loss}$")
        print(f"{'PnL'.ljust(20)}: ${round(self.PnL, 2)}")
        print(f"{'RR'.ljust(20)}: {round(self.rr, 2)}")
        print(f"{'Account Trail ST'.ljust(20)}: {util.cl(self.account_trail_enabler)}")
        print(f"{'Primary STP'.ljust(20)}: {util.cl(self.stop_selection)}")
        print(f"{'Secondary STP'.ljust(20)}: {util.cl(self.secondary_stop_selection)}")
        print(f"{'Secondary STP Sts'.ljust(20)}: {util.cl(self.enable_sec_stop_selection)}")
        print(f"{'Multiple Position'.ljust(20)}: {self.multiple_positions}\n")
            
        print(f"{'Primary Symb'.ljust(20)}: {util.cl(self.symbol_selection)}")
        print(f"{'Break Even Pos..n'.ljust(20)}: {util.cl(self.enable_breakeven)}")
        print(f"{'Trail ST Pos..n'.ljust(20)}: {util.cl(self.enable_trail_stop)}")
        print(f"{'Dynamic Risk'.ljust(20)}: {util.cl(self.enable_dynamic_position_risk)}")
        print(f"{'Record PnL'.ljust(20)}: {util.cl(self.record_pnl)}\n")

        print(f"{'Close by Solid CDL'.ljust(20)}: {util.cl(self.close_by_solid_cdl)}")
        print(f"{'Close by Time'.ljust(20)}: {util.cl(self.close_by_time)}\n")

        print(f"{'Neutraliser'.ljust(20)}: {util.cl(self.enable_neutralizer)}")
        print(f"{'Early Loss Exit'.ljust(20)}: {util.cl(self.max_loss_exit)}")
        print(f"{'Early Target Exit'.ljust(20)}: {util.cl(self.max_target_exit)} ({self.account_target_ratio}R)\n")

        print(f"{'Exited On PnL'.ljust(20)}: {util.cl(self.exited_by_pnl)}\n")
        
        print("System Based Parameters")
        if "ATR_BASED_DIRECTION" in self.systems:
            print(f"{'ATR TF'.ljust(20)}: {util.cl(self.atr_check_timeframe)}")
        
        if "_limit" in self.multiple_positions:
            print(f"{'Muli Positions'.ljust(20)}: {util.cl(self.max_trades_on_same_direction)}")

    def main(self):
        while True:
            self.is_market_open, self.is_market_close = util.get_market_status(start_hour=self.start_hour)

            if self.security == "STOCK":
                self.is_market_open = self.is_market_open and util.is_us_activemarket_peroid()
                self.is_market_close = not util.is_us_activemarket_peroid()

            self.equity = self.account.get_equity()
            self.max_possible_loss = round(self.risk_manager.get_max_loss())

            self.PnL = (self.equity - self.risk_manager.account_size)
            self.rr = self.PnL/self.risk_manager.risk_of_an_account

            """
            1. Retrieves all active positions and today's trades
            2. Checks if there are no active positions (`active_position.empty`) and if there are trades for today (`not today_trades.empty`).
            3. If the conditions are met, it prints a message indicating that this is the initial run with exited trades.
            4. Sets `self.exited_by_pnl` to `True` to indicate that trades have exited by profit and loss (PnL).
            5. Disables PnL notifications by setting `self.notify_pnl` to `False`.
            6. Marks the initial run as complete by setting `self.is_initial_run` to `False`.
            """
            if self.is_initial_run:
                active_position = self.wrapper.get_all_active_positions()
                today_trades = self.wrapper.get_todays_trades()
                if active_position.empty and (not today_trades.empty):
                    self.exited_by_pnl=True
                    self.notify_pnl = False
                    self.is_initial_run = False
                    print(f"Initial Entry Check: Early Exit by PnL: {self.exited_by_pnl}")

            # Print configs and pnl on console
            self.verbose()

            # Cancel all pending orders
            self.orders.cancel_all_pending_orders()

            # Check if the risk-reward ratio (RR) is greater than 1.1 or if the account trailing feature is enabled,
            # and ensure that the trade hasn't been exited by PnL, while notifications for PnL are enabled.
            """
            From the results, enabling the account trail from start will protect some of the losses rather wait till to enable at 1.1 RR
            """
            # Disabled the trail loss. So we hold the trade until the close of the market.
            # the thought behind disabling is, We don't know how the market move. Sometime it may come down and go up so we just keep the position until it close for max profit.
            # if (self.rr > 2.1 or self.account_trail_enabler) and (not self.exited_by_pnl) and self.notify_pnl:
            #     if self.risk_manager.has_daily_maximum_risk_reached() and self.max_loss_exit:
            #         self.close_trades_early_on_pnl(exit_statement="Trail Close")
                
            #     # This helps to track the account level loss once after the RR go above 1.1
            #     self.account_trail_enabler = True

            # Early exit based on max account level profit or Loss
            if ((self.rr <= -1 and self.max_loss_exit) or (self.rr > self.account_target_ratio and self.max_target_exit)) and (not self.exited_by_pnl) and self.notify_pnl:
                self.close_trades_early_on_pnl()
            
            if self.close_by_time:
                positions = self.risk_manager.close_positions_by_time(timeframe=self.trading_timeframe, wait_factor=3)
                for obj in positions:
                    self.orders.close_single_position(obj=obj)

            if self.close_by_solid_cdl:
                positions = self.risk_manager.close_positions_by_solid_candle(timeframe=self.trading_timeframe, wait_factor=1, close_check_candle=1)
                for obj in positions:
                    self.orders.close_single_position(obj=obj)

            if self.record_pnl and (not self.exited_by_pnl) and (not self.is_market_close):
                # Check if PnL recording is enabled, we are not in an immediate exit condition, and the market is still open
                # Proceed to record PnL only if there are trades made today
                if not self.wrapper.get_todays_trades().empty:
                    files_util.record_pnl(iteration=1, pnl=self.PnL, rr=self.rr, risk_per=self.risk_manager.position_risk_percentage, strategy=self.strategy, system='|'.join(self.systems))
                
                directional_pnl = self.wrapper.get_active_directional_pnl()
                if directional_pnl:
                    files_util.record_pnl_directional(long_pnl=directional_pnl.long, short_pnl=directional_pnl.short, strategy=self.strategy, system='|'.join(self.systems))


            # Each position trail stop
            if self.enable_trail_stop:
                self.risk_manager.trailing_stop_and_target(stop_multiplier=self.stop_ratio, target_multiplier=self.target_ratio, trading_timeframe=self.trading_timeframe,
                                                           num_cdl_for_stop=self.num_prev_cdl_for_stop, stop_selection=self.stop_selection)
            
            if self.enable_neutralizer:
                list_of_positions = self.risk_manager.neutralizer(enable_ratio=0.7, timeframe=self.trading_timeframe)
                for symbol, direction in list_of_positions:
                    # This helps to neutralize the reverse option while trading, It's like we take squared for us to to the squreroot
                    if self.risk_manager.strategy==Directions.REVERSE.name:
                        direction = Directions.LONG if direction == Directions.SHORT else Directions.SHORT

                    if self.trade(direction=direction, symbol=symbol, comment=f"NEUTRAL", break_level=-1, market_entry=True):
                        break
            
            if self.enable_breakeven:
                self.risk_manager.breakeven(profit_factor=1)

            if self.is_market_close:
                # Don't close the trades on market close if it's more than 4 hour time frame
                if self.trading_timeframe < 240:
                    self.orders.close_all_positions()
                
                # Update the result in Slack
                if self.notify_pnl and not self.is_initial_run:
                    self.risk_manager.alert.send_msg(f"{self.trading_timeframe} : {self.risk_manager.strategy}-{'|'.join(self.systems)}: ($ {round(self.PnL, 2)})  {round(self.rr, 2)}, ${round(self.equity)}")
                    
                    # Write the pnl to a file
                    files_util.update_pnl(file_name=util.get_server_ip(), system='|'.join(self.systems), strategy=self.risk_manager.strategy, pnl=self.PnL, rr=self.rr, each_pos_percentage=self.risk_manager.position_risk_percentage)
                    # Update the strategy
                    # self.strategy:str = files_util.get_strategy()
                
                # Reset account size for next day
                self.risk_manager = RiskManager(account_risk=self.account_risk,  position_risk=self.each_position_risk,  stop_ratio=self.stop_ratio, 
                                                target_ratio=self.target_ratio, dynamic_postional_risk=self.enable_dynamic_position_risk, strategy=self.strategy)

                self.notify_pnl = False # Once sent, Disable
                self.exited_by_pnl = False # Reset the Immidiate exit                
            
            if self.is_market_open and (not self.exited_by_pnl) \
                  and (not self.is_market_close) \
                    and self.wrapper.any_remaining_trades(max_trades=self.trades_per_day):
                
                # Enable again once market active
                self.notify_pnl = True
                
                # Once it's active in market then the initial run become deactive
                self.is_initial_run = False 

                for symbol in curr.get_symbols(security=self.security, symbol_selection=self.symbol_selection):
                    # Check is the market has resonable spread
                    # if not self.wrapper.is_reasonable_spread(symbol=symbol, pips_threshold=15):
                    #     continue

                    for system in self.systems:
                        # Reset trade direction for each system
                        trade_direction = None
                        comment = system
                        try: 
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
                                    min_gap = 2
                                    trade_direction = self.strategies.daily_high_low_breakouts(symbol=symbol, 
                                                                                            timeframe=self.trading_timeframe,
                                                                                            min_gap=min_gap)
                                case "DAILY_HL_DOUBLE_HIT":
                                    min_gap = 4
                                    trade_direction = self.strategies.daily_high_low_breakout_double_high_hit(symbol=symbol, 
                                                                                                            timeframe=self.trading_timeframe,
                                                                                                            min_gap=min_gap)
                                case "WEEKLY_HL":
                                    min_gap = 4
                                    trade_direction = self.strategies.weekly_high_low_breakouts(symbol=symbol, 
                                                                                            timeframe=self.trading_timeframe,
                                                                                            min_gap=min_gap)
                                case "D_TOP_BOTTOM":
                                    trade_direction = self.strategies.get_dtop_dbottom(symbol=symbol, 
                                                                                    timeframe=self.trading_timeframe)
                                case "HEIKIN_ASHI":
                                    trade_direction = self.strategies.get_heikin_ashi_reversal(symbol=symbol, 
                                                                                            timeframe=self.trading_timeframe)
                                case "HEIKIN_ASHI_PRE":
                                    trade_direction = self.strategies.get_heikin_ashi_pre_entry(symbol=symbol, 
                                                                                            timeframe=self.trading_timeframe)
                                case "U_REVERSAL":
                                    trade_direction, comment = self.strategies.get_u_reversal(symbol=symbol, 
                                                                                    timeframe=self.trading_timeframe)
                                case "SINGLES":
                                    trade_direction = self.strategies.strike_by_solid_candle(symbol=symbol, 
                                                                                    timeframe=self.trading_timeframe)
                                case "PREV_DAY_CLOSE_DIR":
                                    trade_direction = self.strategies.previous_day_close(symbol=symbol)
                                
                                case "ATR_BASED_DIRECTION":
                                    trade_direction = self.strategies.atr_based_direction(symbol=symbol, entry_atr_timeframe=self.atr_check_timeframe)
                                
                                case "PREV_DAY_CLOSE_DIR_ADVANCED":
                                    trade_direction = self.strategies.previous_day_close_advanced(symbol=symbol)
                                
                                case "PREV_DAY_CLOSE_DIR_HEIKIN_ASHI":
                                    trade_direction = self.strategies.previous_day_close_heikin_ashi(symbol=symbol)
                                
                                case "SAME_DIRECTION_PREV_HEIKIN":
                                    trade_direction = self.strategies.same_prev_day_direction_with_heikin(symbol=symbol)

                                case "4H_CLOSE_DIR":
                                    trade_direction = self.strategies.four_hour_close(symbol=symbol)
                                
                                case "SINGLE_SYMBOL":
                                    print(f"{'Selected Symb'.ljust(20)}: {util.cl(symbol)}")
                                    trade_direction = self.strategies.previous_candle_close(symbol=symbol, timeframe=self.trading_timeframe)
                        except Exception as e:
                            error_trace = traceback.format_exc()
                            log_it("STRATEGY_SELECTION").info(error_trace)
                                
                        if trade_direction:
                            is_valid_signal, is_opening_trade = self.risk_manager.check_signal_validity(symbol=symbol,
                                                                                      timeframe=self.trading_timeframe,
                                                                                      trade_direction=trade_direction,
                                                                                      strategy=self.risk_manager.strategy,
                                                                                      multiple_positions=self.multiple_positions,
                                                                                      max_trades_on_same_direction=self.max_trades_on_same_direction)
                            
                            if self.enable_sec_stop_selection:
                                # If it's considered as opening trade then choose the primary stop selection else choose secondary
                                dynamic_stop_selection = self.stop_selection if is_opening_trade else self.secondary_stop_selection
                            else:
                                dynamic_stop_selection = self.stop_selection
                            
                            if is_valid_signal:
                                if self.trade(direction=trade_direction, symbol=symbol, comment=comment, break_level=-1, stop_selection=dynamic_stop_selection):
                                    break # Break the symbol loop

            time.sleep(self.timer)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trader Configuration')

    parser.add_argument('--systems', type=str, help='Select System 3CDL or HOD, LOD Break')
    parser.add_argument('--strategy', type=str, help='Selected Strategy')
    parser.add_argument('--security', type=str, help='Selected Type - Forex or Stock')
    parser.add_argument('--timeframe', type=int, help='Selected timeframe for trade')
    parser.add_argument('--atr_check_timeframe', type=int, help='Selected timeframe for ATR Check entry')
    parser.add_argument('--trades_per_day', type=int, help='Number of trades per day')
    parser.add_argument('--account_risk', type=float, help='Total Account Risk for Trade Session')
    parser.add_argument('--target_ratio', type=float, help='Target ratio, assume stop is 1')
    parser.add_argument('--account_target_ratio', type=float, help='Account Target ratio, assume stop is 1')
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
    parser.add_argument('--record_pnl', type=str, help='Enable to track the PnL')
    parser.add_argument('--close_by_time', type=str, help='Close positions after x min')
    parser.add_argument('--close_by_solid_cdl', type=str, help='Close positions by solid candle after x min')
    parser.add_argument('--primary_symbols', type=str, help='Pick Only Primary Symbols')
    parser.add_argument('--primary_stop_selection', type=str, help='Stop by Candle or any other properties')
    parser.add_argument('--secondary_stop_selection', type=str, help='Stop by Candle or any other properties')
    parser.add_argument('--enable_sec_stop_selection', type=str, help='Enable secondary stop selection')
    parser.add_argument('--max_trades_on_same_direction', type=int, help='Max number of trades by direction')
    
    
    args = parser.parse_args()
    
    trading_timeframe = int(args.timeframe)
    atr_check_timeframe = int(args.atr_check_timeframe)
    each_position_risk = float(args.each_position_risk)
    account_risk =  float(args.account_risk) # each_position_risk * 10
    target_ratio = float(args.target_ratio)
    account_target_ratio = float(args.account_target_ratio)
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
    close_by_time = util.boolean(args.close_by_time)
    close_by_solid_cdl = util.boolean(args.close_by_solid_cdl)
    primary_symbols = args.primary_symbols
    stop_selection = args.primary_stop_selection
    secondary_stop_selection = args.secondary_stop_selection
    enable_sec_stop_selection = util.boolean(args.enable_sec_stop_selection)
    max_trades_on_same_direction = int(args.max_trades_on_same_direction)

    win = SmartTrader(security=security, trading_timeframe=trading_timeframe, account_risk=account_risk, 
                      each_position_risk=each_position_risk, target_ratio=target_ratio, trades_per_day=trades_per_day,
                      num_prev_cdl_for_stop=num_prev_cdl_for_stop, enable_trail_stop=enable_trail_stop,
                      enable_breakeven=enable_breakeven, enable_neutralizer=enable_neutralizer, max_loss_exit=max_loss_exit,
                      start_hour=start_hour, enable_dynamic_position_risk=enable_dynamic_position_risk, strategy=strategy,
                      systems=systems, multiple_positions=multiple_positions, max_target_exit=max_target_exit, record_pnl=record_pnl, 
                      close_by_time=close_by_time, close_by_solid_cdl=close_by_solid_cdl, primary_symbols=primary_symbols,
                      stop_selection=stop_selection, secondary_stop_selection=secondary_stop_selection, account_target_ratio=account_target_ratio,
                      enable_sec_stop_selection=enable_sec_stop_selection, atr_check_timeframe=atr_check_timeframe, 
                      max_trades_on_same_direction=max_trades_on_same_direction)

    win.main()