
import MetaTrader5 as mt
mt.initialize()

account_info_dict = mt.account_info()._asdict()
company = account_info_dict["company"]

currencies = None
indexes = None
jpy_currencies = None
support_pairs = None

if company == "AXSE Brokerage Ltd.":
    currencies = ['AUDJPY_raw', 'AUDNZD_raw', 'AUDUSD_raw', 
                'CHFJPY_raw', 
                'EURJPY_raw', 'EURNZD_raw', 'EURUSD_raw', 'EURCAD_raw',
                'GBPUSD_raw', 'GBPJPY_raw',
                'NZDJPY_raw', "NZDCAD_raw",
                'USDCAD_raw', 'USDJPY_raw', 'USDCHF_raw', 
                'XAUUSD_raw']

    indexes = ['ASX_raw', 'HK50_raw', 'NIKKEI_raw',  'SP_raw', 'FTSE_raw']

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

else:
    raise Exception(f"The << {company} >> Trading platform not found")

for pair in (currencies + indexes + support_pairs):
    mt.symbol_select(f"{pair}", True)