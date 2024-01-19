
import MetaTrader5 as mt
mt.initialize()

account_info_dict = mt.account_info()._asdict()
company = account_info_dict["company"]

currencies = None
indexes = None
jpy_currencies = None
support_pairs = None

# Funded Engineer
if company == "AXSE Brokerage Ltd.":
    currencies = ['AUDJPY_raw', 'AUDNZD_raw', 'AUDUSD_raw', 
                'CHFJPY_raw', 
                'EURJPY_raw', 'EURNZD_raw', 'EURUSD_raw', 'EURCAD_raw',
                'GBPUSD_raw', 'GBPJPY_raw',
                'NZDJPY_raw', "NZDCAD_raw",
                'USDCAD_raw', 'USDJPY_raw', 'USDCHF_raw', 
                'XAUUSD_raw']
    # 'ASX_raw'
    indexes = ['HK50_raw', 'NIKKEI_raw',  'SP_raw', 'FTSE_raw']

    jpy_currencies = ['AUDJPY_raw', 'CHFJPY_raw', 'EURJPY_raw', 'GBPJPY_raw' , 'NZDJPY_raw', 'USDJPY_raw']

    support_pairs = ["NZDUSD_raw", "USDHKD_raw"]

elif company == "FTMO S.R.O.":
    currencies = ['AUDJPY', 'AUDNZD', 'AUDUSD', 
                'CHFJPY', 
                'EURJPY', 'EURNZD', 'EURUSD', 'EURCAD',
                'GBPUSD', 'GBPJPY',
                'NZDJPY', "NZDCAD",
                'USDCAD', 'USDJPY', 'USDCHF', 
                'XAUUSD']

    indexes = ['AUS200.cash', 'HK50.cash', 'JP225.cash',  'US500.cash', 'UK100.cash']

    jpy_currencies = ['AUDJPY', 'CHFJPY', 'EURJPY', 'GBPJPY' , 'NZDJPY', 'USDJPY']

    support_pairs = ["NZDUSD", "USDHKD"]
# FundingPips
elif company == "Black Bull Group Limited":
    currencies = ['AUDJPY', 'AUDNZD', 'AUDUSD', 
                'CHFJPY', 
                'EURJPY', 'EURNZD', 'EURUSD', 'EURCAD',
                'GBPUSD', 'GBPJPY',
                'NZDJPY', "NZDCAD",
                'USDCAD', 'USDJPY', 'USDCHF', 
                'XAUUSD']
    # TODO JP225 is removed, because of invalid volume, which is working for FTMO
    indexes = ['SPX500', 'FTSE100'] # 'JP225',

    jpy_currencies = ['AUDJPY', 'CHFJPY', 'EURJPY', 'GBPJPY' , 'NZDJPY', 'USDJPY']

    support_pairs = ["NZDUSD", "USDHKD"]
# FundedFor
elif company == "TF Global Markets (Aust) Pty Ltd":
    currencies = ['AUDJPYx', 'AUDNZDx', 'AUDUSDx', 
                'CHFJPYx', 
                'EURJPYx', 'EURNZDx', 'EURUSDx', 'EURCADx',
                'GBPUSDx', 'GBPJPYx',
                'NZDJPYx', "NZDCADx",
                'USDCADx', 'USDJPYx', 'USDCHFx', 
                'XAUUSDx']
    
    indexes = ['SPX500x', "UK100x" ] # 'JPN225X',

    jpy_currencies = ['AUDJPYx', 'CHFJPYx', 'EURJPYx', 'GBPJPYx' , 'NZDJPYx', 'USDJPYx']

    support_pairs = ["NZDUSDx", "USDHKDx"]

else:
    raise Exception(f"The << {company} >> Trading platform not found")

for pair in (currencies + indexes + support_pairs):
    mt.symbol_select(f"{pair}", True)


