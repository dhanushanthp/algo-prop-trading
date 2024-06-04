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

mt5.initialize()

class RiskManager:
    def __init__(self, stop_ratio=1, target_ratio=5, account_risk:float=1, position_risk:float=0.5, dynamic:bool=False) -> None:
        self.account = Account()
        self.wrapper = Wrapper()
        self.prices = Prices()
        self.indicators = Indicators(wrapper=self.wrapper, prices=self.prices)
        self.alert = Slack()
        self.account_size = self.account.get_liquid_balance() - self.wrapper.get_closed_pnl()
        self.position_risk_percentage = files_util.get_most_risk_percentage() if dynamic else position_risk
        self.account_risk_percentage = self.position_risk_percentage * 10 if dynamic else account_risk
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
    
    def check_signal_validity(self, symbol:str, trade_direction:Directions, strategy:str):

        if strategy==Directions.REVERSE.name:
            trade_direction = Directions.LONG if trade_direction == Directions.SHORT else Directions.SHORT
        
        # Check does this already has trades on same direction, Load Passed Data
        todays_trades = self.wrapper.get_todays_trades()

        # If the symbol is not already traded, then take the trade
        if todays_trades.empty or (symbol not in list(todays_trades["symbol"])):
            return True
        else:
            match trade_direction:
                case Directions.LONG:
                    traded_symbol = todays_trades[(todays_trades["symbol"] == symbol) & (todays_trades["type"] == 0) & (todays_trades["entry"] == 0)]
                    if traded_symbol.empty:
                        # Shoud not have any previous trades on Long Direction
                        return True
                case Directions.SHORT:
                    traded_symbol = todays_trades[(todays_trades["symbol"] == symbol) & (todays_trades["type"] == 1) & (todays_trades["entry"] == 0)]
                    if traded_symbol.empty:
                        # Shoud not have any previous trades on Short Direction
                        return True

        return False
    
    def has_daily_maximum_risk_reached(self):
        """
        Check if the daily maximum risk has been reached based on the account's equity and trail loss.

        Returns:
        bool: True if the daily maximum risk has been reached, False otherwise.
        """

        # Retrieve account details including equity
        equity = self.account.get_equity()

        # Calculate trail loss, where equity will increase based on positive returns
        # trail_loss = equity - self.risk_of_an_account

        # Update account trail loss with the maximum value between current trail loss and previous maximum
        # self.account_trail_loss = max(trail_loss, self.account_trail_loss)

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


    def trailing_stop_and_target(self, stop_multiplier:float, target_multiplier:float, trading_timeframe:int, num_cdl_for_stop:int):
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
                if pnl > self.risk_of_a_position:
                    match position.type:
                        case 0:
                            # Long Position
                            if stop_price < open_price:
                                is_stop_updated = True
                        case 1:
                            # Short Position
                            if stop_price > open_price:
                                is_stop_updated = True
                
                # Increase the range of the spread to eliminate the sudden stopouts
                stp_shield_obj = self.get_stop_range(symbol=symbol, timeframe=trading_timeframe, multiplier=stop_multiplier, num_cdl_for_stop=num_cdl_for_stop)
                tgt_shield_obj = self.get_stop_range(symbol=symbol, timeframe=trading_timeframe, multiplier=target_multiplier, num_cdl_for_stop=num_cdl_for_stop)
                
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
                
                if (trail_stop != stop_price) or (target_price != trail_target) or is_stop_updated or (stop_price == 0):
                    
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


    def breakeven(self, profit_factor:int=2):        
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
    
    def get_stop_range(self, symbol, timeframe, buffer_ratio=config.buffer_ratio, multiplier=1, num_cdl_for_stop=0) -> Shield:
        """
        Calculates the stop range based on given parameters.

        If the time frame is greater than 4 hours, the stop is set to the high or low of the previous and current bar based on the trade direction.

        Args:
            self: The instance of the class.
            symbol (str): The symbol for which the stop range is calculated.
            timeframe: The timeframe for calculation.
            buffer_ratio (float, optional): The buffer ratio for adjusting the stop range. Defaults to config.buffer_ratio.
            multiplier (int, optional): Multiplier for the stop range calculation. Defaults to 1.
            num_cdl_for_stop (int, optional): Number of previous candles considered for stop calculation. Defaults to 0.

        Returns:
            Shield: An object representing the stop range with attributes:
                - symbol (str): The symbol.
                - long_range (float): The lower stop range for a long trade.
                - short_range (float): The upper stop range for a short trade.
                - range_distance (float): The distance of the stop range from the mid price.
                - is_strong_signal (bool): Indicates whether the current candle is considered strong.
        """
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
        
        mid_price = self.prices.get_exchange_price(symbol)
        
        # In cooprate ATR along with candle high/low when the candle length is too small/ price ranging
        atr = self.indicators.get_atr(symbol=symbol, timeframe=timeframe)
        distance_from_high = max(atr, abs(higher_stop-mid_price))
        distance_from_low = max(atr, abs(lower_stop-mid_price))

        optimal_distance = max(distance_from_high, distance_from_low) * multiplier
        optimal_distance = optimal_distance + (optimal_distance*buffer_ratio)
        
        lower_stop = self.prices.round(symbol=symbol, price=mid_price - optimal_distance)
        higher_stop = self.prices.round(symbol=symbol, price=mid_price + optimal_distance)
        
        return Shield(symbol=symbol, long_range=lower_stop, short_range=higher_stop, range_distance=optimal_distance, is_strong_signal=is_strong_candle)

    def get_lot_size(self, symbol, entry_price, stop_price) -> Tuple[float, float]:
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
        
        lots = round(lots, 2)

        return points_in_stop, lots
    

    def neutralizer(self, enable_ratio:float=0.5):
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
                        if self.check_signal_validity(symbol=symbol, trade_direction=Directions.SHORT, strategy=None):
                            neutral_positions.append((symbol, Directions.SHORT))
                case 1:
                    # Short Position
                    middle_price = open_price + ((stop_price - open_price) * enable_ratio)
                    if current_price > middle_price:
                        if self.check_signal_validity(symbol=symbol, trade_direction=Directions.LONG, strategy=None):
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
    obj = RiskManager(stop_ratio=1, target_ratio=3)
    import sys
    test_symbol = sys.argv[1]
    decision = sys.argv[2]

    match decision:
        case "stop_range":
            # Test: Stop Ranges
            stp_range = obj.get_stop_range(symbol=test_symbol, timeframe=60)
            print(stp_range)
        
        case "target_range":
            # Test: Target Ranges 
            tgt_range = obj.get_stop_range(symbol=test_symbol, timeframe=60, multiplier=3)
            print(tgt_range)
        
        case "lot_size":
            # Test: Lot Size
            entry_price = obj.prices.get_entry_price(symbol=test_symbol)
            stp_range = obj.get_stop_range(symbol=test_symbol, timeframe=60)
            size = obj.get_lot_size(symbol=test_symbol, entry_price=entry_price, stop_price=stp_range.get_long_stop)
            print(size)
        
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
            print(obj.check_signal_validity(symbol=test_symbol, trade_direction=Directions.LONG))

        case "neutral":
            print(obj.neutralizer())