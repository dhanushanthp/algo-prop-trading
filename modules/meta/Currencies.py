import MetaTrader5 as mt
mt.initialize()
from modules.meta import util

account_info_dict = mt.account_info()._asdict()
company = account_info_dict["company"]

currencies = None
indexes = None
jpy_currencies = None
support_pairs = None

major_pairs = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF", "AUDUSD", "EURCHF", "US500.cash", "XAUUSD"]
us_indexes = ["US500.cash", "XAUUSD"]

master_stocks = ["AAPL", "AMZN", "NVDA", "TSLA", "GOOG", "MSFT", "META"]

# master_currencies = ['AUDJPY', 'AUDNZD', 'AUDUSD', 'AUDCHF', "AUDCAD",
#                     'CHFJPY', "CADCHF", "CADJPY",
#                     'EURJPY', 'EURNZD', 'EURUSD', 'EURCAD', "EURAUD", "EURCHF",
#                     'GBPUSD', 'GBPJPY', "GBPAUD", "GBPCHF",
#                     'NZDJPY', "NZDCAD", "NZDUSD",
#                     'USDCAD', 'USDJPY', 'USDCHF',
#                     'XAUUSD']

master_currencies = major_pairs

# master_jpy_pairs = ['AUDJPY', 'CHFJPY', 'EURJPY', 'GBPJPY' , 'NZDJPY', 'USDJPY', "CADJPY"]

master_jpy_pairs = ["USDJPY"]

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

# + indexes + support_pairs+
for pair in (currencies +  master_stocks):
    mt.symbol_select(f"{pair}", True)


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

def get_major_symbols(security="FOREX"):
    if security == "FOREX":
        main_pairs = major_pairs.copy()
      
        # if util.is_us_premarket_peroid():
        #     main_pairs.extend(us_indexes)
        
        return main_pairs
    elif security == "STOCK":
        return master_stocks
    else:
        raise Exception("Security is not defined!") 

if __name__ == "__main__":
    for i in range(10):
        print(get_major_symbols())