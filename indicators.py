from datetime import datetime,  timedelta
import MetaTrader5 as mt5
import pytz
import numpy as np
import currency_pairs as curr

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

def calculate_current_position_stop(symbol):
    existing_positions = mt5.positions_get()
    for position in existing_positions:
        if symbol == position.symbol:
            entry_price = position.price_open
            stop_loss = position.sl
            distance = abs(stop_loss-entry_price)
            return round(distance, 5)


def get_mid_price(symbol):
    ask_price = mt5.symbol_info_tick(symbol).ask
    bid_price = mt5.symbol_info_tick(symbol).bid
    mid_price = (ask_price + bid_price)/2
    return mid_price

def get_bid_ask(symbol):
    ask_price = mt5.symbol_info_tick(symbol).ask
    bid_price = mt5.symbol_info_tick(symbol).bid
    return bid_price, ask_price


def get_ordered_symbols():
    ticks = (curr.currencies + curr.indexes)
    symbol_change = []    
    for tick in ticks:
        symbol_info = mt5.symbol_info(tick)
        symbol_change.append((tick, abs(symbol_info.price_change)))
        
    # Sorting the list based on the second element of each tuple in descending order
    sorted_list_desc = sorted(symbol_change, key=lambda x: x[1], reverse=True)

    # Extracting the first values from the sorted list
    sorted_list = [item[0] for item in sorted_list_desc]
    
    return sorted_list

def previous_candle_move(symbol, timeframe):
    
    selected_time = match_timeframe(timeframe)
    
    previous_candle = mt5.copy_rates_from_pos(symbol, selected_time, 1, 1)[0]
    current_candle = mt5.copy_rates_from_pos(symbol, selected_time, 0, 1)[0]

    current_candle_body = abs(current_candle["close"] - current_candle["open"])
    previous_candle_body = abs(previous_candle["close"] - previous_candle["open"])

    previous_candle_total_length = abs(previous_candle["high"] - previous_candle["low"])

    spread = get_spread(symbol)

    # We should implment this logics here, since we are trading based on the selected timeframe
    previous_candle_signal = None
    """
    1. Previous candle should atleaat 3 times more than the spread (Avoid ranging behaviour)
        1.1 The 3 time spread for a valid current candle has been added in signal idenfication.
    2. Current candle body should be larger than the previous candle body to be valid entry
    """
    # and (current_candle_body < previous_candle_total_length)
    if (current_candle_body > 3 * spread) :
        if previous_candle["close"] > previous_candle["open"]:
            previous_candle_signal = "L"
        else:
            previous_candle_signal = "S"
    
    # Previous bar high/low
    previous_high = previous_candle["high"]
    previous_low = previous_candle["low"]

    if current_candle["high"] > previous_high:
        previous_high = current_candle["high"]
    
    if current_candle["low"] < previous_low:
        previous_low = current_candle["low"]
    
    previous_high = previous_high + 3 * spread
    previous_low = previous_low - 3 * spread
    
    mid_price = get_mid_price(symbol)
    
    atr = get_atr(symbol, selected_time)

    distance_from_high = max(atr, abs(previous_high-mid_price))
    distance_from_low = max(atr, abs(previous_low-mid_price))
    
    # Balance the stop incase if stop is too close
    if distance_from_high > distance_from_low:
        previous_low = mid_price - distance_from_high
    
    if distance_from_low > distance_from_high:
        previous_high = mid_price + distance_from_low
    
    return previous_high, previous_low, previous_candle_signal


