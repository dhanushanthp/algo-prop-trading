from modules.ibrk import Currencies as curr
from typing import Tuple
from clients.ibrk_wrapper import IBRK

class Prices:
    def __init__(self, ibrk):
        self.ibrk:IBRK = ibrk
    
    def get_exchange_price(self, symbol) -> float:
        bid_price, ask_price = self.ibrk.get_bid_ask(symbol=symbol)
        exchange_rate = round((bid_price + ask_price)/2, 4)
        return exchange_rate

    def get_bid_ask(self, symbol) -> Tuple[float, float]:
        bid_price, ask_price = self.ibrk.get_bid_ask(symbol=symbol)
        return bid_price, ask_price

    def get_entry_price(self, symbol) -> float:
        """
        Rounded according to Symbol
        """
        try:
            entry_price = self.get_exchange_price(symbol=symbol)
            return self.round(symbol=symbol, price=entry_price)
        except Exception:
            return None
    
    def round(self, symbol, price) -> float:
        round_factor = 5 if symbol in curr.currencies else 2
        round_factor = 2 if symbol == "XAUUSD" else round_factor
        round_factor = 3 if symbol in curr.jpy_pairs else round_factor
        return round(price, round_factor)
    
    def get_spread(self, symbol) -> float:
        bid_price, ask_price = self.ibrk.get_bid_ask(symbol=symbol)
        spread = ask_price - bid_price
        return spread

    def get_dollar_value(self, symbol) -> float:
        """"
        The dollar value received is inversely proportional to the estimated number of lots. Therefore, 
        increasing the dollar value will lead to a decrease in lots, ultimately reducing the overall risk
        for a single position.
        """
        symbol_lead = symbol[0:3]
        symbol_follow = symbol[3:6]

        if symbol == "US500.cash":
            return 1.0
        elif symbol == "UK100.cash":
            return self.get_exchange_price("GBPUSD")
        elif symbol == "HK50.cash":
            return round(1/self.get_exchange_price("USDHKD"), 4)
        elif symbol == "JP225.cash":
            return round(1/self.get_exchange_price("USDJPY"), 4)
        elif symbol == "AUS200.cash":
            return self.get_exchange_price("AUDUSD")
        elif symbol == "XAUUSD":
            return 2/self.get_exchange_price("XAUUSD")
        elif symbol == "AUDUSD":
            return 1.6 * self.get_exchange_price("AUDUSD") # TODO, This fix number 1.6 has to be changed!
        elif symbol == "NZDUSD":
            return 1.6 * self.get_exchange_price("NZDUSD") # TODO, This fix number 1.6 has to be changed!
        elif symbol in ["CADJPY", "CADCHF"]:
            return (1/self.get_exchange_price(symbol)) * 1/self.get_exchange_price(f"USDCAD")
        elif symbol in ["CHFJPY"]:
            return (1/self.get_exchange_price(symbol)) * 1/self.get_exchange_price(f"USDCHF")
        elif symbol_lead == "USD":
            """
            e.g USDJPY, USDCAD, USDCHF
            If the currency is lead by USD then we just calculate the inverse of the exchange
            """
            return 1/self.get_exchange_price(symbol)
        elif symbol_follow == "USD":
            """
            e.g GBPUSD, EURUSD
            If the currency is followed by USD then we just calculate the exchange
            """
            return self.get_exchange_price(symbol)
        else:
            """
            e.g AUDNZD, AUDJPY, NZDJPY, EURJPY, GBPJPY
            None of the currency lead by USD
            """
            return (1/self.get_exchange_price(symbol)) * self.get_exchange_price(f"{symbol_lead}USD")

if __name__ == "__main__":
    price_obj = Prices()
    import sys
    symbol = sys.argv[1]
    print(price_obj.get_dollar_value(symbol=symbol))