from modules.ibrk.RiskManager import RiskManager
from modules.common.Directions import Directions
from modules.ibrk.Prices import Prices
from modules.ibrk.wrapper import IBRK
import ib_insync as ibi

class Orders:
    def __init__(self, prices:Prices, risk_manager:RiskManager, ibrk:IBRK) -> None:
        self.prices = prices
        self.risk_manager=risk_manager
        self.ibrk = ibrk

    # def close_single_position(self, obj):        
    #     order_type = mt5.ORDER_TYPE_BUY if obj.type == 1 else mt5.ORDER_TYPE_SELL
    #     exist_price = mt5.symbol_info_tick(obj.symbol).bid if obj.type == 1 else mt5.symbol_info_tick(obj.symbol).ask
        
    #     close_request = {
    #         "action": mt5.TRADE_ACTION_DEAL,
    #         "symbol": obj.symbol,
    #         "volume": obj.volume,
    #         "type": order_type,
    #         "position": obj.ticket,
    #         "price": exist_price,
    #         "deviation": 20,
    #         "magic": 234000,
    #         "comment": 'close_trail_version',
    #         "type_time": mt5.ORDER_TIME_GTC,
    #         "type_filling": mt5.ORDER_FILLING_IOC, # also tried with ORDER_FILLING_RETURN
    #     }
        
    #     result = mt5.order_send(close_request) # send order to close a position
        
    #     if result.retcode != mt5.TRADE_RETCODE_DONE:
    #         print("Close Order "+obj.symbol+" failed!!...comment Code: "+str(result.comment))
    

    # def close_all_positions(self):
    #     positions = mt5.positions_get()
    #     for obj in positions: 
    #         self.close_single_position(obj=obj)


    # def cancel_all_pending_orders(self):
    #     active_orders = mt5.orders_get()

    #     # Cancell all pending orders regadless of trial or real
    #     for active_order in active_orders:
    #         request = {
    #             "action": mt5.TRADE_ACTION_REMOVE,
    #             "order": active_order.ticket,
    #         }

    #         result = mt5.order_send(request)

    #         if result.retcode != mt5.TRADE_RETCODE_DONE:
    #             print(f"Failed to cancel order {active_order.ticket}, reason: {result.comment}")
    

    def long_entry(self, symbol:str, trading_timeframe:int):
        entry_price = self.prices.get_entry_price(symbol=symbol)

        if entry_price:
            shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe)
            print(shield_object)
            
            if shield_object.get_signal_strength:
                if entry_price > shield_object.get_long_stop:

                    points_in_stop, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_long_stop)

                    # contract = ibi.CFD("GBP.USD", currency="USD", exchange="IDEALPRO")
                    contract = ibi.Forex(symbol, currency="USD", exchange="IDEALPRO")

                    # contract = ibi.Contract()
                    # contract.symbol = "EUR"
                    # contract.secType = "CFD"
                    # contract.currency = "USD"
                    # contract.exchange = "IDEALPRO"

                    orders = self.ibrk.ib.bracketOrder(action="BUY", 
                                              quantity=lots,
                                              limitPrice=entry_price,
                                              takeProfitPrice=self.prices.round(symbol, entry_price + self.risk_manager.target_ratio * points_in_stop),
                                              stopLossPrice=self.prices.round(symbol, entry_price - self.risk_manager.stop_ratio * points_in_stop)
                                              )
                    print(contract)
                    for i in orders:
                        print(i)
                        self.ibrk.ib.placeOrder(contract, i)
            else:
                print(f"{symbol.ljust(12)}: Waiting for signal strength...")
    

    # def short_entry(self, symbol:str, reference:str, break_level:float, trading_timeframe:int):
    #     entry_price = self.prices.get_entry_price(symbol)
        
    #     if entry_price:
    #         shield_object = self.risk_manager.get_stop_range(symbol=symbol, timeframe=trading_timeframe)

    #         if shield_object.get_signal_strength and self.risk_manager.check_trade_wait_time(symbol=symbol):
    #             if entry_price < shield_object.get_short_stop:
    #                 try:
    #                     print(f"{symbol.ljust(12)}: {Directions.SHORT}")      
    #                     points_in_stop, lots = self.risk_manager.get_lot_size(symbol=symbol, entry_price=entry_price, stop_price=shield_object.get_short_stop)

    #                     order_request = {
    #                         "action": mt5.TRADE_ACTION_PENDING,
    #                         "symbol": symbol,
    #                         "volume": lots,
    #                         "type": mt5.ORDER_TYPE_SELL_LIMIT,
    #                         "price": entry_price,
    #                         "sl": self.prices.round(symbol, entry_price + self.risk_manager.stop_ratio * points_in_stop),
    #                         "tp": self.prices.round(symbol, entry_price - self.risk_manager.target_ratio * points_in_stop),
    #                         "comment": f"{reference}-{break_level}",
    #                         "magic":trading_timeframe,
    #                         "type_time": mt5.ORDER_TIME_GTC,
    #                         "type_filling": mt5.ORDER_FILLING_RETURN,
    #                     }
                        
    #                     request_log = mt5.order_send(order_request)
    #                 except Exception as e:
    #                     print(f"{symbol.ljust(12)}: {e}")     
    #         else:
    #             print(f"{symbol.ljust(12)}: Waiting for signal strength...")      

if __name__ == "__main__":
    symbol = "EURUSD"
    ibrk = IBRK()
    risk_obj = RiskManager(ibrk=ibrk)
    prices_obj = Prices(ibrk=ibrk)
    order_obj = Orders(prices=prices_obj, risk_manager=risk_obj, ibrk=ibrk)

    # Test: Cancel all pending orders
    # order_obj.cancel_all_pending_orders()

    # Test: Close all open positions
    # order_obj.close_all_positions()
    
    # Test: Enter Long Position
    order_obj.long_entry(symbol=symbol, trading_timeframe=60)

    # Test: Enter Short Position
    # order_obj.short_entry(symbol=symbol, break_level=0.87834, trading_timeframe=60)


