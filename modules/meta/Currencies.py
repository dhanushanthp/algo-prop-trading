import MetaTrader5 as mt
mt.initialize()
from modules.meta import util
import numpy as np

account_info_dict = mt.account_info()._asdict()
company = account_info_dict["company"]

currencies = None
indexes = None
jpy_currencies = None
support_pairs = None

"""
All Collections
"""
us_indexes = ["US500.cash", "XAUUSD"]

master_stocks = ["AAPL", "AMZN", "NVDA", "TSLA", "GOOG", "MSFT", "META"]

master_currencies = ['AUDJPY', 'AUDNZD', 'AUDUSD', 'AUDCHF', "AUDCAD",
                    'CHFJPY', "CADCHF", 
                    "CADJPY",
                    'EURJPY', 'EURNZD', 'EURUSD', 'EURCAD', "EURAUD", "EURCHF",
                    'GBPUSD', 'GBPJPY', "GBPAUD", "GBPCHF",
                    'NZDJPY', "NZDCAD", "NZDUSD",
                    'USDCAD', 'USDJPY', 'USDCHF']

master_jpy_pairs = ['AUDJPY', 'CHFJPY', 'EURJPY', 'GBPJPY' , 'NZDJPY', 'USDJPY', "CADJPY"]

"""
Major Symbols
'EURJPY', 'GBPJPY', 'CADJPY', 'CHFJPY', 'AUDJPY', "NZDJPY", "USDJPY": All move on same direcion, So pick USDJPY
'EURUSD', 'GBPUSD': Pick 'GBPUSD'
'NZDUSD', 'NZDCAD': Pick 'NZDUSD'
'EURAUD', 'EURNZD', 'GBPAUD':  Pick 'EURAUD'
'CADCHF', 'AUDCHF', 'USDCHF' Pick USDCHF
'EURCHF', 'GBPCHF': Pick EURCHF
"AUDUSD", "AUDCAD": Pick AUDUSD
"NZDUSD, "AUDUSD": Pick AUSUSD
"""
major_pairs = ['AUDNZD', 'AUDUSD', 'EURCAD', 'EURAUD', 'EURCHF', 'GBPUSD', 'USDCAD', 'USDCHF']

major_jpy_pairs = ["USDJPY"]

# Funded Engineer
if company == "AXSE Brokerage Ltd.":
    currencies = [f"{i}_raw" for i in master_currencies]
    jpy_currencies = [f"{i}_raw" for i in master_jpy_pairs]
    indexes = ['HK50_raw', 'NIKKEI_raw',  'SP_raw', 'FTSE_raw']
    support_pairs = ["NZDUSD_raw", "USDCAD_raw"]

# FTMO
elif company == "FTMO S.R.O.":
    currencies = master_currencies
    jpy_currencies = master_jpy_pairs
    indexes = ['AUS200.cash', 'HK50.cash', 'JP225.cash',  'US500.cash', 'UK100.cash']
    support_pairs = ["NZDUSD", "USDCAD"]

# FundingPips
elif company == "Black Bull Group Limited":
    currencies = master_currencies 
    jpy_currencies = master_jpy_pairs
    indexes = ['SPX500', 'FTSE100'] # 'JP225', # TODO JP225 is removed, because of invalid volume, which is working for FTMO
    support_pairs = ["NZDUSD", "USDCAD"]

# FundedFor
elif company == "TF Global Markets (Aust) Pty Ltd":
    currencies = [f"{i}x" for i in master_currencies]
    jpy_currencies = [f"{i}x" for i in master_jpy_pairs]
    indexes = ['SPX500x', "UK100x" ] # 'JPN225X',
    support_pairs = ["NZDUSDx", "USDCADx"]

# FundedNext
elif company == "GrowthNext - F.Z.C":
    currencies = master_currencies 
    jpy_currencies = master_jpy_pairs
    indexes = ['SPX500', "UK100", "HK50", "AUS200"] # "JP225"
    support_pairs = ["NZDUSD", "USDCAD"]

else:
    raise Exception(f"The << {company} >> Trading platform not found")


