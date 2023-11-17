
import MetaTrader5 as mt

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

for pair in (currencies + indexes + support_pairs):
    mt.symbol_select(pair, True)