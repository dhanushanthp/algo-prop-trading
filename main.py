import MetaTrader5 as mt
mt.initialize()
import os
import time
import argparse
import traceback
from datetime import timedelta
import modules.config as config
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
from modules.meta.TradeTracker import TradeTracker
from modules.meta.DelayedEntry import DelayedEntry

class Main():
    def __init__(self, **kwargs):
        self.timer = 15 # In Seconds
        self.stop_ratio = 1.0
        self.exited_by_pnl:bool = False
        self.notify_pnl:bool = True
        # This is confirms is it a fresh run of the day, or run after a crash, If this become false then we won't be taking any trades.
        self.is_initial_run:bool= True # This helps to avoid message and pnl write while market is closed.
        self.account_trail_enabler:bool=kwargs["account_trail_enabler"]
        self.PnL:float = 0
        self.rr:float = 0
        self.dynamic_exit_rr:float = -1

        # Key Arguments, Below values will be override when the risk is dynamic
        self.strategy:str = kwargs["strategy"]
        self.market_direction:str = kwargs["market_direction"] # BREAK or REVERSE, If the dynamic is not selected then it will be used
        self.account_risk = kwargs["account_risk"]
        self.max_account_risk = kwargs["max_account_risk"]
        # self.each_position_risk = kwargs["each_position_risk"]
        self.each_position_risk = round(self.account_risk/10, 2)
        self.enable_dynamic_direction = kwargs["enable_dynamic_direction"]
        self.multiple_positions = kwargs["multiple_positions"]

        # Enter with Stop and Target or Open
        self.entry_with_st_tgt = kwargs["entry_with_st_tgt"]
            
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
        self.start_minute = kwargs["start_minute"]
        self.record_pnl = kwargs["record_pnl"]
        self.close_by_time = kwargs["close_by_time"]
        self.close_by_solid_cdl = kwargs["close_by_solid_cdl"]

        self.symbol_selection = kwargs["primary_symbols"]
        self.primary_stop_selection = kwargs["primary_stop_selection"]
        self.secondary_stop_selection = kwargs["secondary_stop_selection"] 
        self.enable_sec_stop_selection = kwargs["enable_sec_stop_selection"] # Even it might be TRUE, But only activate after a first trade of a symbol.
        self.enable_delayed_entry = kwargs["enable_delayed_entry"]
        self.enter_market_by_delay = False

        # Applies only for 
        self.atr_check_timeframe = kwargs["atr_check_timeframe"]
        self.max_trades_on_same_direction = kwargs["max_trades_on_same_direction"]

        self.stop_expected_move = kwargs["stop_expected_move"]

        self.adaptive_reentry = kwargs["adaptive_reentry"]
        self.adaptive_tolerance = kwargs["adaptive_tolerance"]

        # Dynamic Risk Management, Reentry on Loss
        self.enable_double_entry = kwargs["enable_double_entry"]
        self.active_double_entry = False

        # Once the trade is taken then the position at risk will be calculated
        self.len_position_at_risk = 0

        self.off_market_rr = 0
        self.off_market_pnl = 0
        
        # External dependencies
        self.risk_manager = RiskManager(account_risk=self.account_risk, 
                                        max_account_risk=self.max_account_risk,
                                        position_risk=self.each_position_risk, 
                                        stop_ratio=self.stop_ratio, 
                                        target_ratio=self.target_ratio,
                                        enable_dynamic_direction=self.enable_dynamic_direction,
                                        market_direction=self.market_direction,
                                        stop_expected_move=self.stop_expected_move,
                                        account_target_ratio=self.account_target_ratio, 
                                        double_entry=self.enable_double_entry)
        self.alert = Slack()
        self.prices = Prices()
        self.wrapper = Wrapper()
        self.account = Account()
        self.indicators = Indicators(wrapper=self.wrapper, prices=self.prices)
        self.strategies = Strategies(wrapper=self.wrapper, indicators=self.indicators)
        self.orders = Orders(prices=self.prices, risk_manager=self.risk_manager, wrapper=self.wrapper)
        self.trade_tracker = TradeTracker()
        self.delayed_entry = DelayedEntry(indicators=self.indicators, strategies=self.strategies, risk_manager=self.risk_manager)
        
        # Account information
        self.account_name = self.account.get_account_name()

        # Expected reward for the day
        self.closed_pnl = self.wrapper.get_closed_pnl() # Only when starting the process first time

        # Initiate the ticker
        curr.ticker_initiator(security=self.security, symbol_selection=self.symbol_selection)

        # Get the trading symbols
        self.trading_symbols = curr.get_symbols(security=self.security, symbol_selection=self.symbol_selection)

        self.rr_change = 0
        self.rr_chage_prior = 0

    def trade(self, direction:Directions, symbol:str, comment:str, break_level:float, market_entry:bool=False, stop_selection:str="ATR4H", entry_with_st_tgt:bool=True) -> bool:
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
        method_name = None

        if direction:
            match self.risk_manager.market_direction:
                case Directions.BREAK.name:
                    method_name = "long_entry" if direction == Directions.LONG else "short_entry"
                case Directions.REVERSE.name:
                    method_name = "short_entry" if direction == Directions.LONG else "long_entry"
                case _:
                    # Because some cases if the chart is not loaded then the direction will be UKNOWN
                    log_it("DIR_TRADE_SELECTION").info(f"{symbol}: Trade Skip! Direction not defined!")
            
            # Only take trades with valid method names
            if method_name in ["long_entry", "short_entry"]:
                method = getattr(self.orders, method_name, None)

                if method:
                    status = method(symbol=symbol, 
                                    reference=f"{comment}", 
                                    break_level=break_level, 
                                    trading_timeframe=self.trading_timeframe,
                                    num_cdl_for_stop=self.num_prev_cdl_for_stop,
                                    market_entry=market_entry,
                                    stop_selection=stop_selection,
                                    entry_with_st_tgt=entry_with_st_tgt)
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
        self.risk_manager.alert.send_msg(f"{util.get_account_name()} - {config.local_ip} : {self.risk_manager.market_direction}-{self.strategy}: ($ {round(self.PnL, 2)})  {round(self.rr, 2)}, ${round(self.equity)}")

        account_risk_percentage = self.risk_manager.account_risk_percentage
        # This is because we are dividing the risk by 2, So we need to multiply by 2 to get the actual risk
        if self.enable_double_entry:
            account_risk_percentage = account_risk_percentage * 2

        # Write the pnl to a file
        self.trade_tracker.daily_pnl_track(pnl=self.PnL, rr=self.rr, strategy=self.strategy, market_direction=self.risk_manager.market_direction, account_risk_percentage=account_risk_percentage, 
                                           each_position_risk_percentage=self.risk_manager.position_risk_percentage, equity=self.equity)

        if self.record_pnl:
            self.trade_tracker.record_pnl_logs(pnl=self.PnL, rr=self.rr, rr_change=self.rr_change)
                
        # Reset account size for next day
        self.risk_manager = RiskManager(account_risk=self.account_risk, max_account_risk=self.max_account_risk, position_risk=self.each_position_risk, stop_ratio=self.stop_ratio, 
                                        target_ratio=self.target_ratio, enable_dynamic_direction=self.enable_dynamic_direction,
                                        market_direction=self.market_direction, stop_expected_move=self.stop_expected_move, account_target_ratio=self.account_target_ratio, 
                                        double_entry=self.enable_double_entry)
                
        self.notify_pnl = False # Once sent, Disable
        self.exited_by_pnl = True
        self.enter_market_by_delay = False
        self.active_double_entry = False # Reset the double entry


    def verbose(self):
        """
        Print the configuration and Pnl parameters in console for monitoring purposes
        """
        os.system('cls' if os.name == 'nt' else 'clear')
        day, hour, minute = util.get_current_day_hour_min()
        market_status_string = util.cl_status("Inactive: ", color="red") if self.is_market_close else util.cl_status("Active: ", color="green")
        print(f"\n--- {market_status_string}{self.security} {self.trading_timeframe} TF {self.risk_manager.market_direction.upper()} ---")
        if self.is_market_close:
            print(f"{'Market Open at '.ljust(20)}: {self.start_hour}:{str(self.start_minute).zfill(2)}")

        print(util.cl_status("\nBASIC CONDITIONS", "yellow"))
        print(f"{'Primary Symb'.ljust(20)}: {util.cl(self.symbol_selection)}")
        print(f"{'Day & Time'.ljust(20)}: {day}: {str(hour).zfill(2)}:{str(minute).zfill(2)}")
        print(f"{'PnL'.ljust(20)}: ${round(self.PnL, 2)}")
        print(f"{'RR'.ljust(20)}: {round(self.rr, 2)}\n")

        print(f"{'Strategy'.ljust(20)}: {self.strategy}")
        # print(f"{'Adaptive Re-Entry'.ljust(20)}: {util.cl(self.adaptive_reentry)}")
        print(f"{'Entry with ST & TGT'.ljust(20)}: {util.cl(self.entry_with_st_tgt)}")
        print(f"{'Multiple Position'.ljust(20)}: {self.multiple_positions}")
        if "ATR_BASED_DIRECTION" == self.strategy:
            print(f"{'ATR TF'.ljust(20)}: {util.cl(self.atr_check_timeframe)}")
        
        if "_limit" in self.multiple_positions:
            print(f"{'Multi Positions'.ljust(20)}: {util.cl(self.max_trades_on_same_direction)}")

        print(util.cl_status("\nRISK CONDITIONS", "yellow"))
        print(f"{'Target Ratio'.ljust(20)}: 1:{int(self.target_ratio)}")
        print(f"{'Max Account Risk %'.ljust(20)}: {round(self.risk_manager.account_risk_percentage, 2)}%")
        print(f"{'Max Account Risk $'.ljust(20)}: ${round(self.risk_manager.risk_of_an_account, 2)}")
        print(f"{'Positional Risk %'.ljust(20)}: {round(self.risk_manager.position_risk_percentage, 2)}%")
        print(f"{'Positional Risk $ '.ljust(20)}: ${round(self.risk_manager.risk_of_a_position, 2)}")
        print(f"{'Ada. Risk Tolarance'.ljust(20)}: ${round(self.risk_manager.risk_of_a_position*self.adaptive_tolerance, 2)}")
        print(f"{'Max Loss'.ljust(20)}: ${self.max_possible_loss}")
        
        print(util.cl_status("\nSTOP CONDITIONS", "yellow"))
        print(f"{'STOP SELECTION'.ljust(20)}: {util.cl(self.primary_stop_selection)}")
        if self.primary_stop_selection == "FACTOR":
            print(f"{'Factor STP %'.ljust(20)}: {util.cl(self.primary_stop_selection)}, {util.cl(self.stop_expected_move)}{util.cl('%')}")
        else:
            print(f"{'Primary STP Status'.ljust(20)}: {util.cl(self.primary_stop_selection)}")
        # print(f"{'Secondary STP Status'.ljust(20)}: {util.cl(self.enable_sec_stop_selection)}")
        # print(f"{'Secondary STP'.ljust(20)}: {util.cl(self.secondary_stop_selection)}\n")
        
        # print(f"{'Break Even Pos..n'.ljust(20)}: {util.cl(self.enable_breakeven)}")
        # print(f"{'Trail ST Pos..n'.ljust(20)}: {util.cl(self.enable_trail_stop)}")
        print(f"{'Account Trail ST'.ljust(20)}: {util.cl(self.account_trail_enabler)}")
        print(f"{'Dynamic Direction'.ljust(20)}: {util.cl(self.enable_dynamic_direction)}")
        print(f"{'Record PnL'.ljust(20)}: {util.cl(self.record_pnl)}\n")

        # print(f"{'Close by Solid CDL'.ljust(20)}: {util.cl(self.close_by_solid_cdl)}")
        # print(f"{'Close by Time'.ljust(20)}: {util.cl(self.close_by_time)}\n")

        
        # print(f"{'Neutraliser'.ljust(20)}: {util.cl(self.enable_neutralizer)}")
        print(f"{'Early Loss Exit'.ljust(20)}: {util.cl(self.max_loss_exit)}")
        print(f"{'Early Target Exit'.ljust(20)}: {util.cl(self.max_target_exit)} ({self.risk_manager.account_target_ratio} R)\n")

        print(util.cl_status("DOUBLE ENTRY", "yellow"))
        print(f"{'IS ENABLED'.ljust(20)}: {util.cl(self.enable_double_entry)}")
        print(f"{'IS ACTIVE'.ljust(20)}: {util.cl(self.active_double_entry)}\n")

        print(util.cl_status("DELAYED ENTRY", "yellow"))
        print(f"{'IS ENABLED'.ljust(20)}: {util.cl(self.enable_delayed_entry)}")
        print(f"{'IS ACTIVE'.ljust(20)}: {util.cl(self.enter_market_by_delay)}\n")


        print(f"{'Exited On PnL'.ljust(20)}: {util.cl(self.exited_by_pnl)}")
        print(f"{'RR Change'.ljust(20)}: {util.cl(self.rr_change)}")
        print(f"{'Dynamic RR'.ljust(20)}: {util.cl(self.dynamic_exit_rr)}")

        # print(util.cl_status("\nOFF MARKET", "yellow"))
        # print(f"{'RR'.ljust(20)}: {util.cl(self.off_market_rr)}")
        # print(f"{'PNL'.ljust(20)}: {util.cl(round(self.off_market_pnl, 2))}")


    def trading_activated(self):
        """
        Determines if trading is activated based on several conditions.
        Returns:
            bool: True if trading is activated, False otherwise.
        Conditions:
            - The market is open.
            - The trading has not been exited by PnL (Profit and Loss).
            - The market is not closed.
            - There are remaining trades available for the day.
        """
        return self.is_market_open and (not self.exited_by_pnl) \
                and (not self.is_market_close) \
                and self.wrapper.any_remaining_trades(max_trades=self.trades_per_day)
    
    def main(self):
        while True:
            self.is_market_open, self.is_market_close = util.get_market_status(start_hour=self.start_hour, start_minute=self.start_minute)
            self.rr_change, _, _ = self.trade_tracker.get_rr_change()

            if self.security == "STOCK":
                self.is_market_open = self.is_market_open and util.is_us_activemarket_peroid()
                self.is_market_close = not util.is_us_activemarket_peroid()

            self.equity = self.account.get_equity()
            self.max_possible_loss = round(self.risk_manager.get_max_loss())

            try:
                self.PnL = (self.equity - self.risk_manager.account_size)
                self.rr = self.PnL/self.risk_manager.risk_of_an_account
            except Exception as e:
                self.rr = 0

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
                    print(f"\n************* Initial Entry Check: Early Exit by PnL: {self.exited_by_pnl} *************")

            # Cancel all pending orders
            self.orders.cancel_all_pending_orders()

            # Check if the risk-reward ratio (RR) is greater than 1.1 or if the account trailing feature is enabled,
            # and ensure that the trade hasn't been exited by PnL, while notifications for PnL are enabled.
            """
            From the results, enabling the account trail from start will protect some of the losses rather wait till to enable at 1.1 RR
            """
            # Disabled the trail loss. So we hold the trade until the close of the market.
            # the thought behind disabling is, We don't know how the market move. Sometime it may come down and go up so we just keep the position until it close for max profit.
            # Also this helps to protect he down side of the market as well.
            if self.account_trail_enabler and (not self.exited_by_pnl) and self.notify_pnl:
                if self.risk_manager.has_daily_maximum_risk_reached() and self.max_loss_exit:
                    self.close_trades_early_on_pnl(exit_statement="Trail Close")
                
                # This helps to track the account level loss once after the RR go above 1.1
                self.account_trail_enabler = True

            """
            Enable account level breakeven when RR hit 0.8 RR, This way we protect the downside of it.
            # Just accept the loss, that what you have agreed for...

            Later note: I have increased the Max target to 4, so If the price move above 2 then goes back make it break even.

            Later Note: I have moved the break even to Max target rather exit, So that the exit will happen based on the RR change more than 1, However If the price move below then it will exit with max target RR
            """
            # if self.rr > 2:
            #     self.dynamic_exit_rr = 0.1

            # Early exit based on max account level profit or Loss
            if ((
                (self.rr <= self.dynamic_exit_rr and self.max_loss_exit) 
                 or (self.rr > 2 and self.rr_change >= 1 and (self.rr_change < self.rr_chage_prior) and self.max_target_exit) # Once the RR change is goes above 1RR and the once it's start decreaing then take the exist,
                 or (self.rr > self.risk_manager.account_target_ratio and self.max_target_exit and (not self.rr_change > 1))) # Exit based on the Dynamic RR, Once the RR change goes above 1, this logic will be deactivated, Where this will try to take max profit based on the sudden hype.
                and (not self.exited_by_pnl) and self.notify_pnl):
                self.close_trades_early_on_pnl()
            
            # This should be come below the self.rr_change exit check.
            self.rr_chage_prior = self.rr_change

            """
            Once after a loss of a possition entry in to opposite direction, This will help to recover the loss in the same day. But not 100% Certain
            """
            if self.enable_double_entry:
                # Check the PnL
                # The max rr will avoid the over trading above 2 losses
                # or (self.off_market_rr <= -1.0 and self.off_market_rr > -2.0)
                if (self.rr <= -1.0 and self.rr > -2.0):
                    # Check the existing positions
                    active_position = self.wrapper.get_all_active_positions()
                    # When it's not a initial run condition and active position become zero
                    if active_position.empty:
                        self.active_double_entry = True
                        # Reset account size for next day
                        self.risk_manager = RiskManager(account_risk=self.account_risk, max_account_risk=self.max_account_risk,  position_risk=self.each_position_risk,  stop_ratio=self.stop_ratio, 
                                                target_ratio=self.target_ratio, enable_dynamic_direction=self.enable_dynamic_direction, market_direction=self.market_direction,
                                                stop_expected_move=self.stop_expected_move,  account_target_ratio=self.account_target_ratio, 
                                                double_entry=self.enable_double_entry)
                        
                        # Toggle the Direction, Note this could be a double loss as well in come cases
                        # This remains the same until the market close or next postion exit
                        self.risk_manager.market_direction = "BREAK" if self.risk_manager.market_direction == "REVERSE" else "REVERSE"

                        # Since we are changing the direction, we need to reset the RR that includes the previous loss position as well.
                        self.dynamic_exit_rr = -2
                        
                        self.exited_by_pnl = False # Reset the Immidiate exit
                        self.notify_pnl = True # Once opening a trade, enable again
                        self.is_initial_run = False # Once this is disabled, the process will not come in the double entry condition and other conditions remains same
                        self.rr_change = 0 # Reset the RR change


            if self.close_by_time:
                positions = self.risk_manager.close_positions_by_time(timeframe=self.trading_timeframe, wait_factor=3)
                for obj in positions:
                    self.orders.close_single_position(obj=obj)


            if self.close_by_solid_cdl:
                positions = self.risk_manager.close_positions_by_solid_candle(timeframe=self.trading_timeframe, wait_factor=1, close_check_candle=1)
                for obj in positions:
                    self.orders.close_single_position(obj=obj)

            if self.adaptive_reentry and not self.exited_by_pnl:
                """
                Close the positions which are at risk and take the opposite direction of the previous entry. This is individual position based re entry strategy
                """
                position_at_risk = self.trade_tracker.symbol_historic_pnl(each_position_risk_appertide=self.risk_manager.risk_of_a_position * self.adaptive_tolerance)
                self.len_position_at_risk = len(position_at_risk)
                print(f"\nPosition at Risk: {position_at_risk}")
                if self.len_position_at_risk > 0:
                    # No need to check the today trades if the position at risk is empty
                    today_trades = self.wrapper.get_todays_trades()
                    today_trades = today_trades[today_trades["entry"] == 0]
                    # Last traded direction
                    position_dict = dict(zip(today_trades["symbol"], today_trades["type"]))
                    today_trades = today_trades.groupby("symbol")["type"].count().reset_index(name="count")

                    # Only position traded once
                    trades_with_single_entry = today_trades[today_trades["count"] == 1]["symbol"].unique() 
                    
                    for symbol in position_at_risk:
                        if symbol in trades_with_single_entry:
                            # Once the postion is closed, the re entry will be taken care by the adaptive re-entry below
                            self.orders.close_single_position_by_symbol(symbol=symbol)
                
                    time.sleep(3)

            # Record PNL even once after the positions are exit based on todays trades
            # This helps to track the PnL based on the trades taken today
            if not self.wrapper.get_todays_trades().empty and not self.is_market_close:
                # The reason added out of the IF condition to calculate the positional PnL for each Symbol
                self.off_market_pnl, symbol_pnl = self.risk_manager.calculate_trades_based_pnl()
                if self.exited_by_pnl:
                    self.off_market_rr = round(self.off_market_pnl/self.risk_manager.risk_of_an_account, 2)
                else:
                    # symbol_pnl = self.wrapper.get_all_active_positions()[["symbol", "profit"]]
                    # symbol_pnl = symbol_pnl.rename({"profit": "net_pnl"}, axis=1)
                    self.off_market_pnl = self.PnL
                    self.off_market_rr = round(self.rr, 2)
                
                self.trade_tracker.record_pnl_logs(pnl=self.off_market_pnl, rr=self.off_market_rr, rr_change=self.rr_change)
                # self.trade_tracker.record_symbol_pnl_logs(pnl_df=symbol_pnl)


            # Each position trail stop
            if self.enable_trail_stop:
                self.risk_manager.trailing_stop_and_target(stop_multiplier=self.stop_ratio, target_multiplier=self.target_ratio, trading_timeframe=self.trading_timeframe,
                                                           num_cdl_for_stop=self.num_prev_cdl_for_stop, stop_selection=self.primary_stop_selection)
            
            if self.enable_neutralizer:
                list_of_positions = self.risk_manager.neutralizer(enable_ratio=0.7, timeframe=self.trading_timeframe)
                for symbol, direction in list_of_positions:
                    # This helps to neutralize the reverse option while trading, It's like we take squared for us to to the squreroot
                    if self.risk_manager.market_direction==Directions.REVERSE.name:
                        direction = Directions.LONG if direction == Directions.SHORT else Directions.SHORT

                    if self.trade(direction=direction, symbol=symbol, comment=f"NEUTRAL", break_level=-1, market_entry=True):
                        break
            

            if self.enable_breakeven:
                self.risk_manager.breakeven(profit_factor=1)


            if self.is_market_close:
                # Close all positions
                self.orders.close_all_positions()
                
                # Update the result in Slack
                if self.notify_pnl and not self.is_initial_run:
                    self.risk_manager.alert.send_msg(f"{util.get_account_name()} - {config.local_ip} : {self.risk_manager.market_direction}-{self.strategy}: ($ {round(self.PnL, 2)})  {round(self.rr, 2)}, ${round(self.equity)}")

                    account_risk_percentage = self.risk_manager.account_risk_percentage
                    # This is because we are dividing the risk by 2, So we need to multiply by 2 to get the actual risk
                    if self.enable_double_entry:
                        account_risk_percentage = account_risk_percentage * 2

                    # Write the pnl to a file
                    self.trade_tracker.daily_pnl_track(pnl=self.PnL, rr=self.rr, strategy=self.strategy, market_direction=self.risk_manager.market_direction, account_risk_percentage=account_risk_percentage, 
                                                       each_position_risk_percentage=self.risk_manager.position_risk_percentage, equity=self.equity)
                
                # Reset account size for next day
                self.risk_manager = RiskManager(account_risk=self.account_risk, max_account_risk=self.max_account_risk, position_risk=self.each_position_risk,  stop_ratio=self.stop_ratio, 
                                                target_ratio=self.target_ratio, enable_dynamic_direction=self.enable_dynamic_direction, market_direction=self.market_direction,
                                                stop_expected_move=self.stop_expected_move,  account_target_ratio=self.account_target_ratio, 
                                                double_entry=self.enable_double_entry)

                self.notify_pnl = False # Once sent, Disable
                self.exited_by_pnl = False # Reset the Immidiate exit
                self.dynamic_exit_rr = -1 # Reset the exit RR to -1
                self.rr_change = 0 # Reset the RR change
                self.enter_market_by_delay = False # reset the delayed entry
                self.active_double_entry = False # Reset the double entry

            # Enable delayed entry based on the tracked performance
            if self.enable_delayed_entry:
                # Record the Pnl Pre for perfect entry
                if self.trading_activated():
                    self.delayed_entry.symbol_price_recorder(symbols=self.trading_symbols)
                
                    get_delay_signal = self.delayed_entry.is_max_ranged()
                    print(f"\n{'Pre Tracked RR'.ljust(20)}: {self.delayed_entry.delayed_rr()}")
                    print(f"{'Pre Track Signal'.ljust(20)}: {get_delay_signal}")
                
                    if get_delay_signal:
                        self.enter_market_by_delay = True    
            else:
                self.enter_market_by_delay = True

            # Print configs and pnl on console
            self.verbose()

            if self.trading_activated() and self.enter_market_by_delay:

                # Enable again once market active
                self.notify_pnl = True
                
                # Once it's active in market then the initial run become deactive
                self.is_initial_run = False 
                current_active_positions = self.wrapper.get_active_positions()

                for symbol in self.trading_symbols:
                    # Skip the symbol if it's already in active positions
                    if symbol in current_active_positions:
                        continue

                    # Reset trade direction for each symbol
                    trade_direction = None
                    comment = self.strategy
                    
                    try: 
                        match self.strategy:
                            case "3CDL_STR":
                                trade_direction = self.strategies.get_three_candle_strike(symbol=symbol, 
                                                                                        timeframe=self.trading_timeframe)
                            case "3CDL_REV":
                                trade_direction = self.strategies.get_three_candle_reverse(symbol=symbol, 
                                                                                            timeframe=self.trading_timeframe)                 
                            case "4CDL_PULLBACK":
                                trade_direction = self.strategies.get_four_candle_reversal(symbol=symbol, 
                                                                                        timeframe=self.trading_timeframe)
                            case "4CDL_PULLBACK_EXT":
                                trade_direction = self.strategies.get_four_candle_reversal(symbol=symbol, 
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
                            
                            case "HEIKIN_ASHI_3CDL_REV":
                                trade_direction = self.strategies.get_heikin_ashi_3_cdl_reversal(symbol=symbol, 
                                                                                        timeframe=self.trading_timeframe, start=1)

                            case "U_REVERSAL":
                                trade_direction, comment = self.strategies.get_u_reversal(symbol=symbol, 
                                                                                timeframe=self.trading_timeframe)
                            case "SINGLES":
                                trade_direction = self.strategies.strike_by_solid_candle(symbol=symbol, 
                                                                                timeframe=self.trading_timeframe)
                            case "PREV_DAY_CLOSE_DIR":
                                trade_direction = self.strategies.previous_day_close(symbol=symbol)

                            case "3CDL_ESCAPE":
                                trade_direction = self.strategies.get_three_candle_escape(symbol=symbol)
                            
                            case "TODAY_DOMINATION":
                                trade_direction = self.strategies.today_domination(symbol=symbol)
                            
                            case "PREV_DAY_CLOSE_DIR_MKT_DOMINATION":
                                trade_direction = self.indicators.get_dominant_market_actual_direction()
                            
                            case "DAY_CLOSE_SMA":
                                trade_direction = self.strategies.day_close_sma(symbol=symbol)
                            
                            case "PREV_DAY_CLOSE_DIR_PREV_HIGH_LOW":
                                trade_direction = self.strategies.previous_day_close_prev_high_low(symbol=symbol)
                            
                            case "ATR_BASED_DIRECTION":
                                trade_direction = self.strategies.atr_referenced_previous_close_direction(symbol=symbol, entry_atr_timeframe=self.atr_check_timeframe)
                            
                            case "PREV_DAY_CLOSE_DIR_ADVANCED":
                                trade_direction = self.strategies.previous_day_close_advanced(symbol=symbol)
                            
                            case "PREV_DAY_CLOSE_DIR_HEIKIN_ASHI":
                                trade_direction = self.strategies.previous_day_close_heikin_ashi(symbol=symbol)
                            
                            case "SAME_DIRECTION_PREV_HEIKIN":
                                trade_direction = self.strategies.same_prev_day_direction_with_heikin(symbol=symbol)

                            case "4H_CLOSE_DIR":
                                trade_direction = self.strategies.four_hour_close(symbol=symbol)
                            
                            case "PEAK_REVERSAL":
                                trade_direction = self.strategies.get_peak_level_revesals(symbol=symbol, timeframe=self.trading_timeframe)
                            
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
                                                                                    strategy=self.risk_manager.market_direction,
                                                                                    multiple_positions=self.multiple_positions,
                                                                                    max_trades_per_day=self.max_trades_on_same_direction)
                        
                        if self.enable_sec_stop_selection:
                            # If it's considered as opening trade then choose the primary stop selection else choose secondary
                            dynamic_stop_selection = self.primary_stop_selection if is_opening_trade else self.secondary_stop_selection
                        else:
                            dynamic_stop_selection = self.primary_stop_selection
                        
                        # Pending trades basedon waiting signal
                        if not is_valid_signal:
                            print(f"{symbol}: {trade_direction}")

                        if self.adaptive_reentry and self.len_position_at_risk > 0:
                            if self.risk_manager.market_direction == Directions.BREAK.name:
                                trade_direction = Directions.SHORT if position_dict[symbol] == 0 else Directions.LONG
                            else:
                                # If the strategy is REVERSE then the trade direction will be opposite to the last trade
                                trade_direction = Directions.LONG if position_dict[symbol] == 0 else Directions.SHORT

                        if is_valid_signal:
                            self.trade(direction=trade_direction, symbol=symbol, comment=comment, break_level=-1, stop_selection=dynamic_stop_selection, entry_with_st_tgt=self.entry_with_st_tgt)

            time.sleep(self.timer)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trader Configuration')

    parser.add_argument('--strategy', type=str, help='Select System 3CDL or HOD, LOD Break')
    parser.add_argument('--market_direction', type=str, help='Selected Strategy')
    parser.add_argument('--security', type=str, help='Selected Type - Forex or Stock')
    parser.add_argument('--timeframe', type=int, help='Selected timeframe for trade')
    parser.add_argument('--atr_check_timeframe', type=int, help='Selected timeframe for ATR Check entry')
    parser.add_argument('--trades_per_day', type=int, help='Number of trades per day')
    parser.add_argument('--account_risk', type=float, help='Total Account Risk for Trade Session')
    parser.add_argument('--max_account_risk', type=float, help='Total Account Risk for Trade Session')
    parser.add_argument('--target_ratio', type=float, help='Target ratio, assume stop is 1')
    parser.add_argument('--account_target_ratio', type=float, help='Account Target ratio, assume stop is 1')
    parser.add_argument('--each_position_risk', type=float, help='Each Position risk percentage w.r.t account size') # Just Dummy
    parser.add_argument('--num_prev_cdl_for_stop', type=int, help='Number of previous candle for stops')
    parser.add_argument('--enable_trail_stop', type=str, help='Enable Trail stop')
    parser.add_argument('--enable_breakeven', type=str, help='Enable breakeven')
    parser.add_argument('--enable_neutralizer', type=str, help='Enable neutralizer')
    parser.add_argument('--entry_with_st_tgt', type=str, help='Entry with Target and Stop')
    parser.add_argument('--max_loss_exit', type=str, help='Enable Account Protect')
    parser.add_argument('--max_target_exit', type=str, help='Enable Early Profit')
    parser.add_argument('--enable_dynamic_direction', type=str, help='Enable dynamic direction')
    parser.add_argument('--start_hour', type=int, help='Start Hour Of Trading')
    parser.add_argument('--start_minute', type=int, help='Start Minute Of Trading')
    parser.add_argument('--multiple_positions', type=str, help='How to handle multiple trades at a time: [by_trades, by_active, by_open]')
    parser.add_argument('--record_pnl', type=str, help='Enable to track the PnL')
    parser.add_argument('--close_by_time', type=str, help='Close positions after x min')
    parser.add_argument('--close_by_solid_cdl', type=str, help='Close positions by solid candle after x min')
    parser.add_argument('--primary_symbols', type=str, help='Pick Only Primary Symbols')
    parser.add_argument('--primary_stop_selection', type=str, help='Stop by Candle or any other properties')
    parser.add_argument('--stop_expected_move', type=float, help='% of expected move of an symbol based on the price')
    parser.add_argument('--account_trail_enabler', type=str, help='Enable/Disable Account Trail')
    parser.add_argument('--secondary_stop_selection', type=str, help='Stop by Candle or any other properties')
    parser.add_argument('--enable_sec_stop_selection', type=str, help='Enable secondary stop selection')
    parser.add_argument('--max_trades_on_same_direction', type=int, help='Max number of trades by direction')
    parser.add_argument('--adaptive_reentry', type=str, help='Reentry based on the RR hit')
    parser.add_argument('--adaptive_tolerance', type=float, help='The factor of the each position, that flip based on the pnl')
    parser.add_argument('--enable_delayed_entry', type=str, help='Enable Delayed Entry')
    parser.add_argument('--enable_double_entry', type=str, help='Enable Double Entry on Loose Position')
    
    
    args = parser.parse_args()
    
    trading_timeframe = int(args.timeframe)
    atr_check_timeframe = int(args.atr_check_timeframe)
    each_position_risk = float(args.each_position_risk)
    account_risk =  float(args.account_risk) # each_position_risk * 10
    max_account_risk = float(args.max_account_risk)
    target_ratio = float(args.target_ratio)
    account_target_ratio = float(args.account_target_ratio)
    security = str(args.security)
    trades_per_day = int(args.trades_per_day)
    num_prev_cdl_for_stop = int(args.num_prev_cdl_for_stop)
    enable_trail_stop = util.boolean(args.enable_trail_stop)
    enable_breakeven = util.boolean(args.enable_breakeven)
    enable_neutralizer = util.boolean(args.enable_neutralizer)
    enable_dynamic_direction = util.boolean(args.enable_dynamic_direction)
    start_hour = int(args.start_hour)
    start_minute = int(args.start_minute)
    max_loss_exit = util.boolean(args.max_loss_exit)
    max_target_exit = util.boolean(args.max_target_exit)
    market_direction = args.market_direction
    strategy = args.strategy
    multiple_positions = args.multiple_positions
    record_pnl = util.boolean(args.record_pnl)
    close_by_time = util.boolean(args.close_by_time)
    close_by_solid_cdl = util.boolean(args.close_by_solid_cdl)
    primary_symbols = args.primary_symbols
    primary_stop_selection = args.primary_stop_selection
    secondary_stop_selection = args.secondary_stop_selection
    enable_sec_stop_selection = util.boolean(args.enable_sec_stop_selection)
    max_trades_on_same_direction = int(args.max_trades_on_same_direction)
    entry_with_st_tgt = util.boolean(args.entry_with_st_tgt)
    stop_expected_move = float(args.stop_expected_move)
    account_trail_enabler = util.boolean(args.account_trail_enabler)
    adaptive_reentry = util.boolean(args.adaptive_reentry)
    adaptive_tolerance = float(args.adaptive_tolerance)
    enable_delayed_entry = util.boolean(args.enable_delayed_entry)
    enable_double_entry = util.boolean(args.enable_double_entry)

    win = Main(security=security, trading_timeframe=trading_timeframe, account_risk=account_risk, max_account_risk=max_account_risk,
                      each_position_risk=each_position_risk, target_ratio=target_ratio, trades_per_day=trades_per_day,
                      num_prev_cdl_for_stop=num_prev_cdl_for_stop, enable_trail_stop=enable_trail_stop,
                      enable_breakeven=enable_breakeven, enable_neutralizer=enable_neutralizer, max_loss_exit=max_loss_exit,
                      start_hour=start_hour, start_minute=start_minute, enable_dynamic_direction=enable_dynamic_direction, market_direction=market_direction,
                      strategy=strategy, multiple_positions=multiple_positions, max_target_exit=max_target_exit, record_pnl=record_pnl, 
                      close_by_time=close_by_time, close_by_solid_cdl=close_by_solid_cdl, primary_symbols=primary_symbols,
                      primary_stop_selection=primary_stop_selection, secondary_stop_selection=secondary_stop_selection, account_target_ratio=account_target_ratio,
                      enable_sec_stop_selection=enable_sec_stop_selection, atr_check_timeframe=atr_check_timeframe, 
                      max_trades_on_same_direction=max_trades_on_same_direction, entry_with_st_tgt=entry_with_st_tgt,
                      stop_expected_move=stop_expected_move, account_trail_enabler=account_trail_enabler, adaptive_reentry=adaptive_reentry, adaptive_tolerance=adaptive_tolerance,
                      enable_delayed_entry=enable_delayed_entry, enable_double_entry=enable_double_entry)

    win.main()