def find_r_s(symbol, timeframe):

    selected_time = match_timeframe(timeframe)
    
    # If does the mid values intersect with previous 5 bars
    # get past 5 candles and start from prevous second candle
    past_candles = list(mt5.copy_rates_from_pos(symbol, selected_time, 2, 30))
    past_candles.reverse()

    resistance_levels = {}
    suport_levels = {}

    for i in range(len(past_candles) - 2):
        end_candle = past_candles[i]
        middle_candle = past_candles[i+1]
        start_candle = past_candles[i+2]

        if ((middle_candle['high'] - end_candle["high"]) > 3 * get_spread(symbol))  and ((middle_candle['high'] - start_candle["high"]) > 3 * get_spread(symbol)) :
            resistance_levels[i] =  middle_candle["high"]
        
        if ((end_candle["low"] - middle_candle['low']) > 3 * get_spread(symbol)) and ((start_candle["low"] - middle_candle['low']) > 3 * get_spread(symbol)):
            suport_levels[i] = middle_candle["low"]


    # Filter resistance levels, The levels should not intersect with any previous candle
    breaked_resistances = []
    breaked_supprots = []

    for res in resistance_levels.keys():
        res_level = resistance_levels[res]
        upcoming_candles = past_candles[:res]
        for candle in upcoming_candles:
            if is_number_between(res_level, candle["low"], candle["high"]):
                breaked_resistances.append(res_level)
                break

    for supp in suport_levels.keys():
        supp_level = suport_levels[supp]
        upcoming_candles = past_candles[:supp]
        for candle in upcoming_candles:
            if is_number_between(supp_level, candle["low"], candle["high"]):
                breaked_supprots.append(supp_level)
                break
    
    clean_resistance = [i for i in resistance_levels.values() if i not in breaked_resistances]
    clean_support = [i for i in suport_levels.values() if i not in breaked_supprots]

    return {"support": clean_support, "resistance": clean_resistance}


def find_resistance_support(symbol, timeframe):
    """
    Find resistance and suppot based on 4X timeframe based on current time frame
    """
    selected_time = match_timeframe(timeframe)
    
    # If does the mid values intersect with previous 5 bars
    # get past 5 candles and start from prevous second candle
    past_candles = list(mt5.copy_rates_from_pos(symbol, selected_time, 1, 3))
    past_candles.reverse()
    mid_price = get_mid_price(symbol)
    for candle in past_candles:
        if is_number_between(mid_price, candle["low"], candle["high"]):
            return True
        
    return False
    
def is_number_between(number, lower_limit, upper_limit):
    if lower_limit > upper_limit:
        return lower_limit > number > upper_limit
    else:
        return lower_limit < number < upper_limit

def get_stop_range(symbol, timeframe):
    high, low, previous_candle = previous_candle_move(symbol, timeframe)
    return high, low, previous_candle

def get_atr(symbol, selected_time):
    """
    Get ATR based on 4 hour
    """    
    rates = mt5.copy_rates_from_pos(symbol, selected_time, 0, 20)
    
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


def correlate_entry_timeframe(timeframe):
    if timeframe in [15, 30, 60]:
        return 15
    elif timeframe == 120:
        return 30
    elif timeframe == 240:
        return 60
    else:
        raise Exception("TIMEFRAME FOR PREVIOUS CANDLE NOT DEFINED")


def match_timeframe(timeframe):
    if timeframe == 5:
        selected_time = mt5.TIMEFRAME_M5
    elif timeframe == 15:
        selected_time = mt5.TIMEFRAME_M15
    elif timeframe == 30:
        selected_time = mt5.TIMEFRAME_M30
    elif timeframe == 60:
        selected_time = mt5.TIMEFRAME_H1
    elif timeframe == 120:
        selected_time = mt5.TIMEFRAME_H2
    elif timeframe == 180:
        selected_time = mt5.TIMEFRAME_H3
    elif timeframe == 240:
        selected_time = mt5.TIMEFRAME_H4
    else:
        raise Exception("TIMEFRAME FOR PREVIOUS CANDLE NOT DEFINED")
    return selected_time
                    

