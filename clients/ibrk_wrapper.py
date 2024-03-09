import ib_insync as ibi
ib = ibi.IB()
client_id = 1232
import pandas as pd
import pytz
from datetime import datetime, timedelta,  time
from typing import Tuple

class IBRK:
    def __init__(self) -> None:
        self.ib:ibi.IB = ib.connect('127.0.0.1',7497, client_id)

    def match_timeframe(self, timeframe:int):
        if timeframe == 60:
            return "1 hour"
        elif timeframe == 15:
            return "15 mins"
        elif timeframe == 5:
            return "5 mins"
        else:
            raise Exception(f"Timeframe {timeframe} is not defined!")


    def get_candles(self, symbol, timeframe, days=1):
        """
        Get all previous candles per day
        """
        contract = ibi.Forex(symbol)
        bars = ib.reqHistoricalData(
                contract, 
                endDateTime='', 
                durationStr=f'{days} D',
                barSizeSetting=self.match_timeframe(timeframe), 
                whatToShow='MIDPOINT', useRTH=False)

        df = pd.DataFrame(bars)
        df["date"] = df["date"] + timedelta(hours=2)
        return df
    
    def get_last_close_price(self, symbol):
        """
        Get all previous candles per day
        """
        contract = ibi.Forex(symbol)
        bars = ib.reqHistoricalData(
                contract, 
                endDateTime='', 
                durationStr=f'30 S',
                barSizeSetting="5 secs", 
                whatToShow='MIDPOINT', useRTH=False)

        bars = bars[-1]
        return bars.close

    def get_candles_by_index(self, symbol, timeframe, prev_candle_count):
        """
        Get last n candles from the selected candles
        """
        candles = self.get_candles(symbol=symbol, timeframe=timeframe)
        return candles.tail(prev_candle_count)

    def get_previous_candle(self, symbol, timeframe):
        """
        Return previous candle
        """
        candles = self.get_candles(symbol=symbol, timeframe=timeframe)
        return candles.iloc[-2]

    def get_current_candle(self, symbol, timeframe):
        """
        Return Current candle
        """
        candles = self.get_candles(symbol=symbol, timeframe=timeframe)
        return candles.iloc[-1]

    def get_bid_ask(self, symbol) -> Tuple[float, float]:
        """
        Get bid and ask prices
        """
        contract = ibi.Forex(symbol)
        bid_ask = self.ib.reqTickers(contract)[0]

        if bid_ask.bid < 0 or bid_ask.ask < 0:
            close_price = self.get_last_close_price(symbol=symbol)
            return close_price, close_price
        return bid_ask.bid, bid_ask.ask

    def get_account(self):
        account = self.ib.accountValues()
        account_value = None
        buying_power = None
        cash_balance = None
        liquidity = None
        unrealizedPnL=  None
        for i in account:
            if i.tag == "AvailableFunds" and i.currency == "USD":
                account_value = i.value

            if i.tag == "BuyingPower" and i.currency == "USD":
                buying_power = i.value
            
            if i.tag == "CashBalance" and i.currency == "BASE":
                cash_balance = i.value
            
            if i.tag == "ExcessLiquidity" and i.currency == "USD":
                liquidity = i.value
            
            if i.tag == "UnrealizedPnL" and i.currency == "USD":
                unrealizedPnL = i.value

        ouput_dict = {"account_value":account_value ,"buy_power": buying_power, "cash_balance":cash_balance, 
                      "liquidity": liquidity, "unrealized_pnl": unrealizedPnL}
        
        return ouput_dict

    def get_active_orders(self):
        open_orders = self.ib.openOrders()
        return open_orders
    
    def get_existing_positions(self):
        existing_orders = self.ib.positions()
        return existing_orders

if __name__ == "__main__":
    obj = IBRK()
    print(obj.get_last_close_price("EURUSD"))
    print(obj.get_bid_ask("EURUSD"))
    # print(obj.get_candles("EURUSD", 60))
    # print(obj.get_previous_candle("EURUSD", 60))
    # print(obj.get_current_candle("EURUSD", 60))
    # print(obj.get_account())
    # print(obj.get_active_orders())
    # print(obj.get_existing_positions())
    # print(obj.get_candles_by_index("EURUSD", 60, 3)["high"].max())

        

