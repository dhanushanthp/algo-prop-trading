from datetime import datetime,  timedelta
import MetaTrader5 as mt5
import pytz
import numpy as np

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

def previous_candle_move(symbol):
    h1_1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 1, 1)[0]
    h1_0 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1)[0]
    spread = get_spread(symbol)
    
    # Previous bar high/low
    high = h1_1["high"]
    low = h1_1["low"]
    
    # Some cases current bar low could be lower than the previous hour bar and current bar high higher than previous high
    high_0 = h1_0["high"]
    low_0 = h1_0["low"]
    
    if high_0 > high:
        high = high_0
    
    if low_0 < low:
        low = low_0
    
    length = round(abs(high-low), 5)
    
    # Since I'm taking valided entries. I may not need this condition
    # high = high + 3 * spread
    # low = low - 3 * spread
    
    return high, low, length

def get_stop_range(symbol):
    high, low, length = previous_candle_move(symbol)
    return high, low, length

def get_atr(symbol):
    """
    Get ATR based on 4 hour
    """    
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 20)
    
    high = np.array([x['high'] for x in rates])
    low = np.array([x['low'] for x in rates])
    close = np.array([x['close'] for x in rates])

    true_range = np.maximum(high[1:] - low[1:], abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1]))
    atr = np.mean(true_range[-14:])

    return round(atr, 5)

def get_spread(symbol):
    ask_price = mt5.symbol_info_tick(symbol).ask
    bid_price = mt5.symbol_info_tick(symbol).bid
    spread = ask_price - bid_price
    return spread

def get_candle_signal(symbol, verb=True):
    h6 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H6, 0, 1)[0]
    h6_sig=  "L" if h6['close'] - h6['open'] > 2 * get_spread(symbol) else "S" if abs(h6['open'] - h6['close']) > 2 * get_spread(symbol) else "X"
    h6_body = abs(h6['open'] - h6['close'])
    h6_wick = abs(h6['high'] - h6['low']) - h6_body
    h6_strong_candle = h6_wick < h6_body # Body should be double the length than the wicks
    
    # get 10 EURUSD H4 bars starting from 01.10.2020 in UTC time zone
    h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 1)[0]
    h4_sig=  "L" if h4['close'] - h4['open'] > 2 * get_spread(symbol) else "S" if abs(h4['open'] - h4['close']) > 2 * get_spread(symbol) else "X"
    h4_body = abs(h4['open'] - h4['close'])
    h4_wick = abs(h4['high'] - h4['low']) - h4_body
    h4_strong_candle = h4_wick < h4_body # Body should be double the length than the wicks

    h2 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H2, 0, 1)[0]
    h2_sig=  "L" if h2['close'] - h2['open'] > 2 * get_spread(symbol) else "S" if abs(h2['open'] - h2['close']) > 2 * get_spread(symbol) else "X"
    h2_body = abs(h2['open'] - h2['close'])
    h2_wick = abs(h2['high'] - h2['low']) - h2_body
    h2_strong_candle = h2_wick < h2_body # Body should be double the length than the wicks

    h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1)[0]
    h1_sig=  "L" if h1['close'] - h1['open'] > 2 * get_spread(symbol) else "S" if abs(h1['open'] - h1['close']) > 2 * get_spread(symbol) else "X"
    h1_body = abs(h1['open'] - h1['close'])
    h1_wick = abs(h1['high'] - h1['low']) - h1_body
    h1_strong_candle = h1_wick < h1_body # Body should be double the length than the wicks
    
    m30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 1)[0]
    m30_sig=  "L" if m30['close'] - m30['open'] > 2 * get_spread(symbol) else "S" if abs(m30['open'] - m30['close']) > 2 * get_spread(symbol) else "X"
    m30_body = abs(m30['open'] - m30['close'])
    m30_wick = abs(m30['high'] - m30['low']) - m30_body
    m30_strong_candle = m30_wick < m30_body # Body should be double the length than the wicks

    signals = [h6_sig, h4_sig, h2_sig, h1_sig, m30_sig]
    
    if verb:
        print(f"{symbol.ljust(12)}: {''.join(signals)} : {int(h6_strong_candle)}{int(h4_strong_candle)}{int(h2_strong_candle)}{int(h1_strong_candle)}{int(m30_strong_candle)}")
    
    signals = set(signals)
    if len(signals) == 1 and h6_strong_candle and h4_strong_candle and h2_strong_candle and h1_strong_candle and m30_strong_candle:
        return list(signals)[0]

def get_account_details():
    account_info=mt5.account_info()
    if account_info!=None:
        # display trading account data 'as is'
        return account_info.balance, account_info.equity, account_info.margin_free, account_info.profit

if __name__ == "__main__":
    # close_positions_with_half_profit()
    # print(get_atr("US500.cash"))
    # print(previous_candle_move("AUDUSD"))
    # print(get_candle_signal("EURJPY"))
    print(get_account_details())