import MetaTrader5 as mt5
mt5.initialize()
from modules.meta.RiskManager import RiskManager
from modules.common.Directions import Directions
import modules.meta.util as util
from modules.meta.Prices import Prices

class Orders:
    def __init__(self, prices:Prices, risk_manager:RiskManager) -> None:
        self.prices = prices
        self.risk_manager=risk_manager

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


    def cancel_single_pending_order(self, active_order):
        
        request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": active_order.ticket,
            }

        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to cancel order {active_order.ticket}, reason: {result.comment}")


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
    

    def long_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int) -> bool:
        entry_price = self.prices.get_entry_price(symbol=symbol)

        if entry_price:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe)
            #  and self.risk_manager.check_trade_wait_time(symbol=symbol)
            if shield_object.get_signal_strength:
                if entry_price > shield_object.get_long_stop:
                    try:
                        print(f"{symbol.ljust(12)}: {Directions.LONG}")        
                        points_in_stop, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_long_stop)
                        
                        order_request = {
                            "action": mt5.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt5.ORDER_TYPE_BUY_LIMIT,
                            "price": entry_price,
                            "sl": self.prices.round(symbol, entry_price - self.risk_manager.stop_ratio * points_in_stop),
                            "tp": self.prices.round(symbol, entry_price + self.risk_manager.target_ratio * points_in_stop),
                            "comment": f"{reference}-{break_level}",
                            "magic": trading_timeframe,
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": mt5.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt5.order_send(order_request)
                        return util.error_logging(request_log, order_request)
                    except Exception as e:
                        print(f"{symbol.ljust(12)}: {e}")
                        return False
            else:
                print(f"{symbol.ljust(12)}: Waiting for signal strength...")
                return False

    def long_waited_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int) -> bool:
        entry_price = self.prices.get_entry_price(symbol=symbol)

        if entry_price:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe, buffer_ratio=0)
            #  and self.risk_manager.check_trade_wait_time(symbol=symbol)
            if entry_price > shield_object.get_long_stop:
                try:
                    print(f"{symbol.ljust(12)}: {Directions.LONG}")        
                    points_in_stop, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_long_stop)
                    
                    order_request = {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": symbol,
                        "volume": lots,
                        "type": mt5.ORDER_TYPE_BUY_LIMIT,
                        "price": shield_object.get_long_stop,
                        "sl": self.prices.round(symbol, shield_object.get_long_stop - self.risk_manager.stop_ratio * points_in_stop),
                        "tp": self.prices.round(symbol, shield_object.get_long_stop + self.risk_manager.target_ratio * points_in_stop),
                        "comment": f"{reference}-{break_level}",
                        "magic": trading_timeframe,
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_RETURN,
                    }
                    
                    request_log = mt5.order_send(order_request)
                    return util.error_logging(request_log, order_request)
                except Exception as e:
                    print(f"{symbol.ljust(12)}: {e}")
    

    def short_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int) -> bool:
        entry_price = self.prices.get_entry_price(symbol)
        
        if entry_price:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe)
            #  and self.risk_manager.check_trade_wait_time(symbol=symbol)
            if shield_object.get_signal_strength:
                if entry_price < shield_object.get_short_stop:
                    try:
                        print(f"{symbol.ljust(12)}: {Directions.SHORT}")      
                        points_in_stop, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_short_stop)

                        order_request = {
                            "action": mt5.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt5.ORDER_TYPE_SELL_LIMIT,
                            "price": entry_price,
                            "sl": self.prices.round(symbol, entry_price + self.risk_manager.stop_ratio * points_in_stop),
                            "tp": self.prices.round(symbol, entry_price - self.risk_manager.target_ratio * points_in_stop),
                            "comment": f"{reference}-{break_level}",
                            "magic":trading_timeframe,
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": mt5.ORDER_FILLING_RETURN,
                        }
                        
                        request_log = mt5.order_send(order_request)
                        return util.error_logging(request_log, order_request)
                    except Exception as e:
                        print(f"{symbol.ljust(12)}: {e}")
                        return False
            else:
                print(f"{symbol.ljust(12)}: Waiting for signal strength...")
                return False

    def short_waited_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int) -> bool:
        entry_price = self.prices.get_entry_price(symbol)
        
        if entry_price:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe)
            #  and self.risk_manager.check_trade_wait_time(symbol=symbol)
            if entry_price < shield_object.get_short_stop:
                try:
                    print(f"{symbol.ljust(12)}: {Directions.SHORT}")      
                    points_in_stop, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_short_stop)

                    order_request = {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": symbol,
                        "volume": lots,
                        "type": mt5.ORDER_TYPE_SELL_LIMIT,
                        "price": shield_object.get_short_stop,
                        "sl": self.prices.round(symbol, shield_object.get_short_stop + self.risk_manager.stop_ratio * points_in_stop),
                        "tp": self.prices.round(symbol, shield_object.get_short_stop - self.risk_manager.target_ratio * points_in_stop),
                        "comment": f"{reference}-{break_level}",
                        "magic":trading_timeframe,
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_RETURN,
                    }
                    
                    request_log = mt5.order_send(order_request)
                    return util.error_logging(request_log, order_request)
                except Exception as e:
                    print(f"{symbol.ljust(12)}: {e}")

if __name__ == "__main__":
    import sys
    symbol = sys.argv[1]
    direction = sys.argv[2]
    risk_obj = RiskManager()
    prices_obj = Prices()
    order_obj = Orders(prices=prices_obj, risk_manager=risk_obj)

    # Test: Cancel all pending orders
    # order_obj.cancel_all_pending_orders()

    # Test: Close all open positions
    # order_obj.close_all_positions()
    
    # Test: Enter Long Position
    if direction == "long":
        order_obj.long_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60, reference="test")

    if direction == "long_waited":
        order_obj.long_waited_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60, reference="test")

    # Test: Enter Short Position
    if direction == "short":
        order_obj.short_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60, reference="test")
    
    if direction == "short_waited":
        order_obj.short_waited_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60, reference="test")