def get_symbol_mapping(symbol):
    if company == "FTMO S.R.O.":
       return symbol
    elif company == "Black Bull Group Limited":
        """
        BlackBullMarkets [Funding Pips]
        """
        if symbol == "US500.cash":
            return "SPX500"
        elif symbol == "UK100.cash":
            return "FTSE100"
        elif symbol == "JP225.cash":
            return "JP225"
        elif symbol in master_currencies:
            return symbol
        else:
            print(f"Currency Pair No defined in manage_positions.py {symbol}")
    elif company == "AXSE Brokerage Ltd.":
        """
        PurpleTrading [FundedEngineer, SFT, Blueguardian, Thefundedtrader]
        """
        if symbol == "US500.cash":
            return "SP_raw"
        elif symbol == "UK100.cash":
            return "FTSE_raw"
        elif symbol == "HK50.cash":
            return "HK50_raw"
        elif symbol == "JP225.cash":
            return "NIKKEI_raw"
        elif symbol == "AUS200.cash":
            return "ASX_raw"
        elif symbol in master_currencies:
            return f"{symbol}_raw"
        else:
            print(f"Currency Pair No defined in manage_positions.py {symbol}")
    elif company == "TF Global Markets (Aust) Pty Ltd":
        """
        ThinkMarkets [FortunesFunding Compition]
        """
        if symbol == "US500.cash":
            return "SPX500x"
        elif symbol == "UK100.cash":
            return "UK100x"
        elif symbol == "JP225.cash":
            return "JPN225x"
        elif symbol in master_currencies:
            return f"{symbol}x"
        else:
            print(f"Currency Pair No defined in manage_positions.py {symbol}")
    elif company == "GrowthNext - F.Z.C":
        """
        PurpleTrading [FundedEngineer, SFT, Blueguardian, Thefundedtrader]
        """
        if symbol == "US500.cash":
            return "SPX500"
        elif symbol == "UK100.cash":
            return "UK100"
        elif symbol == "HK50.cash":
            return "HK50"
        elif symbol == "JP225.cash":
            return "JP225"
        elif symbol == "AUS200.cash":
            return "AUS200"
        elif symbol in master_currencies:
            return f"{symbol}_raw"
        else:
            print(f"Currency Pair No defined in manage_positions.py {symbol}")

def get_ordered_symbols(without_index=False):
    """
    Retrieves a list of trading symbols ordered by the absolute value of their price changes.
    
    Returns:
        List[str]: A list of trading symbols in descending order of absolute price changes.
    """
    if without_index:
        ticks = currencies
    else:
        ticks = currencies + indexes
    
    symbol_change = []    
    for tick in ticks:
        symbol_info = mt.symbol_info(tick)
        symbol_change.append((tick, abs(symbol_info.price_change)))
        
    # Sorting the list based on the second element of each tuple in descending order
    sorted_list_desc = sorted(symbol_change, key=lambda x: x[1], reverse=True)

    # Extracting the first values from the sorted list
    sorted_list = [item[0] for item in sorted_list_desc]
    
    return sorted_list

def ticker_initiator(security="FOREX", symbol_selection="NON-PRIMARY"):
    symbols = get_symbols(security=security, symbol_selection=symbol_selection)
    for symbol in symbols:
        mt.symbol_select(symbol, True)

def get_symbols(security="FOREX", symbol_selection="NON-PRIMARY"):
    if security == "FOREX":
        main_pairs = []
        if symbol_selection == "PRIMARY":
            main_pairs.extend(major_pairs)
            main_pairs.extend(major_jpy_pairs)
            main_pairs.extend(us_indexes)
        elif symbol_selection == "NON-PRIMARY":
            main_pairs.extend(master_currencies)
            main_pairs.extend(us_indexes)
            # if util.is_us_premarket_peroid():
            #     main_pairs.extend(us_indexes)
        elif symbol_selection == "SINGLE":
            main_pairs.append("US500.cash")
        else:
            raise Exception ("Currency Selection Not Defined")

        return main_pairs
    elif security == "STOCK":
        return master_stocks
    else:
        raise Exception("Security is not defined!") 


def get_major_symbols_market_events(security="FOREX"):
    """
    This function handles the market events based symbol selection.
    """
    if security == "FOREX":
        main_pairs = master_currencies.copy()

        if util.is_us_premarket_peroid():
            main_pairs.extend(us_indexes)

        _,current_hour,_ = util.get_current_day_hour_min()
        market_mapping = util.get_maket_events()

        event_based_removed_symbols = []
        for event_hour in market_mapping.keys():
            event_symbols:list = market_mapping[event_hour]
            for event_symbol in event_symbols:
                if current_hour <= event_hour:
                    for existing_symbol in main_pairs:
                        if event_symbol in existing_symbol:
                            if event_symbol == "USD":
                                event_based_removed_symbols.append("US500.cash")
                            event_based_removed_symbols.append(existing_symbol)

        event_based_removed_symbols = list(set(event_based_removed_symbols))
        valid_symbol = np.setdiff1d(main_pairs, event_based_removed_symbols).tolist()
        return valid_symbol
    elif security == "STOCK":
        return master_stocks
    else:
        raise Exception("Security is not defined!") 

if __name__ == "__main__":
    # print(get_major_symbols_market_events())
    print(get_symbols(symbol_selection="NON-PRIMARY"))