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
    return spread * 2

def get_candle_signal(symbol):
    # get 10 EURUSD H4 bars starting from 01.10.2020 in UTC time zone
    h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 1)[0]
    h4_sig=  "L" if h4[4] - h4[1] > get_spread(symbol) else "S" if abs(h4[4] - h4[1]) > get_spread(symbol) else "X"
    h2 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H2, 0, 1)[0]
    h2_sig=  "L" if h2[4] - h2[1] > get_spread(symbol) else "S" if abs(h2[4] - h2[1]) > get_spread(symbol) else "X"
    h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1)[0]
    h1_sig=  "L" if h1[4] - h1[1] > get_spread(symbol) else "S" if abs(h1[4] - h1[1]) > get_spread(symbol) else "X"
    m30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 1)[0]
    m30_sig=  "L" if m30[4] - m30[1] > get_spread(symbol) else "S" if abs(m30[4] - m30[1]) > get_spread(symbol) else "X"

    signals = [m30_sig, h1_sig, h2_sig, h4_sig]
    print(f"{symbol.ljust(12)}: 30M: {m30_sig.upper()}, 1H: {h1_sig.upper()}, 2H: {h2_sig.upper()}, 4H: {h4_sig.upper()}")
    
    signals = set(signals)
    if len(signals) == 1:
        return list(signals)[0]

def get_account_details():
    account_info=mt5.account_info()
    if account_info!=None:
        # display trading account data 'as is'
        return account_info.equity, account_info.margin_free

def get_exchange_price(symbol):
    ask_price = mt5.symbol_info_tick(symbol).ask
    bid_price = mt5.symbol_info_tick(symbol).bid
    exchange_rate = round((bid_price + ask_price)/2, 4)
    return exchange_rate

def get_dollar_value(symbol):
        # Check which radio button is selected
        if symbol == "US500.cash":
            return 1
        elif symbol == "UK100.cash":
            dollor_value = round(1/get_exchange_price("GBPUSD"), 4)
        elif symbol == "HK50.cash":
            return round(1/get_exchange_price("USDHKD"), 4)
        elif symbol == "JP225.cash":
            return round(1/get_exchange_price("USDJPY"), 4)
        elif symbol == "AUS200.cash":
            return get_exchange_price("AUDUSD")
        elif symbol == "US100.cash":
            return 1
        elif symbol == "AUDNZD":
            return (1/get_exchange_price("AUDNZD")) * get_exchange_price("AUDUSD")
        elif symbol == "USDJPY":
            return 1/get_exchange_price("USDJPY")
        elif symbol == "USDCHF":
            return 1/get_exchange_price("USDCHF")
        elif symbol == "AUDJPY":
            return (1/get_exchange_price("AUDJPY")) * get_exchange_price("AUDUSD")
        elif symbol == "XAUUSD":
            return 2/get_exchange_price("XAUUSD")
        elif symbol == "EURUSD":
            return get_exchange_price("EURUSD")
        elif symbol == "USDCAD":
            return  1/get_exchange_price("USDCAD")
        elif symbol == "AUDUSD":
            return 1.6 * get_exchange_price("AUDUSD") # TODO, This fix number 1.6 has to be changed!
        elif symbol == "GBPUSD":
            return get_exchange_price("GBPUSD")

def get_value_at_risk(symbol, price_open, stop, positions):
    difference = abs(price_open - stop)
    dollor_value = get_dollar_value(symbol)
    
    if symbol in ["AUS200.cash", "US500.cash"]:
        risk = difference * dollor_value * positions
    else:
        print(difference, dollor_value, positions)
        risk = difference * dollor_value * 100000 * positions
    return risk

def close_positions(obj):
    # Get open positions

    if obj.type == 1: # if order type is a buy, to close we have to sell
        order_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(obj.symbol).bid
    else:                   # otherwise, if order type is a sell, to close we have to buy
        order_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(obj.symbol).ask
    
    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": obj.symbol,
        "volume": obj.volume,
        "type": order_type,
        "position": obj.ticket,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": 'Close trade',
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC, # also tried with ORDER_FILLING_RETURN
    }
    
    result = mt5.order_send(close_request) # send order to close a position
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print("Close Order "+obj.symbol+" failed!!...Error Code: "+str(result.retcode))
    else:
        print("Order "+obj.symbol+" closed successfully")

            
def close_positions_with_half_profit():
    existing_positions = mt5.positions_get()
    for position in existing_positions:
        symbol = position.symbol
        entry_price = position.price_open
        stop_price = position.tp
        quantity = position.volume
        max_profit = get_value_at_risk(symbol, entry_price, stop_price, quantity)
        print("Max Profit", round(max_profit), "Pos Po", position.profit)
        if position.profit > 0.5 * max_profit:
            close_positions(position)

# print(get_remaining_margin())
# close_positions_with_half_profit()
# print(get_atr("US500.cash"))
print(previous_candle_move("AUDUSD"))