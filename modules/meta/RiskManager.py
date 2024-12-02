from datetime import datetime, timedelta, time
import modules.config as config
import MetaTrader5 as mt5
import pytz
from modules.common.slack_msg import Slack
import modules.meta.util as util
from modules.meta.Prices import Prices
from typing import Tuple, List
import modules.meta.Currencies as curr
from modules.common.Shield import Shield
from modules.meta.Account import Account
from modules.meta.Indicators import Indicators
from modules.meta.wrapper import Wrapper
from modules.common.Directions import Directions
from modules.common import files_util
from modules.common.logme import log_it

mt5.initialize()

class RiskManager:
    def __init__(self, stop_ratio=1, target_ratio=5, account_risk:float=1.0, position_risk:float=0.1, enable_dynamic_direction:bool=False, **kwargs) -> None:
        """
        A class for managing trading risk at both the account and position levels, ensuring 
        proper risk exposure and adherence to defined risk strategies.

        Attributes:
            stop_ratio (float): The stop-loss ratio for calculating stop-loss levels.
            target_ratio (float): The target profit ratio for calculating take-profit levels.
            account_risk_percentage (float): The percentage of the account balance allocated for total risk.
            position_risk_percentage (float): The percentage of the account balance allocated per position.
            enable_dynamic_direction (bool): Change the trade direction based on previous day win/loss
            risk_of_an_account (int): The maximum allowable loss at the account level.
            risk_of_a_position (int): The maximum allowable loss per position.
            max_account_risk (int): The maximum allowable risk based on the account size.
            partial_profit (int): The amount of profit to lock in for partial position closures.
            account_trail_loss (int): The account size threshold for trailing stop-loss adjustments.
            account_size (float): The liquid balance of the account adjusted for closed PnL.
            account_name (str): The name of the trading account.
            strategy (str): The current trading strategy, determined dynamically or via input.
            stop_expected_move (float): Rather using ATR we can use the Potential % of move based on the symbol current price. Because the ATR could be vary based on the specific day of move

        Methods:
            get_max_loss() -> int:
                Returns the current maximum allowable loss for the account.

            reduce_risk_exposure() -> bool:
                Checks if risk exposure should be reduced based on trading activity and time of day.

                Note:
                    At least one trade should be executed before 5 AM server time. 
                    Returns True if no trades were executed by that time, False otherwise.
        """
        self.account = Account()
        self.wrapper = Wrapper()
        self.prices = Prices()
        self.indicators = Indicators(wrapper=self.wrapper, prices=self.prices)
        self.alert = Slack()
        self.account_size = self.account.get_liquid_balance() - self.wrapper.get_closed_pnl()
        # self.position_risk_percentage, self.strategy = files_util.get_most_risk_percentage(file_name=util.get_server_ip(), strategy=kwargs["strategy"]) if dynamic_postional_risk else (position_risk, kwargs["strategy"])
        self.strategy = kwargs["strategy"]
        self.position_risk_percentage = position_risk
        # If it's a dynamic risk then change the todays direction based on previous direction.
        if enable_dynamic_direction:
            # self.strategy = files_util.get_strategy()
            self.strategy = self.indicators.get_dominant_direction()
        
        self.stop_expected_move:float = kwargs["stop_expected_move"]
        self.account_risk_percentage = account_risk
        self.risk_of_an_account = round(self.account_size/100*self.account_risk_percentage)
        self.risk_of_a_position = round(self.account_size/100*self.position_risk_percentage)
        self.max_account_risk = round(self.account_size/100)
        self.partial_profit = round(self.account_size/1000)
        self.stop_ratio = stop_ratio
        self.target_ratio = target_ratio
        

        # Initial Trail loss w.r.t to account size
        self.account_trail_loss = self.account_size - self.risk_of_an_account
        self.account_name = self.account.get_account_name()
    
    def get_max_loss(self):
        return self.account_trail_loss
    
    def reduce_risk_exposure(self) -> bool:
        """
        Atleast 1 trade would have taken on or before 5 AM Server Time
        """
        # check the current hour
        _, hour, min = util.get_current_day_hour_min()
        if hour >= 5 and min >= 45:
            # Check existing positions
            todays_closed_trades = self.wrapper.get_todays_trades()
            if todays_closed_trades.empty:
                return True

            return False
        
        return False
    
    
    def close_positions_by_time(self, timeframe:int, wait_factor:int):
        """
        Identify and list active trading positions that have exceeded their allowable time limit.
        
        This function retrieves all active trading positions and determines which ones should be closed 
        based on the specified timeframe and wait factor. Positions that have been active for longer than 
        the calculated maximum allowable time will be included in the returned list.

        Args:
            timeframe (int): The base timeframe in minutes for which a position is expected to be held.
            wait_factor (int): A multiplier applied to the base timeframe to determine the maximum allowable time.

        Returns:
            list: A list of positions that should be closed based on the time criteria.
        """
        
        active_positions = self.wrapper.get_all_active_positions(raw=True)
        current_time = util.get_current_time() + timedelta(hours=config.server_timezone)
        list_to_close = []
        
        for obj in active_positions:
            trade_time =  util.get_traded_time(epoch=obj.time)
            max_limit_time = trade_time + timedelta(minutes=timeframe*wait_factor)
            if current_time > max_limit_time:
                list_to_close.append(obj)
        
        return list_to_close
    
    def calculate_trades_based_pnl(self):
        """
        Calculates the total profit and loss (PnL) for today's trades.
        
        The function first defines a nested function to calculate directional PnL based on the trade entry price,
        current price, and trade direction. It then retrieves today's trades and filters them to include only those
        where 'entry' is 0 (indicating a new trade). For each trade, it updates the current price, calculates the 
        price change, calculates the PnL for the position, and adjusts for commission to determine the net PnL.
        Finally, it sums the net PnL for all trades to return the total PnL for the day.

        Returns:
            float: Total PnL for today's trades.
        """
        def directional_pnl(entry, current, direction):
            if direction == 0:
                return current - entry
            elif direction == 1:
                return entry - current
            

        todays_trades = self.wrapper.get_todays_trades()
        todays_trades = todays_trades[["symbol", "entry", "type", "price", "commission", "volume"]].copy()
        todays_trades = todays_trades[todays_trades["entry"] == 0]
        todays_trades["current_price"] = todays_trades["symbol"].apply(lambda x: self.prices.get_exchange_price(symbol=x))
        todays_trades["change"] =  todays_trades.apply(lambda x: directional_pnl(entry=x["price"], current=x["current_price"], direction=x["type"]) , axis=1)
        todays_trades["pnl"] = todays_trades.apply(lambda x: self.get_pnl_of_position(symbol=x["symbol"], lots=x["volume"], points_in_stop=x["change"]), axis=1)
        todays_trades["net_pnl"] = todays_trades["pnl"] + todays_trades["commission"]
        total_pnl = round(todays_trades["net_pnl"].sum(), 2)
        return total_pnl
    
    def close_positions_by_solid_candle(self, timeframe:int, wait_factor:int=1, close_check_candle:int=1, double_candle_check=False, candle_solid_ratio=0.6):
        """
        Evaluates and identifies active trading positions to close based on the presence of a solid candle in the given timeframe.

        This method fetches all active positions and checks each position to determine if it should be closed. A position
        is considered for closing if the time since it was opened exceeds the specified `timeframe` multiplied by `wait_factor`.
        For each such position, the method checks if the candle at the `close_check_candle` index is solid (based on a
        provided ratio). If the position is a long position (type 0) and the candle's closing price is higher than its opening
        price, or if the position is a short position (type 1) and the candle's closing price is lower than its opening price,
        the position is added to the list of positions to be closed.

        Args:
            timeframe (int): The timeframe in minutes used to evaluate the maximum holding period of a position.
            wait_factor (int, optional): A multiplier applied to the timeframe to calculate the maximum limit time for holding a position. Default is 1.
            close_check_candle (int, optional): The index of the candle to check for solidity to determine if a position should be closed. Default is 1.

        Returns:
            list: A list of positions that meet the criteria for closing based on the candle analysis.
        """
        active_positions = self.wrapper.get_all_active_positions(raw=True)
        current_time = util.get_current_time() + timedelta(hours=config.server_timezone)
        list_to_close = []
        
        for obj in active_positions:
            trade_time =  util.get_traded_time(epoch=obj.time)
            max_limit_time = trade_time + timedelta(minutes=timeframe*wait_factor)
            if current_time > max_limit_time:
                prev_cdl = self.indicators.solid_candle_direction(symbol=obj.symbol, timeframe=timeframe, index=close_check_candle, ratio=candle_solid_ratio)
                
                if double_candle_check:
                    second_prev_cdl = self.indicators.solid_candle_direction(symbol=obj.symbol, timeframe=timeframe, index=close_check_candle+1, ratio=candle_solid_ratio)
                    third_prev_cdl = self.indicators.solid_candle_direction(symbol=obj.symbol, timeframe=timeframe, index=close_check_candle+2, ratio=candle_solid_ratio)

                    if (prev_cdl and second_prev_cdl) or (prev_cdl and third_prev_cdl):
                        if obj.type == 0:
                            if (prev_cdl==Directions.LONG and second_prev_cdl==Directions.LONG) or (prev_cdl==Directions.LONG and third_prev_cdl==Directions.LONG):
                                list_to_close.append(obj)
                        elif obj.type == 1:
                            if (prev_cdl==Directions.SHORT and second_prev_cdl==Directions.SHORT) or (prev_cdl==Directions.SHORT and third_prev_cdl==Directions.SHORT):
                                list_to_close.append(obj)
                else:
                    if prev_cdl:
                        if obj.type == 0:
                            if prev_cdl==Directions.LONG:
                                list_to_close.append(obj)
                        elif obj.type == 1:
                            if prev_cdl==Directions.SHORT:
                                list_to_close.append(obj)
        
        return list_to_close


    def get_target_ratio(self, symbol:str, atr_timeframe:int=15, by_type="default") -> float:
        """
        Calculate the target ratio based on the Average True Range (ATR) and the range of the previous day's high and low prices.

        Args:
            symbol (str): The trading symbol for which the target ratio is calculated.
            atr_timeframe (int, optional): The timeframe for calculating the ATR. Defaults to 15.

        Returns:
            float: The target ratio calculated as the ratio of the previous day's range to the ATR. Returns 1 if ATR is not available
        """
        if by_type == "default":
            return self.target_ratio
        elif by_type == "atr_day_vs_selected":
            return round(self.indicators.get_atr(symbol=symbol, timeframe=1440)/self.indicators.get_atr(symbol=symbol, timeframe=atr_timeframe))
        if by_type == "by_atr_spread":
            get_atr = self.indicators.get_atr(symbol=symbol, timeframe=atr_timeframe)
            spread = self.prices.get_spread(symbol=symbol)
            ratio = get_atr/spread
            return round(ratio)
        else:
            yesterday_range = self.wrapper.get_candle_i(symbol=symbol, timeframe=1440, i=1)
            yesterday_range = abs(yesterday_range["high"] - yesterday_range["low"])
            atr = self.indicators.get_atr(symbol=symbol, timeframe=atr_timeframe)
            if atr:
                target_factor = round(yesterday_range/atr)
                return target_factor

        return 10
    
    def find_last_trade_time_gap(self, symbol:str, timeframe:int, from_exit_time:bool=True) -> int:
        """
        Finds the time gap in minutes between the current time and the last trade time for a given symbol.
        
        This function retrieves today's trades for the given symbol and calculates the time difference between the current time
        and the last trade's exit or entry time (based on the `from_exit_time` flag). The result is returned in minutes.
        
        If there are no trades found for the symbol, a fallback value, which is three times the specified `timeframe`, is returned.

        Args:
            symbol (str): The symbol (e.g., stock ticker) for which the last trade time gap is calculated.
            timeframe (int): The default timeframe in minutes used for calculating the fallback time gap.
            from_exit_time (bool, optional): If True (default), calculates the gap from the last trade's exit time; 
                                            if False, calculates it from the last trade's entry time.

        Returns:
            int: The time gap in minutes between the current time and the last trade's time for the symbol.
                If no trades are found, returns `timeframe * 3` as a fallback.
        """
        todays_trades = self.wrapper.get_todays_trades()

        if not todays_trades.empty: 
            if from_exit_time:
                all_symbol_exist_times = todays_trades[(todays_trades["symbol"] == symbol) & (todays_trades["entry"] == 1)]["time"]
            else:
                all_symbol_exist_times = todays_trades[(todays_trades["symbol"] == symbol) & (todays_trades["entry"] == 0)]["time"]

            if not all_symbol_exist_times.empty:
                last_traded_time = util.get_traded_time(epoch=max(all_symbol_exist_times))
                current_time = util.get_current_time() + timedelta(hours=config.server_timezone)
                time_gap = (current_time-last_traded_time).total_seconds()/60
                return round(time_gap)
        
        # Return the highest numbe
        return timeframe * 3


    def check_signal_validity(self, symbol:str, timeframe:int, trade_direction:Directions, strategy:str, multiple_positions:str="by_active_single_direction", max_trades_per_day:int=2) -> Tuple[bool, bool]:
        is_opening_trade = False

        if strategy==Directions.REVERSE.name:
            trade_direction = Directions.LONG if trade_direction == Directions.SHORT else Directions.SHORT
        
        trade_time_gap = self.find_last_trade_time_gap(symbol=symbol, timeframe=timeframe, from_exit_time=True)
        
        if multiple_positions == "by_active_both_direction":
            is_opening_trade = True
            # Get all active position
            active_positions = self.wrapper.get_all_active_positions()

            # If there is no active position and the trade time gap exceeds the specified timeframe, 
            # we skip taking a new position to prevent reacting to sudden price movements (which could 
            # trigger a stop-loss and immediately open a new position based on the same signal).
            if active_positions.empty or (symbol not in list(active_positions["symbol"])):
                if trade_time_gap > timeframe:
                    return True, is_opening_trade
            else:
                match trade_direction:
                    case Directions.LONG:
                        active_symbol = active_positions[(active_positions["symbol"] == symbol) & (active_positions["type"] == 0)]
                        if active_symbol.empty and (trade_time_gap > timeframe):
                            return True, is_opening_trade

                    case Directions.SHORT:
                        active_symbol = active_positions[(active_positions["symbol"] == symbol) & (active_positions["type"] == 1)]
                        if active_symbol.empty and (trade_time_gap > timeframe):
                            return True, is_opening_trade
        elif multiple_positions == "by_active_single_direction":
            # Which means one trade at a time, So we just need to check the active trades
            is_opening_trade = True
            # Get all active position
            active_positions = self.wrapper.get_all_active_positions()

            # If there is no active position and the trade time gap exceeds the specified timeframe, 
            # we skip taking a new position to prevent reacting to sudden price movements (which could 
            # trigger a stop-loss and immediately open a new position based on the same signal).
            if active_positions.empty or (symbol not in list(active_positions["symbol"])):
                if trade_time_gap > timeframe:
                    return True, is_opening_trade
        elif multiple_positions == "by_active_single_direction_with_limit":
            # Which means one trade at a time, So we just need to check the active trades
            is_opening_trade = True
            # Get all active position
            active_positions = self.wrapper.get_all_active_positions()

            # If there is no active position and the trade time gap exceeds the specified timeframe, 
            # we skip taking a new position to prevent reacting to sudden price movements (which could 
            # trigger a stop-loss and immediately open a new position based on the same signal).
            if active_positions.empty or (symbol not in list(active_positions["symbol"])):
                if trade_time_gap > timeframe:
                    todays_trades = self.wrapper.get_todays_trades()
                    if not todays_trades:
                        traded_symbol = todays_trades[(todays_trades["symbol"] == symbol) & (todays_trades["entry"] == 0)]
                        # Limit the number of trades by day by symbol regardless of it's direction
                        if len(todays_trades) < max_trades_per_day:
                            return True, is_opening_trade
                        
                    return True, is_opening_trade

        return False, is_opening_trade
    
    def has_daily_maximum_risk_reached(self):
        """
        Check if the daily maximum risk has been reached based on the account's equity and trailing loss.

        The method evaluates whether the current equity of the account has dropped below a threshold that represents 
        the daily maximum risk. This threshold is dynamically adjusted based on the highest equity level achieved 
        during the day (account's trail loss).

        Returns:
        bool: 
            True if the current equity has fallen below the trailing loss level, indicating the daily maximum risk 
            has been reached.
            False if the equity is still above the trailing loss level, indicating the daily maximum risk has not been reached.
        """

        # Retrieve account details including equity
        equity = self.account.get_equity()

        # Calculate trail loss, where equity will increase based on positive returns
        trail_loss = equity - self.risk_of_an_account

        # Update account trail loss with the maximum value between current trail loss and previous maximum
        self.account_trail_loss = max(trail_loss, self.account_trail_loss)

        # Check if the daily maximum risk has been reached by comparing equity with account trail loss
        if equity < self.account_trail_loss:
            # Return True if daily maximum risk has been reached
            return True
        
        # Return False if daily maximum risk has not been reached
        return False
    
    def get_positions_at_risk(self) -> list:
        """
        Get list of positions that are not breakeven of in the profit
        """
        existing_positions = mt5.positions_get()
        symbol_list = []
        for position in existing_positions:
            symbol = position.symbol
            stop_price = position.sl
            entry_price = position.price_open

            match position.type:
                case 0:
                    if stop_price < entry_price:
                        symbol_list.append(position)

                case 1:
                    if stop_price > entry_price:
                        symbol_list.append(position)
        
        return symbol_list
    
    @staticmethod
    def generate_15min_band(selected_min):
        traded_min_band = 0
        if 0 <= selected_min < 15:
            traded_min_band = 15
        elif 15 <= selected_min < 30:
            traded_min_band = 30
        elif 30 <= selected_min < 45:
            traded_min_band = 45
        else:
            traded_min_band = 60

        return traded_min_band


    def close_on_candle_close(self, timeframe) -> list:
        list_of_positions = []
        existing_positions = mt5.positions_get()
        factor = 2
        for position in existing_positions:
            traded_time = util.get_traded_time(epoch=position.time)
            curret_time = util.get_current_time()
            
            match timeframe:
                case 1:
                    if curret_time > traded_time + timedelta(minutes=1):
                        list_of_positions.append(position)
                case 5:
                    if curret_time > traded_time + timedelta(minutes=5):
                        list_of_positions.append(position)
                case 15:
                    traded_min_band = self.generate_15min_band(traded_time.minute)
                    current_min_band = self.generate_15min_band(curret_time.minute)
                    
                    if current_min_band + curret_time.hour >= traded_min_band + traded_time.hour + (15 * factor):
                        list_of_positions.append(position)
                case 60:
                    # If trade enter at 10, then it will exit at start of 12 or end of 11
                    traded_hour = traded_time.hour
                    # If the trade took place last minute of the hour, then consider the exit for hour + 1
                    # if traded_time.minute > 50:
                    #     traded_hour += 1

                    if curret_time.hour > traded_hour:
                        list_of_positions.append(position)
                case 240:
                    # If trade enter at 10, then it will exit as 
                    # TODO This is tricky, Not strightfoward as 1 hour candle
                    if curret_time.hour > traded_time.hour:
                        list_of_positions.append(position)
        return list_of_positions

    
    def emergency_exit(self, is_market_open:bool, timeframe:int) -> list:
        """
        Retrieves a list of symbols eligible for emergency exit based on ranging hourly candles.

        Args:
            self: The instance of the class.
            is_market_open (bool): Indicates whether the market is open.
            timeframe (int): The timeframe for considering ranging candles.

        Returns:
            list: A list of symbols eligible for emergency exit.
        """
        symbol_list = []
        if is_market_open:
            existing_positions = mt5.positions_get()
            for position in existing_positions:
                symbol = position.symbol
                pnl = position.profit
                # Emergency Exist Plan
                is_ranging = self.indicators.get_three_candle_exit(symbol=symbol, wick_body_ratio=2, timeframe=timeframe)
                
                # Also the profit is more than 1R
                if is_ranging and (pnl > self.risk_of_a_position):
                    symbol_list.append(position)
                    self.alert.send_msg(f"Emergency Exist: {symbol}")
        
        return symbol_list
    

    def disable_stop(self):
        existing_positions = mt5.positions_get()
        for position in existing_positions:
            target_price = position.tp
            modify_request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": position.symbol,
                        "volume": position.volume,
                        "type": position.type,
                        "position": position.ticket,
                        "tp": target_price,
                        "comment": position.comment,
                        "magic": position.magic,
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_FOK,
                        "ENUM_ORDER_STATE": mt5.ORDER_FILLING_RETURN,
                    }
                    
            result = mt5.order_send(modify_request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                if result.comment != "No changes":
                    print("Re-enabling STOP for " + position.symbol + " failed!!...Error: "+str(result.comment))


    def trailing_stop_and_target(self, stop_multiplier:float, target_multiplier:float, trading_timeframe:int, num_cdl_for_stop:int, stop_selection:str):
        """
        Function to manage trailing stops and targets for existing positions based on specified multipliers and trading timeframe.

        Args:
            self: The object instance.
            stop_multiplier (float): The multiplier used to calculate the trailing stop.
            target_multiplier (float): The multiplier used to calculate the trailing target.
            trading_timeframe (int): The timeframe for trading operations.

        Notes:
            This function adjusts the trailing stop and target prices for existing positions. 
            It calculates the stop and target prices based on the specified multipliers and trading timeframe.
            If the current hour is 0, it disables the stop to prevent unexpected actions during periods of high spread. 
            It also adjusts the stop to breakeven when the position's profit exceeds the risk of the position. Additionally, 
            it increases the spread range to prevent sudden stopouts and reactivates the stop if it was previously disabled.
            Finally, it modifies the stop and target prices for the positions and prints relevant information or error messages as necessary.

        """
        _, hour, _ = util.get_current_day_hour_min()
        
        if hour == 0:
            # Disable the stop when the spread is huge, Specially when the position is not close from previous day
            self.disable_stop()
        else:
            existing_positions = mt5.positions_get()
            for position in existing_positions:
                symbol = position.symbol
                stop_price = position.sl
                target_price = position.tp
                open_price = position.price_open
                pnl = position.profit

                # Move the stop to breakeven once the price moved to R
                is_stop_updated=False
                # if pnl > self.risk_of_a_position:
                #     match position.type:
                #         case 0:
                #             # Long Position
                #             if stop_price < open_price:
                #                 is_stop_updated = True
                #         case 1:
                #             # Short Position
                #             if stop_price > open_price:
                #                 is_stop_updated = True
                
                # Increase the range of the spread to eliminate the sudden stopouts
                stp_shield_obj = self.get_stop_range(symbol=symbol, timeframe=trading_timeframe, multiplier=stop_multiplier, num_cdl_for_stop=num_cdl_for_stop, stop_selection=stop_selection)
                tgt_shield_obj = self.get_stop_range(symbol=symbol, timeframe=trading_timeframe, multiplier=target_multiplier, num_cdl_for_stop=num_cdl_for_stop, stop_selection=stop_selection)
                
                match position.type:
                    case 0:
                        # Long Position
                        trail_stop = max(stop_price, stp_shield_obj.get_long_stop)
                        trail_target = min(target_price, tgt_shield_obj.get_short_stop)
                        stop_enabler = stp_shield_obj.get_long_stop
                    case 1:
                        # Short Position
                        trail_stop = min(stop_price, stp_shield_obj.get_short_stop)
                        trail_target = max(target_price, tgt_shield_obj.get_long_stop)
                        stop_enabler = stp_shield_obj.get_short_stop
                
                # if (trail_stop != stop_price) or (target_price != trail_target) or is_stop_updated or (stop_price == 0):
                if (trail_stop != stop_price) or is_stop_updated or (stop_price == 0):
                    
                    # If the position don't have the stop, then it will be reactivated
                    if stop_price == 0:
                        trail_stop = stop_enabler

                    # When the price move above 1R then move the stop to breakeven
                    if is_stop_updated:
                        trail_stop = open_price
                        print(f"BREAKEVEN : {symbol} to {open_price}")

                    print(f"STP Updated: {position.symbol}, PRE STP: {round(stop_price, 5)}, CURR STP: {trail_stop}, PRE TGT: {target_price}, CURR TGT: {trail_target}")

                    modify_request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": position.symbol,
                        "volume": position.volume,
                        "type": position.type,
                        "position": position.ticket,
                        "sl": trail_stop,
                        "tp": target_price, # trail_target
                        "comment": position.comment,
                        "magic": position.magic,
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_FOK,
                        "ENUM_ORDER_STATE": mt5.ORDER_FILLING_RETURN,
                    }
                    
                    result = mt5.order_send(modify_request)
                    
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        if result.comment != "No changes":
                            print("Trailing STOP for " + position.symbol + " failed!!...Error: "+str(result.comment))


    def breakeven(self, profit_factor:int):
        """
        Adjusts the stop-loss of existing positions to breakeven once a specified profit threshold is reached.

        Args:
            profit_factor (int): The profit multiple of the initial risk (`R`) at which the stop-loss should be moved to the breakeven point.

        Behavior:
            - Iterates through all existing positions.
            - For each position, checks if the profit (`pnl`) exceeds the specified `profit_factor` multiplied by the initial risk of the position.
            - If the condition is met:
                - For long positions, the stop-loss is moved to the entry price if the current stop-loss is below the entry price.
                - For short positions, the stop-loss is moved to the entry price if the current stop-loss is above the entry price.
            - If the stop-loss is updated, a modification request is sent to MetaTrader 5 to adjust the stop-loss and target prices.

        Side Effects:
            - Prints a message indicating that the stop-loss has been moved to breakeven for the specified symbol.
            - If the modification request fails, an error message is printed with the failure reason.

        Note:
            - The function assumes that `self.risk_of_a_position` is defined elsewhere in the class and represents the initial risk (`R`) for each position.

        Raises:
            None: The function handles errors internally by printing messages if the stop-loss modification fails.

        """
        existing_positions = mt5.positions_get()
        for position in existing_positions:
            symbol = position.symbol
            stop_price = position.sl
            target_price = position.tp
            open_price = position.price_open
            pnl = position.profit

            # Move the stop to breakeven once the price moved to R
            is_stop_updated=False
            if pnl > (profit_factor * self.risk_of_a_position):
                match position.type:
                    case 0:
                        # Long Position
                        if stop_price < open_price:
                            is_stop_updated = True
                    case 1:
                        # Short Position
                        if stop_price > open_price:
                            is_stop_updated = True
            
            if is_stop_updated:
                # When the price move above 1R then move the stop to breakeven
                if is_stop_updated:
                    trail_stop = open_price
                    trail_target = target_price
                    print(f"BREAKEVEN : {symbol} to {open_price}")

                    modify_request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": position.symbol,
                        "volume": position.volume,
                        "type": position.type,
                        "position": position.ticket,
                        "sl": trail_stop,
                        "tp": trail_target,
                        "comment": position.comment,
                        "magic": position.magic,
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_FOK,
                        "ENUM_ORDER_STATE": mt5.ORDER_FILLING_RETURN,
                    }
                    
                    result = mt5.order_send(modify_request)
                    
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        if result.comment != "No changes":
                            print("Trailing STOP for " + position.symbol + " failed!!...Error: "+str(result.comment))
    
    def get_stop_range(self, symbol, timeframe, buffer_ratio=config.buffer_ratio, multiplier=1, num_cdl_for_stop=0, stop_selection:str="CANDLE") -> Shield:
        """
        Calculates the stop loss range for a given trading symbol based on the specified strategy.

        Args:
            symbol (str): The trading symbol (e.g., currency pair, stock ticker) for which the stop range is being calculated.
            timeframe (int): The timeframe in minutes (e.g., 1, 5, 15, 60) to be used for the analysis.
            buffer_ratio (float, optional): A buffer ratio added to the calculated stop range to account for volatility. Defaults to config.buffer_ratio.
            multiplier (float, optional): A multiplier to adjust the calculated stop range. Defaults to 1.
            num_cdl_for_stop (int, optional): The number of candles to consider for calculating the stop range. Only used when stop_selection is "CANDLE". Defaults to 0.
            stop_selection (str, optional): The method to be used for stop calculation. Options include:
                - "CANDLE": Uses recent candles' high/low prices and ATR to determine the stop range.
                - "ATR15M", "ATR1H", "ATR2H", "ATR4H", "ATR1D": Uses ATR of the respective timeframe to determine the stop range.
                Defaults to "CANDLE".

        Returns:
            Shield: An object containing the calculated stop ranges (`long_range` and `short_range`), 
                    the range distance (`range_distance`), and a flag indicating if the current signal 
                    is based on a strong candle (`is_strong_signal`).

        Raises:
            Exception: If an invalid stop_selection is provided.
        
        """
        mid_price = self.prices.get_exchange_price(symbol)

        if stop_selection == "CANDLE":
            selected_time = util.match_timeframe(timeframe)
            
            # Pick last (num_cdl_for_stop + 1) candles (Including current one) to find high and low
            previous_candles = mt5.copy_rates_from_pos(symbol, selected_time, 0, num_cdl_for_stop+1)
            
            current_candle = mt5.copy_rates_from_pos(symbol, selected_time, 0, 1)[0]
            current_candle_body = abs(current_candle["close"] - current_candle["open"])

            spread = self.prices.get_spread(symbol)

            is_strong_candle = None

            # Current candle should atleaat 3 times more than the spread (Avoid ranging behaviour)
            if (current_candle_body > spread) :
                is_strong_candle = True

            # Extracting high and low values from the previous candle
            higher_stop = max([i["high"] for i in previous_candles])
            lower_stop = min([i["low"] for i in previous_candles])
            
            
            # In cooprate ATR along with candle high/low when the candle length is too small/ price ranging
            atr = self.indicators.get_atr(symbol=symbol, timeframe=timeframe)
            distance_from_high = max(atr, abs(higher_stop-mid_price))
            distance_from_low = max(atr, abs(lower_stop-mid_price))

            optimal_distance = max(distance_from_high, distance_from_low) * multiplier
            optimal_distance = optimal_distance + (optimal_distance*buffer_ratio)
        elif stop_selection=="ATR5M":
            # Stop based on last 1 hour of movement
            optimal_distance = self.indicators.get_atr(symbol=symbol, timeframe=5, start_candle=1, n_atr=12)
        elif stop_selection=="ATR15M":
            optimal_distance = self.indicators.get_atr(symbol=symbol, timeframe=15, start_candle=1, n_atr=14)
            mid_price = self.prices.get_exchange_price(symbol)
            lower_stop = self.prices.round(symbol=symbol, price=mid_price - optimal_distance)
            higher_stop = self.prices.round(symbol=symbol, price=mid_price + optimal_distance)
            is_strong_candle = True
        elif stop_selection=="ATR1H":
            optimal_distance = self.indicators.get_atr(symbol=symbol, timeframe=60, start_candle=1, n_atr=14)
        elif stop_selection=="ATR2H":
            optimal_distance = self.indicators.get_atr(symbol=symbol, timeframe=120, start_candle=1, n_atr=14)
        elif stop_selection=="ATR4H":
            optimal_distance = self.indicators.get_atr(symbol=symbol, timeframe=240, start_candle=1, n_atr=14)
        elif stop_selection=="ATR1D":
            optimal_distance = self.indicators.get_atr(symbol=symbol, timeframe=1440, start_candle=1, n_atr=14)
        elif stop_selection=="ATR1D_FACTOR":
            optimal_distance = self.indicators.get_atr(symbol=symbol, timeframe=1440, start_candle=1, n_atr=14)/14
        elif stop_selection=="FACTOR":
            # Lower the expected move, Higher the risk we will be taking. 0.04% expected move is risker than 0.05% expected move
            optimal_distance = mid_price * self.stop_expected_move/100 # 0.05% Move expected
        else:
            raise Exception("Stop Selection is not given!")
        
        lower_stop = self.prices.round(symbol=symbol, price=mid_price - optimal_distance)
        higher_stop = self.prices.round(symbol=symbol, price=mid_price + optimal_distance)
        is_strong_candle = True
        
        return Shield(symbol=symbol, long_range=lower_stop, short_range=higher_stop, range_distance=optimal_distance, is_strong_signal=is_strong_candle)

    
    def get_pnl_of_position(self, symbol, lots, points_in_stop):
         # This change made of fundedEngineer account!

        if symbol in curr.currencies:
            lots = lots*10**5
    
        if symbol in ['ASX_raw', 'FTSE_raw', 'FTSE100']:
            lots = lots*10
        
        if symbol in ['SP_raw', "SPX500"]:
            lots = lots*40
        
        if symbol in ['HK50_raw']:
            lots = lots*100
        
        if symbol in ['NIKKEI_raw']:
            lots = lots*1000

        if symbol in ["XAUUSD"]:
            # Some reason the amount is comes as 4 times. So divide by 4
            lots = lots*4/100
        
        dollor_value = self.prices.get_dollar_value(symbol)
        position_dollor_value = lots * dollor_value * points_in_stop
        return position_dollor_value

    def get_lot_size(self, symbol, entry_price, stop_price) -> Tuple[float, float]:
        """
        Calculates the lot size for a given trading position based on the entry price,
        stop price, and symbol. The method adjusts the lot size based on specific symbols
        and their respective scaling factors.

        Args:
            symbol (str): The trading symbol (e.g., currency pair, stock index).
            entry_price (float): The entry price for the trade.
            stop_price (float): The stop price for the trade.

        Returns:
            Tuple[float, float]: A tuple containing:
                - The number of points in the stop (float).
                - The calculated lot size (float).

        Notes:
            - The method uses the dollar value of the symbol to compute the lot size.
            - Adjustments are made for various symbols, including currency pairs, stock indices,
            and commodities, based on predefined scaling factors.
            - The resulting lot size is rounded to two decimal places, and a minimum lot size
            of 0.01 is enforced.
        """
        dollor_value = self.prices.get_dollar_value(symbol)
        points_in_stop = abs(entry_price-stop_price)
        lots = self.risk_of_a_position/(points_in_stop * dollor_value)
        
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

        if symbol in ["XAUUSD"]:
            # Some reason the amount is comes as 4 times. So divide by 4
            lots = lots*100/4
        
        # if lots <= 0.01:
        #     lots = 0.01

        lots = round(lots, 2)

        return points_in_stop, lots
    

    def neutralizer(self, timeframe:int, enable_ratio:float=0.5):
        """
        Evaluates existing trading positions and identifies positions to neutralize based on the given risk threshold.

        This function checks the current price of each open position against a dynamically calculated middle price.
        If the current price moves beyond the threshold determined by `enable_ratio`, it suggests taking the opposite
        position to neutralize the risk.

        Parameters:
        - enable_ratio (float): The ratio used to determine the threshold for neutralizing positions. Defaults to 0.5.

        Returns:
        - neutral_positions (list): A list of tuples containing symbols and directions for positions to be neutralized.

        The function performs the following steps:
        1. Retrieves existing positions using `mt5.positions_get()`.
        2. Iterates over each position to determine its symbol, stop loss price, open price, and current price.
        3. For long positions:
            - Calculates the middle price where risk is assessed.
            - Checks if the current price is below the middle price.
            - If valid, suggests a short position to neutralize risk.
        4. For short positions:
            - Calculates the middle price where risk is assessed.
            - Checks if the current price is above the middle price.
            - If valid, suggests a long position to neutralize risk.
        5. Returns a list of suggested neutral positions based on the evaluations.

        Example:
            neutral_positions = self.neutralizer(enable_ratio=0.6)
        """
        neutral_positions = []
        existing_positions = mt5.positions_get()
        for position in existing_positions:
            symbol = position.symbol
            stop_price = position.sl
            open_price = position.price_open
            current_price = self.prices.get_entry_price(symbol=symbol)

            match position.type:
                case 0:
                    # Long Position
                    middle_price = open_price - ((open_price - stop_price) * enable_ratio)
                    if current_price < middle_price:
                        if self.check_signal_validity(symbol=symbol, timeframe=timeframe, trade_direction=Directions.SHORT, strategy=None):
                            neutral_positions.append((symbol, Directions.SHORT))
                case 1:
                    # Short Position
                    middle_price = open_price + ((stop_price - open_price) * enable_ratio)
                    if current_price > middle_price:
                        if self.check_signal_validity(symbol=symbol, timeframe=timeframe, trade_direction=Directions.LONG, strategy=None):
                            neutral_positions.append((symbol, Directions.LONG))

        return neutral_positions

    def check_trade_wait_time(self, symbol):
        """
        Magic variable is important from the history
        If you already have made some money. Then don't entry this for another time peroid based on last entered timeframe
        """
        tm_zone = pytz.timezone(f'Etc/GMT-{config.server_timezone}')
        start_time = datetime.combine(datetime.now(tm_zone).date(), time()).replace(tzinfo=tm_zone) - timedelta(hours=2)
        end_time = datetime.now(tm_zone) + timedelta(hours=4)
        today_date = datetime.now(tm_zone).date()

        exit_traded_position = [i for i in mt5.history_deals_get(start_time,  end_time) if i.symbol== symbol and i.entry==1]

        if len(exit_traded_position) > 0:
            last_traded_time = exit_traded_position[-1].time
            last_traded_date = (datetime.fromtimestamp(last_traded_time, tz=tm_zone) - timedelta(hours=2)).date()

            # This is considered as new day
            if last_traded_date != today_date:
                return True

            # Below logic, sameday with traded time gap
            position_id = exit_traded_position[-1].position_id
            entry_traded_object = [i for i in mt5.history_deals_get(start_time,  end_time) if i.position_id == position_id and i.entry == 0]
            if len(entry_traded_object) > 0:
                # Wait until the last traded timeframe is complete
                previous_timeframe = int(entry_traded_object[-1].magic)  # in minutes, This was my input to the process
                # timeframe = max(timeframe, current_trade_timeframe) # Pick the max timeframe based on previous and current suggested trade timeframe

                current_time = (datetime.now(tm_zone) + timedelta(hours=2))
                current_time_epoch = current_time.timestamp()

                # Minutes from last traded time.
                time_difference = (current_time_epoch - last_traded_time)/60

                if time_difference < previous_timeframe:
                    print(f"{symbol.ljust(12)}: Last/Current TF: {previous_timeframe} > Wait Time {round(previous_timeframe - time_difference)} Minutes!")
                    return False

        return True