def get_symbol_mapping(symbol):
    if company == "FTMO S.R.O.":
       return symbol
    elif company == "Black Bull Group Limited":
        # Check which radio button is selected
        if symbol == "US500.cash":
            return "SPX500"
        elif symbol == "UK100.cash":
            return "FTSE100"
        elif symbol == "JP225.cash":
            return "JP225"
        elif symbol == "AUDNZD":
            return symbol
        elif symbol == "USDJPY":
            return symbol
        elif symbol == "USDCHF":
            return symbol
        elif symbol == "AUDJPY":
            return symbol
        elif symbol == "NZDJPY":
            return symbol
        elif symbol == "EURJPY":
            return symbol
        elif symbol == "GBPJPY":
            return symbol
        elif symbol == "EURCAD":
            return symbol
        elif symbol == "NZDCAD":
            return symbol
        elif symbol == "XAUUSD":
            return symbol
        elif symbol == "EURUSD":
            return symbol
        elif symbol == "USDCAD":
            return symbol
        elif symbol == "AUDUSD":
            return symbol
        elif symbol == "GBPUSD":
            return symbol
        elif symbol == "EURNZD":
            return symbol
        elif symbol == "CHFJPY":
            return symbol
        else:
            print(f"Currency Pair No defined in manage_positions.py {symbol}")
    elif company == "AXSE Brokerage Ltd.":
        # Check which radio button is selected
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
        elif symbol == "AUDNZD":
            return "AUDNZD_raw"
        elif symbol == "USDJPY":
            return "USDJPY_raw"
        elif symbol == "USDCHF":
            return "USDCHF_raw"
        elif symbol == "AUDJPY":
            return "AUDJPY_raw"
        elif symbol == "NZDJPY":
            return "NZDJPY_raw"
        elif symbol == "EURJPY":
            return "EURJPY_raw"
        elif symbol == "GBPJPY":
            return "GBPJPY_raw"
        elif symbol == "EURCAD":
            return "EURCAD_raw"
        elif symbol == "NZDCAD":
            return "NZDCAD_raw"
        elif symbol == "XAUUSD":
            return "XAUUSD_raw"
        elif symbol == "EURUSD":
            return "EURUSD_raw"
        elif symbol == "USDCAD":
            return  "USDCAD_raw"
        elif symbol == "AUDUSD":
            return "AUDUSD_raw"
        elif symbol == "GBPUSD":
            return "GBPUSD_raw"
        elif symbol == "EURNZD":
            return "EURNZD_raw"
        elif symbol == "CHFJPY":
            return "CHFJPY_raw"
        else:
            print(f"Currency Pair No defined in manage_positions.py {symbol}")
    elif company == "TF Global Markets (Aust) Pty Ltd":
        # Check which radio button is selected
        if symbol == "US500.cash":
            return "SPX500x"
        elif symbol == "UK100.cash":
            return "UK100x"
        elif symbol == "JP225.cash":
            return "JPN225X"
        elif symbol == "AUDNZD":
            return "AUDNZDx"
        elif symbol == "USDJPY":
            return "USDJPYx"
        elif symbol == "USDCHF":
            return "USDCHFx"
        elif symbol == "AUDJPY":
            return "AUDJPYx"
        elif symbol == "NZDJPY":
            return "NZDJPYx"
        elif symbol == "EURJPY":
            return "EURJPYx"
        elif symbol == "GBPJPY":
            return "GBPJPYx"
        elif symbol == "EURCAD":
            return "EURCADx"
        elif symbol == "NZDCAD":
            return "NZDCADx"
        elif symbol == "XAUUSD":
            return "XAUUSDx"
        elif symbol == "EURUSD":
            return "EURUSDx"
        elif symbol == "USDCAD":
            return  "USDCADx"
        elif symbol == "AUDUSD":
            return "AUDUSDx"
        elif symbol == "GBPUSD":
            return "GBPUSDx"
        elif symbol == "EURNZD":
            return "EURNZDx"
        elif symbol == "CHFJPY":
            return "CHFJPYx"
        else:
            print(f"Currency Pair No defined in manage_positions.py {symbol}")