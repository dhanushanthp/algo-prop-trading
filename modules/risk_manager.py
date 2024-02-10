import modules.indicators as ind
import modules.config as config
import pytz
import datetime
import time
import MetaTrader5 as mt5
import modules.mng_pos as mp
import modules.slack_msg as slack_msg
import modules.util as util
from collections import Counter
from objects.risk_diffuser import RiskDiffuser

class RiskManager:
    def __init__(self, profit_split=1) -> None:
        ACCOUNT_SIZE,_, _,_ = ind.get_account_details()
        self.account_size  = ACCOUNT_SIZE
        self.account_risk_percentage = config.account_risk_percentage * profit_split
        self.risk_of_an_account = round(ACCOUNT_SIZE/100*self.account_risk_percentage)
        self.position_risk_percentage = config.risk_of_a_position
        self.risk_of_a_position = round(ACCOUNT_SIZE/100*self.position_risk_percentage)
        self.previous_time = None
        self.first_max_profit_check = True
        self.second_max_profit_check = True
        self.alert = slack_msg.Slack()
        self.max_risk_hit_counter = 0
        self.enable_half_trail = self.risk_of_an_account + round(ACCOUNT_SIZE/100*0.25) # Add addtional 0.25 to cover commision
        self.max_account_risk = round(ACCOUNT_SIZE/100)
        self.partial_profit = round(ACCOUNT_SIZE/1000)

        # Initial Trail loss w.r.t to account size
        self.account_trail_loss = ACCOUNT_SIZE - self.risk_of_an_account
        self.account_name = ind.get_account_name()

        # The max profit split is 100% of risking the account
        # assert profit_split <= 1
    
    def get_max_loss(self):
        return self.account_trail_loss
    
    def profit_day_checker(self):
        account_size, equity, _, _ = ind.get_account_details()
        if equity > account_size + self.risk_of_a_position:
            # Creates a new file
            with open('enabler.txt', 'w') as fp:
                pass

            return True

    def get_max_profit(self):
        return self.account_size + self.risk_of_an_account
    
    def diffuser_profits(self):
        existing_positions = mt5.positions_get()
        counter = Counter([i.symbol for i in existing_positions])
        diffuser_positions = {item: count for item, count in counter.items() if count >= 2}
        for symbol in diffuser_positions.keys():
            print(symbol)

    def risk_diffusers(self):
        internal_existing_positions = mt5.positions_get()
        counter = Counter([i.symbol for i in internal_existing_positions])
        orders = {}
        for position in internal_existing_positions:
            pos_symbol = position.symbol
            if counter[pos_symbol] < 2 and position.comment == "R>60" and position.comment != "defuser":
                order_type = position.type
                entry_price = position.price_open
                stop_price = position.sl
                volume = position.volume
                bid, ask = ind.get_bid_ask(pos_symbol)
                if order_type == 0:
                    current_price = bid
                else:
                    current_price = ask

                points_in_stop = abs(current_price - stop_price)
                diffuser_enabler = abs(entry_price - stop_price)/2

                positional_risk = mp.get_position_dollar_value(pos_symbol, order_type, entry_price, current_price, volume) * 2
                print(f"{pos_symbol}:{positional_risk/2}")

                if order_type == 0:
                    decision_point = entry_price - diffuser_enabler
                    print(f"{pos_symbol}: {decision_point}->{current_price}")
                    if current_price < decision_point:
                        orders[pos_symbol] = RiskDiffuser("short", pos_symbol, ask + points_in_stop, positional_risk)
                else:
                    decision_point = entry_price + diffuser_enabler
                    print(f"{pos_symbol}: {decision_point}->{current_price}")
                    if current_price > decision_point:
                        orders[pos_symbol] = RiskDiffuser("long", pos_symbol, bid - points_in_stop, positional_risk)
        
        return orders
    
    def has_daily_maximum_risk_reached(self):
        """
        Check if the daily maximum risk has been reached based on the account's equity and trail loss.

        Returns:
        bool: True if the daily maximum risk has been reached, False otherwise.
        """

        # Retrieve account details including equity
        _, equity, _, _ = ind.get_account_details()

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
            stp_candle_high, stp_candle_low, _, _, _ = ind.get_stop_range(symbol=symbol, timeframe=trading_timeframe)
            stp_candle_low = util.curr_round(position.symbol, stp_candle_low)
            stp_candle_high = util.curr_round(position.symbol, stp_candle_high)
            
            tgt_candle_high, tgt_candle_low, _, _, _ = ind.get_stop_range(symbol=symbol, timeframe=trading_timeframe, multiplier=target_multiplier)
            tgt_candle_low = util.curr_round(position.symbol, tgt_candle_low)
            tgt_candle_high = util.curr_round(position.symbol, tgt_candle_high)
            
            if position.type == 0:
                # Long Position
                trail_stop = max(stop_price, stp_candle_low)
                trail_target = min(target_price, tgt_candle_high)
            else:
                # Short Position
                trail_stop = min(stop_price, stp_candle_high)
                trail_target = max(target_price, tgt_candle_low)

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

    def close_single_position(self, obj):        
        order_type = mt5.ORDER_TYPE_BUY if obj.type == 1 else mt5.ORDER_TYPE_SELL
        exist_price = mt5.symbol_info_tick(obj.symbol).bid if obj.type == 1 else mt5.symbol_info_tick(obj.symbol).ask
        
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": obj.symbol,
            "volume": obj.volume,
            "type": order_type,
            "position": obj.ticket,
            "price": exist_price,
            "deviation": 20,
            "magic": 234000,
            "comment": 'close_trail_version',
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC, # also tried with ORDER_FILLING_RETURN
        }
        
        result = mt5.order_send(close_request) # send order to close a position
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print("Close Order "+obj.symbol+" failed!!...comment Code: "+str(result.comment))
    
    def close_all_positions(self):
        positions = mt5.positions_get()
        for obj in positions: 
            self.close_single_position(obj=obj)

    def cancel_all_pending_orders(self):
        active_orders = mt5.orders_get()

        # Cancell all pending orders regadless of trial or real
        for active_order in active_orders:
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": active_order.ticket,
            }

            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"Failed to cancel order {active_order.ticket}, reason: {result.comment}")
    
    def update_to_half_trail(self):
        _, equity, _,_ = ind.get_account_details()
        # Reduce the trail distance when the price cross first profit target
        print(f"{'Half trail at'.ljust(20)}: ${'{:,}'.format(round(self.account_size + self.enable_half_trail))}", "\n")
        if (equity > self.account_size + self.enable_half_trail) and self.first_max_profit_check:
            self.alert.send_msg(f"{self.account_name}: First target max triggered!")
            self.risk_of_an_account = self.risk_of_a_position
            self.first_max_profit_check = False
            return True


if __name__ == "__main__":
    obj = RiskManager(profit_split=0.5)
    while True:
        print(f"Current Risk: {obj.partial_profit}")
        time.sleep(30)