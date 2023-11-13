from datetime import datetime,  timedelta
import MetaTrader5 as mt5
import pytz
import numpy as np

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

def previous_candle_move(symbol):
    h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 1, 1)[0]
    spread = get_spread(symbol)
    high = h1["high"] + 3 * spread
    low = h1["low"] - 3 * spread
    length = round(abs(high-low), 5)
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

def get_candle_signal(symbol):
    # get 10 EURUSD H4 bars starting from 01.10.2020 in UTC time zone
    h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 1)[0]
    h4_sig=  "L" if h4['close'] - h4['open'] > 2 * get_spread(symbol) else "S" if abs(h4['open'] - h4['close']) > 2 * get_spread(symbol) else "X"
    h2 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H2, 0, 1)[0]
    h2_sig=  "L" if h2['close'] - h2['open'] > 2 * get_spread(symbol) else "S" if abs(h2['open'] - h2['close']) > 2 * get_spread(symbol) else "X"
    h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1)[0]
    h1_sig=  "L" if h1['close'] - h1['open'] > 2 * get_spread(symbol) else "S" if abs(h1['open'] - h1['close']) > 2 * get_spread(symbol) else "X"
    m30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 1)[0]
    m30_sig=  "L" if m30['close'] - m30['open'] > 2 * get_spread(symbol) else "S" if abs(m30['open'] - m30['close']) > 2 * get_spread(symbol) else "X"

    signals = [h4_sig, h2_sig,h1_sig, m30_sig]
    # print(f"{symbol.ljust(12)}: 4H: {h4_sig.upper()}, 2H: {h2_sig.upper()}, 1H: {h1_sig.upper()}, 30M: {m30_sig.upper()}")
    print(f"{symbol.ljust(12)}: {''.join(signals)}")
    
    signals = set(signals)
    if len(signals) == 1:
        return list(signals)[0]

def get_account_details():
    account_info=mt5.account_info()
    if account_info!=None:
        # display trading account data 'as is'
        return account_info.equity, account_info.margin_free


# print(get_remaining_margin())
# close_positions_with_half_profit()
# print(get_atr("US500.cash"))
# print(previous_candle_move("AUDUSD"))
