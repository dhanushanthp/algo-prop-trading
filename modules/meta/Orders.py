import MetaTrader5 as mt5
mt5.initialize()
from modules.meta.RiskManager import RiskManager
from modules.common.Directions import Directions
import modules.meta.util as util
from modules.meta.Prices import Prices
from modules.meta.wrapper import Wrapper
from modules.common.logme import log_it
import time

class Orders:
    def __init__(self, prices:Prices, risk_manager:RiskManager, wrapper:Wrapper) -> None:
        self.prices = prices
        self.risk_manager=risk_manager
        self.wrapper = wrapper

    def close_single_position_by_symbol(self, symbol:str):
        """
        Closes a single position based on the symbol.

        Args:
            symbol (str): The symbol of the position to be closed.

        Returns:
            None
        """
        positions = mt5.positions_get()
        for obj in positions: 
            if obj.symbol == symbol:
                self.close_single_position(obj=obj)

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
        """
        Closes all currently open positions.

        Description:
        ------------
        This method retrieves all currently open positions using MetaTrader 5 (MT5) and attempts to close each one.
        It calls the `close_single_position` method for every open position, passing the position object to be closed.

        Usage:
        ------
        - This method closes all open positions, regardless of the symbol.
        - It is useful when you need to exit all trades immediately, such as in cases of market volatility, or to stop all trading activity.

        Example:
        --------
        self.close_all_positions()

        Note:
        -----
        This method assumes that the `close_single_position` method is implemented and 
        properly handles the logic for closing individual positions.

        """
        positions = mt5.positions_get()
        for obj in positions: 
            self.close_single_position(obj=obj)
    
    def close_all_selected_position(self, symbol_list:list):
        """
        Closes all open positions for the given list of symbols.

        Parameters:
        ----------
        symbol_list : list
            A list of symbol names (strings) for which open positions should be closed.

        Description:
        ------------
        This method retrieves all currently open positions using MetaTrader 5 (MT5) and iterates through them.
        If a position's symbol matches any of the symbols in the provided `symbol_list`, it calls 
        the `close_single_position` method to close that particular position.

        Usage:
        ------
        - Pass a list of symbols (e.g., ['EURUSD', 'GBPUSD']) that you want to close positions for.
        - The method will close only those positions with symbols present in the `symbol_list`.

        Example:
        --------
        self.close_all_selected_position(['EURUSD', 'GBPUSD'])

        Note:
        -----
        This method assumes that the `close_single_position` method is implemented and 
        properly handles the logic of closing individual positions.

        """
        positions = mt5.positions_get()
        for obj in positions:
            if obj.symbol in symbol_list:
                self.close_single_position(obj=obj)


    def cancel_single_pending_order(self, active_order):
        """
        Cancels a single pending order in MetaTrader 5 (MT5).

        This method sends a request to cancel the specified pending order using MT5's trading API.
        If the cancellation request fails, the method will print an error message and wait for 3 seconds
        before potentially retrying or reloading existing trades.

        Args:
            active_order (Order): An instance of the Order class representing the pending order to be canceled.
                The `ticket` attribute of this instance is used to identify the order to be canceled.

        Returns:
            None

        Raises:
            None

        Notes:
            - The method uses `mt5.TRADE_ACTION_REMOVE` to specify that the action is to remove the order.
            - The `order_send` function is called to execute the cancellation request.
            - The method checks the return code to determine if the cancellation was successful. If not, an error message is printed.
            - There is a 3-second delay if the cancellation fails, which may help in scenarios where the trading platform needs time to process the request.

        Example:
            order = Order(ticket=123456)
            cancel_single_pending_order(order)
        """
        request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": active_order.ticket,
            }

        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"{active_order.symbol.ljust(12)}: Failed to cancel order {active_order.ticket}, reason: {result.comment}")
            # If the cancle fails, Give some time to reload existing trades.
            time.sleep(3)


    def cancel_all_pending_orders(self):
        """
        Cancels all pending orders on the MetaTrader 5 platform.

        This method retrieves all active orders from the MetaTrader 5 platform 
        and attempts to cancel each one. It cancels pending orders regardless 
        of whether the account is in trial or real mode.

        Returns:
            None

        Raises:
            None

        Notes:
            - If the cancellation of an order fails, a message is printed 
            indicating the order ticket number and the reason for the failure.
            - The function does not raise exceptions or return a status, so the 
            user needs to monitor the printed output for any issues.
        """
        active_orders = mt5.orders_get()

        # Cancell all pending orders regadless of trial or real
        for active_order in active_orders:
            self.cancel_single_pending_order(active_order=active_order)
    

    def long_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int, num_cdl_for_stop:int=2, multiplier:float=1, market_entry:bool=False, stop_selection:str="CANDLE", entry_with_st_tgt:bool=True) -> bool:
        """
        Executes a long entry based on given parameters.

        Args:
            self: The instance of the class.
            symbol (str): The symbol to execute the entry for.
            reference (str): The reference identifier for the entry.
            break_level (float): The break level for the entry.
            trading_timeframe (int): The timeframe for trading.
            num_cdl_for_stop (int, optional): Number of candles for determining stop. Defaults to 2.
            multiplier (float, optional): Multiplier for stop range calculation. Defaults to 1.
            market_entry (bo0=ol, optional): Entry the trade with market price. Defaults to False.
            stop_selection (str, optional): Stop selection strategy, e.g Candle based, ATR based etc. Defaults to CANDLE

        Returns:
            bool: True if the entry is successfully executed, False otherwise.
        """
        if market_entry:
            # Immidiate entry on ASK price
            _, entry_price = self.prices.get_bid_ask(symbol=symbol)
        else:
            entry_price = self.prices.get_entry_price(symbol=symbol)

        # If the latest base is not loaded, then it trades based on wrong signal
        is_chart_upto_date = self.wrapper.is_chart_upto_date(symbol=symbol)
        if not is_chart_upto_date:
            log_it(reference).info(f"{symbol}: HOUR NOT MATCH")
        
        if entry_price and is_chart_upto_date:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe, num_cdl_for_stop=num_cdl_for_stop, multiplier=multiplier, stop_selection=stop_selection)
            if shield_object.get_signal_strength:
                if entry_price > shield_object.get_long_stop:
                    try:
                        print(f"{symbol.ljust(12)}: {Directions.LONG}, {stop_selection}")
                        points_in_stop, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_long_stop)

                        comment = f"{reference}-{break_level}" if break_level != -1 else reference
                        
                        order_request = {
                            "action": mt5.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt5.ORDER_TYPE_BUY_LIMIT,
                            "price": entry_price,
                            # "comment": comment, Some time it failed lengthy string
                            "magic": trading_timeframe,
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": mt5.ORDER_FILLING_RETURN,
                        }

                        if entry_with_st_tgt:
                            order_request["sl"] = self.prices.round(symbol, entry_price - self.risk_manager.stop_ratio * points_in_stop)
                            order_request["tp"] = self.prices.round(symbol, entry_price + self.risk_manager.get_target_ratio(symbol=symbol, atr_timeframe=trading_timeframe) * points_in_stop)
                        
                        request_log = mt5.order_send(order_request)
                        return util.error_logging(request_log, order_request)
                    except Exception as e:
                        print(f"{symbol.ljust(12)}: {e}")
                        return False
            else:
                print(f"{symbol.ljust(12)}: {Directions.LONG} -  Waiting for signal strength...")
                return False

    @DeprecationWarning
    def long_waited_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int) -> bool:
        entry_price = self.prices.get_entry_price(symbol=symbol)

        if entry_price:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe, buffer_ratio=0)
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

    @DeprecationWarning
    def long_waited_prev_candle_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int) -> bool:
        entry_price = self.prices.get_entry_price(symbol=symbol)
        prev_candle_low = self.wrapper.get_previous_candle(symbol=symbol, timeframe=trading_timeframe)['low']

        if entry_price:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe, buffer_ratio=0, num_cdl_for_stop=1)
            if entry_price > shield_object.get_long_stop:
                try:
                    print(f"{symbol.ljust(12)}: {Directions.LONG}")        
                    points_in_stop, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_long_stop)
                    
                    order_request = {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": symbol,
                        "volume": lots,
                        "type": mt5.ORDER_TYPE_BUY_LIMIT,
                        "price": prev_candle_low,
                        "sl": self.prices.round(symbol, prev_candle_low - self.risk_manager.stop_ratio * points_in_stop),
                        "tp": self.prices.round(symbol, prev_candle_low + self.risk_manager.target_ratio * points_in_stop),
                        "comment": f"{reference}-{break_level}",
                        "magic": trading_timeframe,
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_RETURN,
                    }
                    
                    request_log = mt5.order_send(order_request)
                    return util.error_logging(request_log, order_request)
                except Exception as e:
                    print(f"{symbol.ljust(12)}: {e}")
    

    def short_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int, num_cdl_for_stop:int=2, multiplier:float=1, market_entry:bool=False, stop_selection:str="CANDLE", entry_with_st_tgt:bool= True) -> bool:
        """
        Executes a short entry based on given parameters.

        Args:
            self: The instance of the class.
            symbol (str): The symbol to execute the entry for.
            reference (str): The reference identifier for the entry.
            break_level (float): The break level for the entry.
            trading_timeframe (int): The timeframe for trading.
            num_cdl_for_stop (int, optional): Number of candles for determining stop. Defaults to 2.
            multiplier (float, optional): Multiplier the for stop range calculation. Defaults to 1.
            market_entry (bo0=ol, optional): Entry the trade with market price. Defaults to False
            stop_selection (str, optional): Stop selection strategy, e.g Candle based, ATR based etc. Defaults to CANDLE

        Returns:
            bool: True if the entry is successfully executed, False otherwise.
        """
        if market_entry:
            # Immidiate entry on BID price
            entry_price, _ = self.prices.get_bid_ask(symbol=symbol)
        else:
            entry_price = self.prices.get_entry_price(symbol=symbol)

        # If the latest base is not loaded, then it trades based on wrong signal
        is_chart_upto_date = self.wrapper.is_chart_upto_date(symbol=symbol)
        if not is_chart_upto_date:
            log_it(reference).info(f"{symbol}: HOUR NOT MATCH")
        
        if entry_price and is_chart_upto_date:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe, num_cdl_for_stop=num_cdl_for_stop, multiplier=multiplier, stop_selection=stop_selection)
            if shield_object.get_signal_strength:
                if entry_price < shield_object.get_short_stop:
                    try:
                        print(f"{symbol.ljust(12)}: {Directions.SHORT}, {stop_selection}")
                        points_in_stop, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_short_stop)

                        comment = f"{reference}-{break_level}" if break_level != -1 else reference

                        order_request = {
                            "action": mt5.TRADE_ACTION_PENDING,
                            "symbol": symbol,
                            "volume": lots,
                            "type": mt5.ORDER_TYPE_SELL_LIMIT,
                            "price": entry_price,
                            # "comment": comment, Some time it failed lengthy string
                            "magic":trading_timeframe,
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": mt5.ORDER_FILLING_RETURN,
                        }

                        if entry_with_st_tgt:
                            order_request["sl"] = self.prices.round(symbol, entry_price - self.risk_manager.stop_ratio * points_in_stop)
                            order_request["tp"] = self.prices.round(symbol, entry_price + self.risk_manager.get_target_ratio(symbol=symbol, atr_timeframe=trading_timeframe) * points_in_stop)
                        
                        request_log = mt5.order_send(order_request)
                        return util.error_logging(request_log, order_request)
                    except Exception as e:
                        print(f"{symbol.ljust(12)}: {e}")
                        return False
            else:
                print(f"{symbol.ljust(12)}: {Directions.SHORT} - Waiting for signal strength...")
                return False

    @DeprecationWarning
    def short_waited_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int) -> bool:
        entry_price = self.prices.get_entry_price(symbol)
        
        if entry_price:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe)
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

    @DeprecationWarning
    def short_waited_prev_candle_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int) -> bool:
        entry_price = self.prices.get_entry_price(symbol)
        prev_candle_high = self.wrapper.get_previous_candle(symbol=symbol, timeframe=trading_timeframe)['high']
        
        if entry_price:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe, num_cdl_for_stop=1)
            if entry_price < shield_object.get_short_stop:
                try:
                    print(f"{symbol.ljust(12)}: {Directions.SHORT}")      
                    points_in_stop, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_short_stop)

                    order_request = {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": symbol,
                        "volume": lots,
                        "type": mt5.ORDER_TYPE_SELL_LIMIT,
                        "price": prev_candle_high,
                        "sl": self.prices.round(symbol, prev_candle_high + self.risk_manager.stop_ratio * points_in_stop),
                        "tp": self.prices.round(symbol, prev_candle_high - self.risk_manager.target_ratio * points_in_stop),
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
    order_obj = Orders(prices=prices_obj, risk_manager=risk_obj, wrapper=Wrapper())

    # Test: Cancel all pending orders
    # order_obj.cancel_all_pending_orders()

    # Test: Close all open positions
    # order_obj.close_all_positions()
    
    # Test: Enter Long Position
    if direction == "long":
        order_obj.long_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60, reference="test")

    if direction == "long_waited":
        order_obj.long_waited_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60, reference="test")

    if direction == "long_prev":
        order_obj.long_waited_prev_candle_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60, reference="test")

    # Test: Enter Short Position
    if direction == "short":
        order_obj.short_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60, reference="test")
    
    if direction == "short_waited":
        order_obj.short_waited_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60, reference="test")
    
    if direction == "short_prev":
        order_obj.short_waited_prev_candle_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60, reference="test")



