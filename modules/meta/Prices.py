import MetaTrader5 as mt5
import modules.meta.Currencies as curr
from typing import Tuple
mt5.initialize()

class Prices:    
    def get_exchange_price(self, symbol) -> float:
        ask_price = mt5.symbol_info_tick(symbol).ask
        bid_price = mt5.symbol_info_tick(symbol).bid
        exchange_rate = round((bid_price + ask_price)/2, 4)
        return exchange_rate

    def get_bid_ask(self, symbol) -> Tuple[float, float]:
        ask_price = mt5.symbol_info_tick(symbol).ask
        bid_price = mt5.symbol_info_tick(symbol).bid
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
        round_factor = 3 if symbol in curr.jpy_currencies else round_factor
        return round(price, round_factor)
    
    def get_spread(self, symbol) -> float:
        ask_price = mt5.symbol_info_tick(symbol).ask
        bid_price = mt5.symbol_info_tick(symbol).bid
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

        if curr.company == "FTMO S.R.O.":
            if symbol == "US500.cash" or (symbol in curr.master_stocks):
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
                return self.get_exchange_price("XAUUSD")
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
            
        elif curr.company == "Black Bull Group Limited":
            if symbol == "SPX500":
                return 1.0
            elif symbol == "FTSE100":
                return self.get_exchange_price("GBPUSD")
            elif symbol == "JP225":
                return round(1/self.get_exchange_price("USDJPY"), 4)
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
                e.g USDJPY, USDCAD, USDCHF, USDHKD
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
            
        elif curr.company == "AXSE Brokerage Ltd.":
            if symbol == "SP_raw":
                return 1.0
            elif symbol == "FTSE_raw":
                return self.get_exchange_price("GBPUSD_raw")
            elif symbol == "HK50_raw":
                return round(1/self.get_exchange_price("USDHKD_raw"), 4)
            elif symbol == "NIKKEI_raw":
                return round(1/self.get_exchange_price("USDJPY_raw"), 4)
            elif symbol == "ASX_raw":
                return self.get_exchange_price("AUDUSD_raw")
            elif symbol == "XAUUSD_raw":
                return 2/self.get_exchange_price("XAUUSD_raw")
            elif symbol == "AUDUSD_raw":
                return 1.6 * self.get_exchange_price("AUDUSD_raw") # TODO, This fix number 1.6 has to be changed!
            elif symbol == "NZDUSD_raw":
                return 1.6 * self.get_exchange_price("NZDUSD_raw") # TODO, This fix number 1.6 has to be changed!
            elif symbol in ["CADJPY_raw", "CADCHF_raw"]:
                return (1/self.get_exchange_price(symbol)) * 1/self.get_exchange_price(f"USDCAD_raw")
            elif symbol in ["CHFJPY_raw"]:
                return (1/self.get_exchange_price(symbol)) * 1/self.get_exchange_price(f"USDCHF_raw")
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
                return (1/self.get_exchange_price(symbol)) * self.get_exchange_price(f"{symbol_lead}USD_raw")
            
        elif curr.company == "TF Global Markets (Aust) Pty Ltd":
            if symbol == "SPX500x":
                return 1.0
            elif symbol == "UK100x":
                return self.get_exchange_price("GBPUSDx")
            elif symbol == "HK50.cash":
                return round(1/self.get_exchange_price("USDHKDx"), 4)
            elif symbol == "JPN225X":
                return round(1/self.get_exchange_price("USDJPYx"), 4)
            elif symbol == "AUS200.cash":
                return self.get_exchange_price("AUDUSDx")
            elif symbol == "XAUUSDx":
                return 2/self.get_exchange_price("XAUUSDx")
            elif symbol == "AUDUSDx":
                return 1.6 * self.get_exchange_price("AUDUSDx") # TODO, This fix number 1.6 has to be changed!
            elif symbol == "NZDUSDx":
                return 1.6 * self.get_exchange_price("NZDUSDx") # TODO, This fix number 1.6 has to be changed!
            elif symbol in ["CADJPYx", "CADCHFx"]:
                return (1/self.get_exchange_price(symbol)) * 1/self.get_exchange_price(f"USDCADx")
            elif symbol in ["CHFJPYx"]:
                return (1/self.get_exchange_price(symbol)) * 1/self.get_exchange_price(f"USDCHFx")
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
                return (1/self.get_exchange_price(symbol)) * self.get_exchange_price(f"{symbol_lead}USDx")
        
        elif curr.company == "GrowthNext - F.Z.C":
            if symbol == "SPX500":
                return 1.0
            elif symbol == "UK100":
                return self.get_exchange_price("GBPUSD")
            elif symbol == "JP225":
                return round(1/self.get_exchange_price("USDJPY"), 4)
            elif symbol == "HK50":
                return round(1/self.get_exchange_price("USDHKD"), 4)
            elif symbol == "AUS200":
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
                e.g USDJPY, USDCAD, USDCHF, USDHKD
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
        else:
            raise Exception(f"The << {curr.company} >> Trading platform not found")

if __name__ == "__main__":
    price_obj = Prices()
    import sys
    symbol = sys.argv[1]
    print(price_obj.get_dollar_value(symbol=symbol))
    # print(price_obj.get_exchange_price(symbol))