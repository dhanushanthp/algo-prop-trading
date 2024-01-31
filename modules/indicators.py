from datetime import datetime,  timedelta
import MetaTrader5 as mt5
import pytz
import numpy as np
import modules.currency_pairs as curr
import collections

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

def get_ordered_symbols(without_index=False):
    """
    Retrieves a list of trading symbols ordered by the absolute value of their price changes.
    
    Returns:
        List[str]: A list of trading symbols in descending order of absolute price changes.
    """
    if without_index:
        ticks = (curr.currencies)
    else:
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


def get_stop_range(symbol, timeframe, n_spreds=10, multiplier=1):
    
    selected_time = match_timeframe(timeframe)
    
    previous_candle = mt5.copy_rates_from_pos(symbol, selected_time, 1, 1)[0]
    
    current_candle = mt5.copy_rates_from_pos(symbol, selected_time, 0, 1)[0]
    current_candle_body = abs(current_candle["close"] - current_candle["open"])

    spread = get_spread(symbol)

    is_strong_candle = None

    # Current candle should atleaat 3 times more than the spread (Avoid ranging behaviour)
    if (current_candle_body > 3 * spread) :
        is_strong_candle = True

    # Extracting high and low values from the previous candle
    higher_stop = previous_candle["high"]
    lower_stop = previous_candle["low"]

    # Checking if the high value of the current candle is greater than the previous high
    if current_candle["high"] > higher_stop:
        # Updating the previous_high if the condition is met
        higher_stop = current_candle["high"]

    # Checking if the low value of the current candle is less than the previous low
    if current_candle["low"] < lower_stop:
        # Updating the previous_low if the condition is met
        lower_stop = current_candle["low"]
    
    # Adding buffer to candle based high and low
    higher_stop = higher_stop + (n_spreds * spread)
    lower_stop = lower_stop - (n_spreds * spread)
    
    mid_price = get_mid_price(symbol)
    
    # In cooprate ATR along with candle high/low
    atr = get_atr(symbol, selected_time)
    distance_from_high = max(atr, abs(higher_stop-mid_price))
    distance_from_low = max(atr, abs(lower_stop-mid_price))

    optimal_distance = max(distance_from_high, distance_from_low) * multiplier
    lower_stop = mid_price - optimal_distance
    higher_stop = mid_price + optimal_distance

    is_long = "N"
    if optimal_distance > atr:
        is_long = "Y"
    
    return higher_stop, lower_stop, is_strong_candle, is_long, optimal_distance

def get_account_name():
    info = mt5.account_info()
    balance = round(info.balance/1000)
    return f"{info.name} {balance}K "


def candle_based_trade(symbol, timeframe):
    """
    1 hour cdls
    """
    selected_time = match_timeframe(timeframe)
    current_cadle = list(mt5.copy_rates_from_pos(symbol, selected_time, 0, 1))[-1]

    upper_wick = abs(current_cadle["open"] - current_cadle["high"])
    lower_wick = abs(current_cadle["open"] - current_cadle["low"])

    if (6*get_spread(symbol) > abs(current_cadle["open"] - current_cadle["close"]) > 3*get_spread(symbol)) and (upper_wick > 3*get_spread(symbol) or lower_wick > 3*get_spread(symbol)):
        if current_cadle["open"] > current_cadle["close"]:
            return "short"
        else:
            return "long"
    

def close_based_reversals(symbol, timeframe, reversal_looks_back=24):
    selected_time = match_timeframe(timeframe)
    
    past_candles = list(mt5.copy_rates_from_pos(symbol, selected_time, 1, reversal_looks_back))
    past_candles.reverse()

    resistance_levels = {}
    suport_levels = {}

    for i in range(len(past_candles) - 1):
        current_candle = past_candles[i]
        next_candle = past_candles[i+1]

        current_candle_dir = "long" if current_candle["open"] < current_candle["close"] else "short"
        next_candle_dir = "long" if next_candle["open"] < next_candle["close"] else "short"

        if next_candle_dir == "long" and current_candle_dir=="short":
            resistance_levels[i] = next_candle["close"]
        elif next_candle_dir == "short" and current_candle_dir=="long":
            suport_levels[i] = next_candle["close"]
    
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


