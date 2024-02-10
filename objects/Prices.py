import MetaTrader5 as mt5
import modules.currency_pairs as curr

class Prices:
    def __init__(self):
        pass
    
    def _get_exchange_price(self, symbol):
        ask_price = mt5.symbol_info_tick(symbol).ask
        bid_price = mt5.symbol_info_tick(symbol).bid
        exchange_rate = round((bid_price + ask_price)/2, 4)
        return exchange_rate

    def get_dollar_value(self, symbol):
        """"
        The dollar value received is inversely proportional to the estimated number of lots. Therefore, 
        increasing the dollar value will lead to a decrease in lots, ultimately reducing the overall risk
        for a single position.
        """
        symbol_lead = symbol[0:3]
        symbol_follow = symbol[3:6]

        if curr.company == "FTMO S.R.O.":
            if symbol == "US500.cash":
                return 1
            elif symbol == "UK100.cash":
                return self._get_exchange_price("GBPUSD")
            elif symbol == "HK50.cash":
                return round(1/self._get_exchange_price("USDHKD"), 4)
            elif symbol == "JP225.cash":
                return round(1/self._get_exchange_price("USDJPY"), 4)
            elif symbol == "AUS200.cash":
                return self._get_exchange_price("AUDUSD")
            elif symbol == "XAUUSD":
                return 2/self._get_exchange_price("XAUUSD")
            elif symbol == "AUDUSD":
                return 1.6 * self._get_exchange_price("AUDUSD") # TODO, This fix number 1.6 has to be changed!
            elif symbol == "NZDUSD":
                return 1.6 * self._get_exchange_price("NZDUSD") # TODO, This fix number 1.6 has to be changed!
            elif symbol in ["CADJPY", "CADCHF"]:
                return (1/self._get_exchange_price(symbol)) * 1/self._get_exchange_price(f"USDCAD")
            elif symbol in ["CHFJPY"]:
                return (1/self._get_exchange_price(symbol)) * 1/self._get_exchange_price(f"USDCHF")
            elif symbol_lead == "USD":
                """
                e.g USDJPY, USDCAD, USDCHF
                If the currency is lead by USD then we just calculate the inverse of the exchange
                """
                return 1/self._get_exchange_price(symbol)
            elif symbol_follow == "USD":
                """
                e.g GBPUSD, EURUSD
                If the currency is followed by USD then we just calculate the exchange
                """
                return self._get_exchange_price(symbol)
            else:
                """
                e.g AUDNZD, AUDJPY, NZDJPY, EURJPY, GBPJPY
                Non of the currency lead by USD
                """
                return (1/self._get_exchange_price(symbol)) * self._get_exchange_price(f"{symbol_lead}USD")
            
        elif curr.company == "Black Bull Group Limited":
            if symbol == "SPX500":
                return 1
            elif symbol == "FTSE100":
                return self._get_exchange_price("GBPUSD")
            elif symbol == "JP225":
                return round(1/self._get_exchange_price("USDJPY"), 4)
            elif symbol == "XAUUSD":
                return 2/self._get_exchange_price("XAUUSD")
            elif symbol == "AUDUSD":
                return 1.6 * self._get_exchange_price("AUDUSD") # TODO, This fix number 1.6 has to be changed!
            elif symbol == "NZDUSD":
                return 1.6 * self._get_exchange_price("NZDUSD") # TODO, This fix number 1.6 has to be changed!
            elif symbol in ["CADJPY", "CADCHF"]:
                return (1/self._get_exchange_price(symbol)) * 1/self._get_exchange_price(f"USDCAD")
            elif symbol in ["CHFJPY"]:
                return (1/self._get_exchange_price(symbol)) * 1/self._get_exchange_price(f"USDCHF")
            elif symbol_lead == "USD":
                """
                e.g USDJPY, USDCAD, USDCHF
                If the currency is lead by USD then we just calculate the inverse of the exchange
                """
                return 1/self._get_exchange_price(symbol)
            elif symbol_follow == "USD":
                """
                e.g GBPUSD, EURUSD
                If the currency is followed by USD then we just calculate the exchange
                """
                return self._get_exchange_price(symbol)
            else:
                """
                e.g AUDNZD, AUDJPY, NZDJPY, EURJPY, GBPJPY
                Non of the currency lead by USD
                """
                return (1/self._get_exchange_price(symbol)) * self._get_exchange_price(f"{symbol_lead}USD")
            
        elif curr.company == "AXSE Brokerage Ltd.":
            if symbol == "SP_raw":
                return 1
            elif symbol == "FTSE_raw":
                return self._get_exchange_price("GBPUSD_raw")
            elif symbol == "HK50_raw":
                return round(1/self._get_exchange_price("USDHKD_raw"), 4)
            elif symbol == "NIKKEI_raw":
                return round(1/self._get_exchange_price("USDJPY_raw"), 4)
            elif symbol == "ASX_raw":
                return self._get_exchange_price("AUDUSD_raw")
            elif symbol == "XAUUSD_raw":
                return 2/self._get_exchange_price("XAUUSD_raw")
            elif symbol == "AUDUSD_raw":
                return 1.6 * self._get_exchange_price("AUDUSD_raw") # TODO, This fix number 1.6 has to be changed!
            elif symbol == "NZDUSD_raw":
                return 1.6 * self._get_exchange_price("NZDUSD_raw") # TODO, This fix number 1.6 has to be changed!
            elif symbol in ["CADJPY_raw", "CADCHF_raw"]:
                return (1/self._get_exchange_price(symbol)) * 1/self._get_exchange_price(f"USDCAD_raw")
            elif symbol in ["CHFJPY_raw"]:
                return (1/self._get_exchange_price(symbol)) * 1/self._get_exchange_price(f"USDCHF_raw")
            elif symbol_lead == "USD":
                """
                e.g USDJPY, USDCAD, USDCHF
                If the currency is lead by USD then we just calculate the inverse of the exchange
                """
                return 1/self._get_exchange_price(symbol)
            elif symbol_follow == "USD":
                """
                e.g GBPUSD, EURUSD
                If the currency is followed by USD then we just calculate the exchange
                """
                return self._get_exchange_price(symbol)
            else:
                """
                e.g AUDNZD, AUDJPY, NZDJPY, EURJPY, GBPJPY
                Non of the currency lead by USD
                """
                return (1/self._get_exchange_price(symbol)) * self._get_exchange_price(f"{symbol_lead}USD_raw")
            
        elif curr.company == "TF Global Markets (Aust) Pty Ltd":
            if symbol == "SPX500x":
                return 1
            elif symbol == "UK100x":
                return self._get_exchange_price("GBPUSDx")
            elif symbol == "HK50.cash":
                return round(1/self._get_exchange_price("USDHKDx"), 4)
            elif symbol == "JPN225X":
                return round(1/self._get_exchange_price("USDJPYx"), 4)
            elif symbol == "AUS200.cash":
                return self._get_exchange_price("AUDUSDx")
            elif symbol == "XAUUSDx":
                return 2/self._get_exchange_price("XAUUSDx")
            elif symbol == "AUDUSDx":
                return 1.6 * self._get_exchange_price("AUDUSDx") # TODO, This fix number 1.6 has to be changed!
            elif symbol == "NZDUSDx":
                return 1.6 * self._get_exchange_price("NZDUSDx") # TODO, This fix number 1.6 has to be changed!
            elif symbol in ["CADJPYx", "CADCHFx"]:
                return (1/self._get_exchange_price(symbol)) * 1/self._get_exchange_price(f"USDCADx")
            elif symbol in ["CHFJPYx"]:
                return (1/self._get_exchange_price(symbol)) * 1/self._get_exchange_price(f"USDCHFx")
            elif symbol_lead == "USD":
                """
                e.g USDJPY, USDCAD, USDCHF
                If the currency is lead by USD then we just calculate the inverse of the exchange
                """
                return 1/self._get_exchange_price(symbol)
            elif symbol_follow == "USD":
                """
                e.g GBPUSD, EURUSD
                If the currency is followed by USD then we just calculate the exchange
                """
                return self._get_exchange_price(symbol)
            else:
                """
                e.g AUDNZD, AUDJPY, NZDJPY, EURJPY, GBPJPY
                Non of the currency lead by USD
                """
                return (1/self._get_exchange_price(symbol)) * self._get_exchange_price(f"{symbol_lead}USDx")