if __name__ == "__main__":
    obj = RiskManager(stop_ratio=1, target_ratio=3, strategy="dynamic")
    import sys
    test_symbol = sys.argv[1]
    decision = sys.argv[2]

    match decision:
        case "stop_range":
            # Test: Stop Ranges
            timeframe=int(sys.argv[3])
            stp_range = obj.get_stop_range(symbol=test_symbol, timeframe=timeframe, num_cdl_for_stop=2, stop_selection="CANDLE")
            print(stp_range)
            stp_range = obj.get_stop_range(symbol=test_symbol, timeframe=timeframe, stop_selection="ATR1D")
            print(stp_range)
        
        case "target_range":
            # Test: Target Ranges 
            tgt_range = obj.get_stop_range(symbol=test_symbol, timeframe=60, multiplier=3)
            print(tgt_range)
        
        case "lot_size":
            # Test: Lot Size
            # python modules\meta\RiskManager.py CADJPY lot_size
            entry_price = obj.prices.get_entry_price(symbol=test_symbol)
            stp_range = obj.get_stop_range(symbol=test_symbol, timeframe=15,  stop_selection="ATR15M")
            point_in_stop, lots = obj.get_lot_size(symbol=test_symbol, entry_price=entry_price, stop_price=stp_range.get_long_stop)
            print(f"Entry:{entry_price + point_in_stop} \nSTP SRT:{entry_price + point_in_stop + point_in_stop} \nSTP LNG: {entry_price} \nLOT: {lots}")
            print()
            stp_range = obj.get_stop_range(symbol=test_symbol, timeframe=15,  stop_selection="FACTOR")
            point_in_stop, lots = obj.get_lot_size(symbol=test_symbol, entry_price=entry_price, stop_price=stp_range.get_long_stop)
            print(f"Entry:{entry_price + point_in_stop} \nSTP SRT:{entry_price + point_in_stop + point_in_stop} \nSTP LNG: {entry_price} \nLOT: {lots}")
        
        case "wait_time":
            check_time = obj.check_trade_wait_time(symbol=test_symbol)
            print(check_time)

        case "trail":
            obj.trailing_stop_and_target(stop_multiplier=1, target_multiplier=3, trading_timeframe=60)

        case "disable_stop":
            obj.disable_stop()
        
        case "emer_exit":
            print(obj.emergency_exit(timeframe=60))

        case "pos_at_risk":
            print(obj.get_positions_at_risk())
        
        case "close_on":
            print(obj.close_on_candle_close(timeframe=5))

        case "validity":
            # python modules\meta\RiskManager.py EURUSD validity
            print(obj.check_signal_validity(symbol=test_symbol, timeframe=15, trade_direction=Directions.LONG,  multiple_positions="by_active_one_direction", strategy=Directions.BREAK.name))

        case "neutral":
            print(obj.neutralizer())

        case "close_by_time":
            for symbol in obj.close_positions_by_time(60, 3):
                print(symbol.symbol)
        
        case "target_ratio":
            # python modules\meta\RiskManager.py CADJPY target_ratio
            for symbol in curr.get_symbols(symbol_selection="NON-PRIMARY"):
                print(symbol, obj.get_target_ratio(symbol=symbol, atr_timeframe=15, by_type="by_atr_spread"))
        
        case "time_gap":
            # python modules\meta\RiskManager.py CADJPY time_gap
            for symbol in curr.get_symbols():
                print(symbol, obj.find_last_trade_time_gap(symbol=symbol, timeframe=60))

        case "get_pnl":
            # python modules\meta\RiskManager.py CADJPY get_pnl
            for i in range(100):
                print(obj.calculate_trades_based_pnl())
                import time
                time.sleep(1)