import MetaTrader5 as mt5
import indicators as ind
import currency_pairs as curr

# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

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
            return round(1/get_exchange_price("GBPUSD"), 4)
        elif symbol == "HK50.cash":
            return round(1/get_exchange_price("USDHKD"), 4)
        elif symbol == "JP225.cash":
            return round(1/get_exchange_price("USDJPY"), 4)
        elif symbol == "AUS200.cash":
            return get_exchange_price("AUDUSD")
        elif symbol == "AUDNZD":
            return (1/get_exchange_price("AUDNZD")) * get_exchange_price("AUDUSD")
        elif symbol == "USDJPY":
            return 1/get_exchange_price("USDJPY")
        elif symbol == "USDCHF":
            return 1/get_exchange_price("USDCHF")
        elif symbol == "AUDJPY":
            return (1/get_exchange_price("AUDJPY")) * get_exchange_price("AUDUSD")
        elif symbol == "NZDJPY":
            return (1/get_exchange_price("NZDJPY")) * get_exchange_price("NZDUSD")
        elif symbol == "EURJPY":
            return (1/get_exchange_price("EURJPY")) * get_exchange_price("EURUSD")
        elif symbol == "GBPJPY":
            return (1/get_exchange_price("GBPJPY")) * get_exchange_price("GBPUSD")
        elif symbol == "EURCAD":
            return (1/get_exchange_price("EURCAD")) * get_exchange_price("EURUSD")
        elif symbol == "NZDCAD":
            return (1/get_exchange_price("NZDCAD")) * get_exchange_price("NZDUSD")
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
        elif symbol == "EURNZD":
            return (1/get_exchange_price("EURNZD")) * get_exchange_price("EURUSD")
        elif symbol == "CHFJPY":
            return 1/get_exchange_price("CHFJPY")/ get_exchange_price("USDCHF")
        else:
            raise Exception("Currency Pair No defined in manage_positions.py")

def get_value_at_risk(symbol, price_open, stop, positions):
    difference = abs(price_open - stop)
    dollor_value = get_dollar_value(symbol)
    
    if symbol in curr.indexes:
        risk = difference * dollor_value * positions
    else:
        risk = difference * dollor_value * 100000 * positions
    return round(risk, 2)

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

def stop_round(symbol, stop_price):
    if symbol in curr.currencies:
        if symbol in curr.jpy_currencies:
            return round(stop_price, 3)
        return round(stop_price, 5)
    else:
        return round(stop_price, 2)

def breakeven_1R_positions_old():
    existing_positions = mt5.positions_get()
    for position in existing_positions:
        symbol = position.symbol
        entry_price = position.price_open
        stop_loss = position.sl
        quantity = position.volume
        max_loss = get_value_at_risk(symbol, entry_price, stop_loss, quantity)
        # Break even when price reach 1R
        # if position.symbol != "GBPUSD":
        #     continue

        high, low, length = ind.previous_candle_move(symbol=position.symbol)
        stop_price = 0
        if position.type == 0:
            stop_price = low
        elif position.type == 1:
            stop_price = high
        
        stop_price = stop_round(symbol=position.symbol, stop_price=stop_price)

        actual_stop_pips = abs(position.tp - position.price_open)
        current_stop_pips = abs(stop_price - position.price_open)

        # Only when the stop price is not set to previous bar. Otherwise the 
        # stop has been already moved.
        # Don't change when 1. existing stop price equals to new calculated stop and 2. If new stop pips is higher than initial pips
        # round(stop_price, 3) != round(position.sl, 3)
        if (actual_stop_pips > current_stop_pips):
            modify_request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": position.type,
                "position": position.ticket,
                "sl": stop_price,
                "tp": position.tp,
                "comment": 'Break Even',
                "magic": 234000,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
                "ENUM_ORDER_STATE": mt5.ORDER_FILLING_RETURN,
            }
            
            result = mt5.order_send(modify_request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                if result.comment not in ["No changes"]:
                    print("Manage Order " + position.symbol + " failed!!...Error: "+str(result.comment))

def breakeven_1R_positions():
    existing_positions = mt5.positions_get()
    for position in existing_positions:
        symbol = position.symbol
        entry_price = position.price_open
        stop_loss = position.sl
        quantity = position.volume
        max_loss = get_value_at_risk(symbol, entry_price, stop_loss, quantity)
        # print(position.symbol, max_loss/2, position.profit)
        if (position.profit > max_loss) and max_loss != 0:
            modify_request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": position.type,
                "position": position.ticket,
                "sl": position.price_open,
                "tp": position.tp,
                "comment": 'break_even',
                "magic": 234000,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
                "ENUM_ORDER_STATE": mt5.ORDER_FILLING_RETURN,
            }
            
            result = mt5.order_send(modify_request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                if result.comment != "No changes":
                    print("Modify Order " + position.symbol + " failed!!...Error: "+str(result.comment))

# breakeven_1R_positions()
# print(get_dollar_value("GBPJPY"))
# print(get_exchange_price("NZDUSD"))