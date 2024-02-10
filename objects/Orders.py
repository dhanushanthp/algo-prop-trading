import MetaTrader5 as mt5
mt5.initialize()

class Orders:
    def __init__(self) -> None:
        pass

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