def is_ema_cross(symbol, timeframe):
    selected_time = match_timeframe(timeframe)

    # get 10 EURUSD H4 bars starting from 01.10.2020 in UTC time zone
    window_size = 21
    candle = mt5.copy_rates_from_pos(symbol, selected_time, 0, window_size)
    candle_close = [i["close"] for i in candle]
    sma21  = np.average(candle_close)

    # Upper Time SMA
    upper_candle = mt5.copy_rates_from_pos(symbol, selected_time, 0, 50)
    upper_candle_close = [i["close"] for i in upper_candle]
    sma50  = np.average(upper_candle_close)


    ask_price = mt5.symbol_info_tick(symbol).ask
    bid_price = mt5.symbol_info_tick(symbol).bid

    # Also confirm higher timeframe in the same trend as lower time frame
    if (candle[-1]["close"] > candle[-1]["open"]) and is_number_between(sma21, candle[-1]["open"], bid_price) and (sma50 < sma21):
        return "L", sma21
    elif (candle[-1]["close"] < candle[-1]["open"]) and is_number_between(sma21, ask_price, candle[-1]["open"]) and (sma50 > sma21):
        return "S", sma21
    
    return None, None

def get_candle_signal(symbol, verb=True):
    
    # get 10 EURUSD H4 bars starting from 01.10.2020 in UTC time zone
    h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 1)[0]
    h4_sig=  "L" if h4['close'] - h4['open'] > 3 * get_spread(symbol) else "S" if abs(h4['open'] - h4['close']) > 3 * get_spread(symbol) else "X"
    h4_body = abs(h4['open'] - h4['close'])
    h4_wick = abs(h4['high'] - h4['low']) - h4_body
    h4_strong_candle = h4_wick < h4_body # Body should be double the length than the wicks

    h2 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H2, 0, 1)[0]
    h2_sig=  "L" if h2['close'] - h2['open'] > 3 * get_spread(symbol) else "S" if abs(h2['open'] - h2['close']) > 3 * get_spread(symbol) else "X"
    h2_body = abs(h2['open'] - h2['close'])
    h2_wick = abs(h2['high'] - h2['low']) - h2_body
    h2_strong_candle = h2_wick < h2_body # Body should be double the length than the wicks

    h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1)[0]
    h1_sig=  "L" if h1['close'] - h1['open'] > 3 * get_spread(symbol) else "S" if abs(h1['open'] - h1['close']) > 3 * get_spread(symbol) else "X"
    h1_body = abs(h1['open'] - h1['close'])
    h1_wick = abs(h1['high'] - h1['low']) - h1_body
    h1_strong_candle = h1_wick < h1_body # Body should be double the length than the wicks
    
    m30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 1)[0]
    m30_sig=  "L" if m30['close'] - m30['open'] > 3 * get_spread(symbol) else "S" if abs(m30['open'] - m30['close']) > 3 * get_spread(symbol) else "X"
    m30_body = abs(m30['open'] - m30['close'])
    m30_wick = abs(m30['high'] - m30['low']) - m30_body
    m30_strong_candle = m30_wick < m30_body # Body should be double the length than the wicks

    signals = [h4_sig, h2_sig, h1_sig, m30_sig]
    
    if verb:
        print(f"{symbol.ljust(12)}: {''.join(signals)} : {int(h4_strong_candle)}{int(h2_strong_candle)}{int(h1_strong_candle)}{int(m30_strong_candle)}")
    
    signals = set(signals)
    if len(signals) == 1 and h4_strong_candle and h2_strong_candle and h1_strong_candle and m30_strong_candle:
        return list(signals)[0]

def get_account_details():
    account_info=mt5.account_info()
    if account_info!=None:
        # display trading account data 'as is'
        return account_info.balance, account_info.equity, account_info.margin_free, account_info.profit

if __name__ == "__main__":
    # close_positions_with_half_profit()
    # print(get_atr("US500.cash"))
    # [print(round(i, 5)) for i in list(get_stop_range("AUDNZD"))]
    # print(find_r_s("XAUUSD", 15))
    # print(match_timeframe(15))
    # print(match_timeframe(30))
    # print(match_timeframe(60))
    # print(mt5.TIMEFRAME_H2)
    # print(mt5.TIMEFRAME_H1)
    print(mt5.TIMEFRAME_M15)
    # print(get_candle_signal("EURJPY"))
    # print(get_account_details())