def find_reversal_zones(symbol, timeframe, reversal_looks_back=20):
    """
    Finds potential reversal zones based on historical price data.

    Parameters:
    - symbol (str): The trading symbol for the financial instrument.
    - timeframe (str): The timeframe for historical price data (e.g., 'M1', 'H1', 'D1').
    - reversal_looks_back (int): The number of candles to look back for identifying potential reversals (default: 20).

    Returns:
    dict: A dictionary containing identified support and resistance levels.
        Example:
        {
            'support': [support_level1, support_level2, ...],
            'resistance': [resistance_level1, resistance_level2, ...]
        }

    The function analyzes historical price data to identify potential reversal zones by comparing
    highs and lows of adjacent candles. It then filters out levels that intersect with previous candles.

    Note: The function relies on a helper function, `match_timeframe`, and assumes the existence of
    another helper function, `is_number_between`.

    :param symbol: Trading symbol for the financial instrument.
    :param timeframe: Timeframe for historical price data.
    :param reversal_looks_back: Number of candles to look back for potential reversals (default: 20).
    :return: A dictionary with 'support' and 'resistance' levels.
    """

    selected_time = match_timeframe(timeframe)
    
    past_candles = list(mt5.copy_rates_from_pos(symbol, selected_time, 0, reversal_looks_back * 10))
    past_candles.reverse()

    resistance_levels = {}
    suport_levels = {}

    for i in range(len(past_candles) - 2*reversal_looks_back - 1):
        i_current_candle = i + reversal_looks_back
        i_candle_forward = i_current_candle - reversal_looks_back
        i_candle_backward = i_current_candle + reversal_looks_back

        current_candle = past_candles[i_current_candle]
        candle_forward = past_candles[i_candle_forward: i_current_candle - 1]
        candle_backward = past_candles[i_current_candle + 1: i_candle_backward]

        # Find highs
        high_current_cadle = current_candle["high"]
        high_candle_forward = max([i["high"] for i in candle_forward])
        high_candle_backward = max([i["high"] for i in candle_backward])
        
        if high_candle_backward <= high_current_cadle and high_candle_forward <= high_current_cadle:
            resistance_levels[i_current_candle] = high_current_cadle
        
        # Find lows
        low_current_cadle = current_candle["low"]
        low_candle_forward = min([i["low"] for i in candle_forward])
        low_candle_backward = min([i["low"] for i in candle_backward])
        
        if low_candle_backward >= low_current_cadle and low_candle_forward >= low_current_cadle:
            suport_levels[i_current_candle] = low_current_cadle
    
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

def understand_direction(symbol, timeframe, level, num_past_candles=8):
    """
    Determines the market direction based on candlestick analysis.

    Parameters:
    - symbol (str): The financial instrument symbol.
    - timeframe (str): The timeframe for candlestick analysis.
    - level (float): The specified price level for analysis.

    Returns:
    - str: The market direction, either "short" for a potential short entry or
           "long" for a potential long entry.

    This function analyzes the intersection of the mid-values of the previous
    30 candles with the specified price level. If an intersection is found, the
    function checks whether the breakout is in the "short" or "long" direction
    based on the color of the previous breakout candle. A green candle indicates
    a potential short entry, while a red candle indicates a potential long entry.
    """
    selected_time = match_timeframe(timeframe)
    
    # If the mid values intersect with the previous 5 bars
    # get past 5 candles and start from the previous second candle
    past_candles = list(mt5.copy_rates_from_pos(symbol, selected_time, 1, num_past_candles))
    past_candles.reverse()
    
    for candle in past_candles:
        open_price = candle["open"]
        close_price = candle["close"]

        # If there is any candle intersection with the current level,
        # determine the breakout direction based on the previous breakout candle color
        if is_number_between(level, open_price, close_price):
            return "short"
        elif is_number_between(level, close_price, open_price):
            return "long"
    
    # If there is no candle intersection then we go for reverse
    return None

def support_resistance_levels(symbol, timeframe):
    """
    Combines support and resistance levels identified from different methods to provide a consolidated set.

    Parameters:
    - symbol (str): The trading symbol for the financial instrument.
    - timeframe (str): The timeframe for historical price data (e.g., 'M1', 'H1', 'D1').

    Returns:
    dict: A dictionary containing consolidated support and resistance levels.
        Example:
        {
            'support': [support_level1, support_level2, ...],
            'resistance': [resistance_level1, resistance_level2, ...]
        }

    This function leverages two different methods to identify support and resistance levels: one based on recent
    candlestick patterns and the other based on historical reversal zones. The identified levels from both methods
    are consolidated and returned in a clean format, free from duplicates.

    Note: The function relies on the existence of two helper functions, `find_r_s` and `find_reversal_zones`.

    :param symbol: Trading symbol for the financial instrument.
    :param timeframe: Timeframe for historical price data.
    :return: A dictionary with consolidated 'support' and 'resistance' levels.
    """
    from_candle_pattern = find_r_s(symbol, timeframe)
    from_higher_level = find_reversal_zones(symbol, timeframe)

    clean_support = from_candle_pattern["support"]
    clean_resistance = from_candle_pattern["resistance"]

    clean_support.extend(from_higher_level["support"])
    clean_resistance.extend(from_higher_level["resistance"])
    
    return {"support": clean_support, "resistance": clean_resistance}


