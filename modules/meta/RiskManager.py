from datetime import datetime, timedelta, time
import modules.config as config
import MetaTrader5 as mt5
import pytz
import modules.common.slack_msg as slack_msg
import modules.meta.util as util
from modules.meta.Prices import Prices
from typing import Tuple, List
import modules.meta.Currencies as curr
from modules.common.Shield import Shield
from modules.meta.Account import Account
from modules.meta.Indicators import Indicators

mt5.initialize()

class RiskManager:
    def __init__(self, stop_ratio=1, target_ratio=5, account_risk:float=1, position_risk:float=0.5) -> None:
        self.account = Account()
        ACCOUNT_SIZE = self.account.get_liquid_balance()
        self.account_size  = ACCOUNT_SIZE
        self.account_risk_percentage = account_risk
        self.position_risk_percentage = position_risk
        self.risk_of_an_account = round(ACCOUNT_SIZE/100*self.account_risk_percentage)
        self.risk_of_a_position = round(ACCOUNT_SIZE/100*self.position_risk_percentage)
        self.alert = slack_msg.Slack()
        self.max_account_risk = round(ACCOUNT_SIZE/100)
        self.partial_profit = round(ACCOUNT_SIZE/1000)
        self.prices = Prices()
        self.stop_ratio = stop_ratio
        self.target_ratio = target_ratio
        self.indicators = Indicators()

        # Initial Trail loss w.r.t to account size
        self.account_trail_loss = ACCOUNT_SIZE - self.risk_of_an_account
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
            todays_closed_trades = self.indicators.wrapper.get_todays_trades()
            if todays_closed_trades.empty:
                return True

            return False
        
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
    
    def get_risk_positions(self) -> list:
        """
        Get list of positions that are not breakeven of in the profit
        """
        existing_positions = mt5.positions_get()
        symbol_list = []
        for position in existing_positions:
            symbol = position.symbol
            stop_price = position.sl
            entry_price = position.price_open

            if position.type == 0:
                if stop_price < entry_price:
                    symbol_list.append(position)
            
            if position.type == 1:
                if stop_price > entry_price:
                    symbol_list.append(position)
        
        return symbol_list

    
    def emergency_exit(self, is_market_open:bool, timeframe:int) -> list:
        """
        Get list of symbol which are meant to exist based on ranging hourly candles
        """
        symbol_list = []
        if is_market_open:
            existing_positions = mt5.positions_get()
            for position in existing_positions:
                symbol = position.symbol
                pnl = position.profit
                # Emergency Exist Plan
                is_ranging = self.indicators.get_three_candle_exit(symbol=symbol, ratio=2, timeframe=timeframe)
                
                # Also the profit is more than 1R
                if is_ranging and (pnl > self.risk_of_a_position):
                    symbol_list.append(position)
                    self.alert.send_msg(f"Emergency Exist: {symbol}")
        
        return symbol_list


    def adjust_positions_trailing_stops(self, is_market_open:bool, stop_multiplier:float, target_multiplier:float, trading_timeframe:int):
        # Only adjust while market is open
        if is_market_open:
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
                    # Long Position
                    if position.type == 0:
                        if stop_price < open_price:
                            is_stop_updated = True
                    # Short Position
                    else:
                        if stop_price > open_price:
                            is_stop_updated = True
                
                # Increase the range of the spread to eliminate the sudden stopouts
                stp_shield_obj = self.get_stop_range(symbol=symbol, timeframe=trading_timeframe, multiplier=stop_multiplier)
                tgt_shield_obj = self.get_stop_range(symbol=symbol, timeframe=trading_timeframe, multiplier=target_multiplier)
                
                if position.type == 0:
                    # Long Position
                    trail_stop = max(stop_price, stp_shield_obj.get_long_stop)
                    trail_target = min(target_price, tgt_shield_obj.get_short_stop)
                else:
                    # Short Position
                    trail_stop = min(stop_price, stp_shield_obj.get_short_stop)
                    trail_target = max(target_price, tgt_shield_obj.get_long_stop)
                
                if (trail_stop != stop_price) or (target_price != trail_target) or is_stop_updated:
                    
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
    
    def get_stop_range(self, symbol, timeframe, buffer_ratio=config.buffer_ratio, multiplier=1, num_cdl_for_stop=2) -> Shield:
        """
        num_cdl_for_stop : number of previous candles considered from current candles for stop calculation e.g, 1 previous candle, 2 is second previous candle
        however it includes current candle for calculation, in case if the current candle is longer than the previous candles
        """
        selected_time = util.match_timeframe(timeframe)
        
        # Pick last 3 candles (Including current one) to find high and low
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

    # Test: Stop Ranges
    stp_range = obj.get_stop_range(symbol=test_symbol, timeframe=60)
    print(stp_range)

    # Test: Target Ranges 
    tgt_range = obj.get_stop_range(symbol=test_symbol, timeframe=60, multiplier=3)
    print(tgt_range)

    # Test: Lot Size
    entry_price = obj.prices.get_entry_price(symbol=test_symbol)
    size = obj.get_lot_size(symbol=test_symbol, entry_price=entry_price, stop_price=stp_range.get_long_stop)
    print(size)

    check_time = obj.check_trade_wait_time(symbol=test_symbol)
    print(check_time)

    # print(obj.reduce_risk_exposure())

    # obj.adjust_positions_trailing_stops(target_multiplier=8, trading_timeframe=60)
    
    # print(obj.emergency_exit(timeframe=60))

    print(obj.get_risk_positions())