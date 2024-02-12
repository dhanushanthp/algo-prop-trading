import modules.config as config
import time
import MetaTrader5 as mt5
import modules.mng_pos as mp
import modules.slack_msg as slack_msg
import modules.util as util
from objects.Prices import Prices
from typing import Tuple
import objects.Currencies as curr
from objects.Shield import Shield
from objects.Account import Account
from objects.Indicators import Indicators


mt5.initialize()

class RiskManager:
    def __init__(self, profit_split=1, stop_ratio=1, target_ratio=3) -> None:
        self.account = Account()
        ACCOUNT_SIZE = self.account.get_liquid_balance()
        self.account_size  = ACCOUNT_SIZE
        self.account_risk_percentage = config.account_risk_percentage * profit_split
        self.risk_of_an_account = round(ACCOUNT_SIZE/100*self.account_risk_percentage)
        self.position_risk_percentage = config.risk_of_a_position
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
        self.account_trail_loss = max(trail_loss, self.account_trail_loss)

        # Check if the daily maximum risk has been reached by comparing equity with account trail loss
        if equity < self.account_trail_loss:
            # Return True if daily maximum risk has been reached
            return True
        
        # Return False if daily maximum risk has not been reached
        return False

    def adjust_positions_trailing_stops(self, target_multiplier:float, trading_timeframe:int):
        existing_positions = mt5.positions_get()
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
    
    def get_stop_range(self, symbol, timeframe, buffer_ratio=config.buffer_ratio, multiplier=1) -> Shield:
        selected_time = util.match_timeframe(timeframe)
        
        previous_candle = mt5.copy_rates_from_pos(symbol, selected_time, 1, 1)[0]
        
        current_candle = mt5.copy_rates_from_pos(symbol, selected_time, 0, 1)[0]
        current_candle_body = abs(current_candle["close"] - current_candle["open"])

        spread = self.prices.get_spread(symbol)

        is_strong_candle = None

        # Current candle should atleaat 3 times more than the spread (Avoid ranging behaviour)
        if (current_candle_body > spread) :
            is_strong_candle = True

        # Extracting high and low values from the previous candle
        higher_stop = previous_candle["high"]
        lower_stop = previous_candle["low"]

        # Checking if the high value of the current candle is greater than the previous high
        if current_candle["high"] > higher_stop:
            # Updating the previous_high if the condition is met
            higher_stop = current_candle["high"]

        # Checking if the low value of the current candle is less than the previous low
        if current_candle["low"] < lower_stop:
            # Updating the previous_low if the condition is met
            lower_stop = current_candle["low"]
        
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
        
        lots = round(lots, 2)

        return points_in_stop, lots


if __name__ == "__main__":
    obj = RiskManager(profit_split=0.5, stop_ratio=1, target_ratio=3)
    test_symbol = "EURUSD"

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