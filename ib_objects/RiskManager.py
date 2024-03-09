from datetime import datetime, timedelta, time
import modules.config as config
import pytz
import objects.slack_msg as slack_msg
from ib_objects.Prices import Prices
from typing import Tuple
import ib_objects.Currencies as curr
from objects.Shield import Shield
from ib_objects.Account import Account
from ib_objects.Indicators import Indicators
from clients.ibrk_wrapper import IBRK

class RiskManager:
    def __init__(self, ibrk:IBRK, stop_ratio=1, target_ratio=3, account_risk:float=1, position_risk:float=0.1) -> None:
        self.ibrk:IBRK = ibrk
        self.account = Account(self.ibrk)
        ACCOUNT_SIZE = self.account.get_liquid_balance()
        self.account_size  = ACCOUNT_SIZE
        self.account_risk_percentage = account_risk
        self.position_risk_percentage = position_risk
        self.risk_of_an_account = round(ACCOUNT_SIZE/100*self.account_risk_percentage)
        self.risk_of_a_position = round(ACCOUNT_SIZE/100*self.position_risk_percentage)
        self.alert = slack_msg.Slack()
        self.max_account_risk = round(ACCOUNT_SIZE/100)
        self.partial_profit = round(ACCOUNT_SIZE/1000)
        self.prices = Prices(self.ibrk)
        self.stop_ratio = stop_ratio
        self.target_ratio = target_ratio
        self.indicators = Indicators(self.ibrk)
        

        # Initial Trail loss w.r.t to account size
        self.account_trail_loss = ACCOUNT_SIZE - self.risk_of_an_account
    
    def get_max_loss(self):
        return self.account_trail_loss
    
    def has_daily_maximum_risk_reached(self):
        """
        Check if the daily maximum risk has been reached based on the account's equity and trail loss.

        Returns:
        bool: True if the daily maximum risk has been reached, False otherwise.
        """

        # Retrieve account details including equity
        equity = self.account.get_equity()

        # Calculate trail loss, where equity will increase based on positive returns
        trail_loss = equity - self.risk_of_an_account

        # Update account trail loss with the maximum value between current trail loss and previous maximum
        # self.account_trail_loss = max(trail_loss, self.account_trail_loss)

        # Check if the daily maximum risk has been reached by comparing equity with account trail loss
        if equity < self.account_trail_loss:
            # Return True if daily maximum risk has been reached
            return True
        
        # Return False if daily maximum risk has not been reached
        return False

    def adjust_positions_trailing_stops(self, target_multiplier:float, trading_timeframe:int):
        existing_positions = self.ibrk.get_existing_positions()
        for position in existing_positions:
            symbol = position.symbol
            stop_price = position.sl
            target_price = position.tp
            
            # Increase the range of the spread to eliminate the sudden stopouts
            stp_shield_obj = self.get_stop_range(symbol=symbol, timeframe=trading_timeframe)
            tgt_shield_obj = self.get_stop_range(symbol=symbol, timeframe=trading_timeframe, multiplier=target_multiplier)
            
            if position.type == 0:
                # Long Position
                trail_stop = max(stop_price, stp_shield_obj.get_long_stop)
                trail_target = min(target_price, tgt_shield_obj.get_short_stop)
            else:
                # Short Position
                trail_stop = min(stop_price, stp_shield_obj.get_short_stop)
                trail_target = max(target_price, tgt_shield_obj.get_long_stop)

            if (trail_stop != stop_price) or (target_price != trail_target):
                print(f"STP Updated: {position.symbol}, PRE STP: {round(stop_price, 5)}, CURR STP: {trail_stop}, PRE TGT: {target_price}, CURR TGT: {trail_target}")

                # modify_request = {
                #     "action": mt5.TRADE_ACTION_SLTP,
                #     "symbol": position.symbol,
                #     "volume": position.volume,
                #     "type": position.type,
                #     "position": position.ticket,
                #     "sl": trail_stop,
                #     "tp": trail_target,
                #     "comment": position.comment,
                #     "magic": position.magic,
                #     "type_time": mt5.ORDER_TIME_GTC,
                #     "type_filling": mt5.ORDER_FILLING_FOK,
                #     "ENUM_ORDER_STATE": mt5.ORDER_FILLING_RETURN,
                # }
                
                # result = mt5.order_send(modify_request)
                
                # if result.retcode != mt5.TRADE_RETCODE_DONE:
                #     if result.comment != "No changes":
                #         print("Trailing STOP for " + position.symbol + " failed!!...Error: "+str(result.comment))
    
    def get_stop_range(self, symbol, timeframe, buffer_ratio=config.buffer_ratio, multiplier=1) -> Shield:
        
        # Pick last 3 candles (Including current one) to find high and low
        previous_candles = self.ibrk.get_candles_by_index(symbol=symbol, timeframe=timeframe, 
                                                          prev_candle_count=3)
        
        current_candle = self.ibrk.get_current_candle(symbol=symbol, timeframe=timeframe)
        current_candle_body = abs(current_candle["close"] - current_candle["open"])

        spread = self.prices.get_spread(symbol)

        is_strong_candle = None

        # Current candle should atleaat 3 times more than the spread (Avoid ranging behaviour)
        if (current_candle_body > spread) :
            is_strong_candle = True

        # Extracting high and low values from the previous candle
        higher_stop = previous_candles["high"].max()
        lower_stop = previous_candles["low"].min()
        
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
        """
        1 lot is 100,000 Base currency (Below EUR is a base currency)
        e.g If 0.5lot EURUSD = EUR 50,000
        """
        
        points_in_stop = round(points_in_stop, 5)
        # lots = lots/10**5
        
        lots = int(lots)
        lots = round(lots, 5)

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

        # exit_traded_position = [i for i in mt5.history_deals_get(start_time,  end_time) if i.symbol== symbol and i.entry==1]
        exit_traded_position = []

        if len(exit_traded_position) > 0:
            last_traded_time = exit_traded_position[-1].time
            last_traded_date = (datetime.fromtimestamp(last_traded_time, tz=tm_zone) - timedelta(hours=2)).date()

            # This is considered as new day
            if last_traded_date != today_date:
                return True

            # Below logic, sameday with traded time gap
            position_id = exit_traded_position[-1].position_id
            # exit_traded_position = [i for i in mt5.history_deals_get(start_time,  end_time) if i.position_id == position_id and i.entry == 0]
            entry_traded_object = []
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
    ibrk = IBRK()
    obj = RiskManager(ibrk=ibrk, stop_ratio=1, target_ratio=3)
    import sys
    test_symbol = sys.argv[1]

    # Test: Stop Ranges
    stp_range = obj.get_stop_range(symbol=test_symbol, timeframe=60)
    print(stp_range)

    entry_price = obj.prices.get_entry_price(test_symbol)

    # # Test: Target Ranges 
    lots = obj.get_lot_size(symbol=test_symbol, entry_price=entry_price, stop_price=stp_range.long_range)
    print(lots)

    # # Test: Lot Size
    # entry_price = obj.prices.get_entry_price(symbol=test_symbol)
    # size = obj.get_lot_size(symbol=test_symbol, entry_price=entry_price, stop_price=stp_range.get_long_stop)
    # print(size)

    # check_time = obj.check_trade_wait_time(symbol=test_symbol)
    # print(check_time)