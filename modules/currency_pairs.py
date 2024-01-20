
import MetaTrader5 as mt
mt.initialize()

account_info_dict = mt.account_info()._asdict()
company = account_info_dict["company"]

currencies = None
indexes = None
jpy_currencies = None
support_pairs = None


master_currencies = ['AUDJPY', 'AUDNZD', 'AUDUSD', 'AUDCHF',
                'CHFJPY', "CADCHF", "CADJPY",
                'EURJPY', 'EURNZD', 'EURUSD', 'EURCAD', "EURAUD", "EURCHF",
                'GBPUSD', 'GBPJPY', "GBPAUD", "GBPCHF",
                'NZDJPY', "NZDCAD", "NZDUSD",
                'USDCAD', 'USDJPY', 'USDCHF', 
                'XAUUSD']

# Funded Engineer
if company == "AXSE Brokerage Ltd.":
    currencies = ['AUDJPY_raw', 'AUDNZD_raw', 'AUDUSD_raw',  'AUDCHF_raw',
                'CHFJPY_raw', "CADCHF_raw", "CADJPY_raw",
                'EURJPY_raw', 'EURNZD_raw', 'EURUSD_raw', 'EURCAD_raw', "EURAUD_raw", "EURCHF_raw",
                'GBPUSD_raw', 'GBPJPY_raw', "GBPAUD_raw", "GBPCHF_raw",
                'NZDJPY_raw', "NZDCAD_raw", "NZDUSD_raw",
                'USDCAD_raw', 'USDJPY_raw', 'USDCHF_raw', 
                'XAUUSD_raw']
    # 'ASX_raw'
    indexes = ['HK50_raw', 'NIKKEI_raw',  'SP_raw', 'FTSE_raw']

    jpy_currencies = ['AUDJPY_raw', 'CHFJPY_raw', 'EURJPY_raw', 'GBPJPY_raw' , 'NZDJPY_raw', 'USDJPY_raw', "CADJPY_raw"]

    support_pairs = ["NZDUSD_raw", "USDHKD_raw"]

elif company == "FTMO S.R.O.":
    currencies = ['AUDJPY', 'AUDNZD', 'AUDUSD', 'AUDCHF',
                'CHFJPY', "CADCHF", "CADJPY",
                'EURJPY', 'EURNZD', 'EURUSD', 'EURCAD', "EURAUD", "EURCHF",
                'GBPUSD', 'GBPJPY', "GBPAUD", "GBPCHF",
                'NZDJPY', "NZDCAD", "NZDUSD",
                'USDCAD', 'USDJPY', 'USDCHF', 
                'XAUUSD']

    indexes = ['AUS200.cash', 'HK50.cash', 'JP225.cash',  'US500.cash', 'UK100.cash']

    jpy_currencies = ['AUDJPY', 'CHFJPY', 'EURJPY', 'GBPJPY' , 'NZDJPY', 'USDJPY', "CADJPY"]

    support_pairs = ["NZDUSD", "USDHKD"]
# FundingPips
elif company == "Black Bull Group Limited":
    currencies = ['AUDJPY', 'AUDNZD', 'AUDUSD', 'AUDCHF',
                'CHFJPY', "CADCHF", "CADJPY",
                'EURJPY', 'EURNZD', 'EURUSD', 'EURCAD', "EURAUD", "EURCHF",
                'GBPUSD', 'GBPJPY', "GBPAUD", "GBPCHF",
                'NZDJPY', "NZDCAD", "NZDUSD",
                'USDCAD', 'USDJPY', 'USDCHF', 
                'XAUUSD']
    # TODO JP225 is removed, because of invalid volume, which is working for FTMO
    indexes = ['SPX500', 'FTSE100'] # 'JP225',

    jpy_currencies = ['AUDJPY', 'CHFJPY', 'EURJPY', 'GBPJPY' , 'NZDJPY', 'USDJPY', "CADJPY"]

    support_pairs = ["NZDUSD", "USDHKD"]
# FundedFor
elif company == "TF Global Markets (Aust) Pty Ltd":
    currencies = ['AUDJPYx', 'AUDNZDx', 'AUDUSDx', 'AUDCHFx',
                'CHFJPYx', "CADCHFx", "CADJPYx",
                'EURJPYx', 'EURNZDx', 'EURUSDx', 'EURCADx', "EURAUDx", "EURCHFx",
                'GBPUSDx', 'GBPJPYx', "GBPAUDx", "GBPCHFx",
                'NZDJPYx', "NZDCADx", "NZDUSDx",
                'USDCADx', 'USDJPYx', 'USDCHFx', 
                'XAUUSDx']
    
    indexes = ['SPX500x', "UK100x" ] # 'JPN225X',

    jpy_currencies = ['AUDJPYx', 'CHFJPYx', 'EURJPYx', 'GBPJPYx' , 'NZDJPYx', 'USDJPYx', "CADJPYx"]

    support_pairs = ["NZDUSDx", "USDHKDx"]

else:
    raise Exception(f"The << {company} >> Trading platform not found")

for pair in (currencies + indexes + support_pairs):
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