def find_r_s(symbol, timeframe):
    """
    Identifies potential support and resistance levels based on recent price behavior.

    Parameters:
    - symbol (str): The trading symbol for the financial instrument.
    - timeframe (str): The timeframe for historical price data (e.g., 'M1', 'H1', 'D1').

    Returns:
    dict: A dictionary containing identified support and resistance levels.
        Example:
        {
            'support': [support_level1, support_level2, ...],
            'resistance': [resistance_level1, resistance_level2, ...]
        }

    The function analyzes recent price behavior by examining the highs and lows of the past three candles.
    It identifies potential resistance levels when the difference between the high of the middle candle
    and the highs of the adjacent candles is greater than 3 times the spread. Similarly, it identifies
    potential support levels when the difference between the low of the middle candle and the lows of
    the adjacent candles is greater than 3 times the spread.

    The function further filters out levels that intersect with previous candles to provide clean support
    and resistance levels.

    Note: The function relies on a helper function, `match_timeframe`, and assumes the existence of
    another helper function, `is_number_between`.

    :param symbol: Trading symbol for the financial instrument.
    :param timeframe: Timeframe for recent price data.
    :return: A dictionary with 'support' and 'resistance' levels.
    """

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
    
def is_number_between(number, lower_limit, upper_limit):
    if lower_limit > upper_limit:
        return lower_limit > number > upper_limit
    else:
        return lower_limit < number < upper_limit

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

def short_tf_mapping(timeframe):
    if timeframe == 240:
        return 60
    elif timeframe == 60:
        return 15
    else:
        raise Exception("TIMEFRAME for mapping is not defined")

def match_timeframe(timeframe):
    if timeframe == 1:
        selected_time = mt5.TIMEFRAME_M1
    elif timeframe == 5:
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
    elif timeframe == 480:
        selected_time = mt5.TIMEFRAME_H8
    elif timeframe == 1440:
        selected_time = mt5.TIMEFRAME_D1
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

def ema_direction(symbol, timeframes:list):
    directions = []
    for timeframe in timeframes:
        selected_time = match_timeframe(timeframe)

        # get 10 EURUSD H4 bars starting from 01.10.2020 in UTC time zone
        candle = mt5.copy_rates_from_pos(symbol, selected_time, 0, 9)
        candle_close = [i["close"] for i in candle]
        sma9  = np.average(candle_close)

        # Upper Time SMA
        upper_candle = mt5.copy_rates_from_pos(symbol, selected_time, 0, 21)
        upper_candle_close = [i["close"] for i in upper_candle]
        sma21  = np.average(upper_candle_close)

        if sma9 > sma21:
            directions.append("L")
        elif sma9 < sma21:
            directions.append("S")
    
    print(timeframes, directions)
    if len(timeframes) == len(directions):
        counter = collections.Counter(directions)
        optimal_direction = set(directions)
        if len(optimal_direction) == 1:
            return list(optimal_direction)[0]
        # elif len(directions) > 2:
        #     return counter.most_common()[0][0]


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
    """
    Retrieves and returns essential details of the trading account.

    This function fetches information such as balance, equity, margin-free funds,
    and profit from the MetaTrader 5 trading account. If the account information is
    successfully obtained, it returns a tuple containing these values.

    Returns:
        tuple: A tuple containing trading account details in the order of (balance, equity, margin_free, profit).
               Returns None if account information retrieval fails.
    """
     
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
    # print(mt5.TIMEFRAME_M15)
    # print(get_candle_signal("EURJPY"))
    # print(get_account_name())
    for symbol in get_ordered_symbols():
        print(symbol)
        # dict_values = support_resistance_levels(symbol, 60)
        # close_b = close_based_reversals(symbol, 60)
        # print(dict_values)
        # print(close_b)
        print(candle_based_trade(symbol, 60))
        print()
        
        # support = dict_values["support"]
        # resistance = dict_values["resistance"]
        # for sup in support:
        #     print(sup, understand_direction(symbol, 60, sup))
        
        # for res in resistance:
        #     print(res, understand_direction(symbol, 60, res))

    # print(close_based_reversals("EURNZD", 60))
    # print(ema_direction("AUDJPY", [240, 60, 30]))
    # print(understand_direction("AUDCHF", 60, 0.56882))