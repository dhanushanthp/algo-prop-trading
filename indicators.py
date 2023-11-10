from datetime import datetime,  timedelta
import MetaTrader5 as mt5
import pytz
import numpy as np

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()
 

def get_atr(symbol):
    # set time zone to UTC
    timezone = pytz.timezone("Etc/UTC")
    # create 'datetime' object in UTC time zone to avoid the implementation of a local time zone offset
    # utc_from = datetime(2023, 11, 7, tzinfo=timezone)

    # Get the current date and time in the desired time zone
    current_datetime = datetime.now(timezone)

    # Calculate two days before the current date and time
    utc_from = current_datetime - timedelta(days=3)


    # get 10 EURUSD H4 bars starting from 01.10.2020 in UTC time zone
    rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_H4, utc_from, 100)

    # Extract high, low, and close prices
    high = np.array([x['high'] for x in rates])
    low = np.array([x['low'] for x in rates])
    close = np.array([x['close'] for x in rates])


    # Calculate true range
    true_range = np.maximum(high[1:] - low[1:], abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1]))

    # Calculate 14-period ATR
    atr = np.mean(true_range[-14:])

    return round(atr, 5)

# print(get_atr("AUS200.cash"))

def get_spread(symbol):
    ask_price = mt5.symbol_info_tick(symbol).ask
    bid_price = mt5.symbol_info_tick(symbol).bid
    spread = ask_price - bid_price
    return spread * 2

def get_last_candle_direction(symbol):
    timezone = pytz.timezone("Etc/UTC")
    current_datetime = datetime.now(timezone)

    # Calculate two days before the current date and time
    utc_from = current_datetime - timedelta(days=1)

    print(symbol)

    # get 10 EURUSD H4 bars starting from 01.10.2020 in UTC time zone
    h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 1)[0]
    h4_sig=  "long" if h4[4] - h4[1] > get_spread(symbol) else "short" if abs(h4[4] - h4[1]) > get_spread(symbol) else None
    h2 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H2, 0, 1)[0]
    h2_sig=  "long" if h2[4] - h2[1] > get_spread(symbol) else "short" if abs(h2[4] - h2[1]) > get_spread(symbol) else None
    h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1)[0]
    h1_sig=  "long" if h1[4] - h1[1] > get_spread(symbol) else "short" if abs(h1[4] - h1[1]) > get_spread(symbol) else None
    m30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 1)[0]
    m30_sig=  "long" if m30[4] - m30[1] > get_spread(symbol) else "short" if abs(m30[4] - m30[1]) > get_spread(symbol) else None
    m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 1)[0]
    m15_sig=  "long" if m15[4] - m15[1] > get_spread(symbol) else "short" if abs(m15[4] - m15[1]) > get_spread(symbol) else None
    m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 1)[0]
    m5_sig=  "short" if m5[4] - m5[1] > get_spread(symbol) else "long" if abs(m5[4] - m5[1]) > get_spread(symbol) else None

    signals = [m30_sig, h1_sig, h2_sig, h4_sig]
    print(signals)
    
    signals = set(signals)
    if len(signals) == 1:
        return list(signals)[0]

def get_remaining_margin():
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
            return 1.6 * get_exchange_price("AUDUSD")
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
    

