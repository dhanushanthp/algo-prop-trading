import MetaTrader5 as mt5
import indicators as ind
import currency_pairs as curr
import client
import numpy as np
import pytz
from datetime import datetime, timedelta, time
import config

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

def stop_round(symbol, stop_price):
    if symbol in curr.currencies:
        if symbol in curr.jpy_currencies:
            return round(stop_price, 3)
        return round(stop_price, 5)
    else:
        return round(stop_price, 2)

def num_of_parallel_tickers():
    tm_zone = pytz.timezone('Etc/GMT-2')
    start_time = datetime.combine(datetime.now(tm_zone).date(), time()).replace(tzinfo=tm_zone)
    end_time = datetime.now(tm_zone) + timedelta(hours=4)
    traded_win_loss = [i.profit > 0 for i in mt5.history_deals_get(start_time,  end_time) if i.entry==1][-10:]
    traded_win_loss.reverse()
    
    # If last trade is win
    if len(traded_win_loss) > 0:
        count_wins = 1
        for i in range(len(traded_win_loss)):
            if traded_win_loss[i] == traded_win_loss[i+1]:
                count_wins += 1
            else:
                break
        
        if count_wins < 4:
            return 4
        return count_wins
    else:
        # Default is one trade, To take more the algo should earn by winning more
        return 4
        

def get_recommended_strategy():
    tm_zone = pytz.timezone('Etc/GMT-2')
    start_time = datetime.combine(datetime.now(tm_zone).date(), time()).replace(tzinfo=tm_zone) - timedelta(hours=4)
    end_time = datetime.now(tm_zone) + timedelta(hours=4)
    
    # Get the last exit trade, Which will not have the "comment". So we need to find the entry for this one
    exit_objects = [i for i in mt5.history_deals_get(start_time,  end_time) if i.entry==1]
    
    # If it's a fresh then there won't be any existing orders. So we set default to reverse starategy
    if len(exit_objects) > 0:
        exit_object = exit_objects[-1]
        entry_object = [i for i in mt5.history_deals_get(start_time,  end_time) if i.entry==0 and i.position_id == exit_object.position_id][-1]
        
        previous_strategy = entry_object.comment
        previous_profit = exit_object.profit
        
        if previous_strategy != "":
            if previous_profit > 0:
                return config.TREND if previous_strategy == config.TREND else config.REVERSAL
            elif previous_profit < 0:
                return config.TREND if previous_strategy == config.REVERSAL else config.REVERSAL
    else:
        return config.REVERSAL


def get_symbol_entry_price(symbol):
    sym_positions = mt5.positions_get(symbol=symbol)
    if len(sym_positions) > 0:
        sym_position = sym_positions[0]
        stop_range = abs(sym_position.price_open - sym_position.sl)/ 2
        return sym_position.price_open, stop_range

    return None, None

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


def cancel_specific_pending_order(symbol):
    active_orders = mt5.orders_get()

    # Cancell all pending orders regadless of trial or real
    for active_order in active_orders:        
        if active_order.symbol == symbol:
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": active_order.ticket,
            }

            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"Failed to cancel order {active_order.ticket}, reason: {result.comment}")

def cancel_all_pending_orders():
    active_orders = mt5.orders_get()

    # Cancell all pending orders regadless of trial or real
    for active_order in active_orders:
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": active_order.ticket,
        }

        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Failed to cancel order {active_order.ticket}, reason: {result.comment}")

def breakeven_1R_positions():
    existing_positions = mt5.positions_get()
    for position in existing_positions:
        symbol = position.symbol
        entry_price = position.price_open
        stop_loss = position.sl
        quantity = position.volume
        max_loss = get_value_at_risk(symbol, entry_price, stop_loss, quantity)
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

def close_single_position(obj):        
    order_type = mt5.ORDER_TYPE_BUY if obj.type == 1 else mt5.ORDER_TYPE_SELL
    exist_price = mt5.symbol_info_tick(obj.symbol).bid if obj.type == 1 else mt5.symbol_info_tick(obj.symbol).ask
    
    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": obj.symbol,
        "volume": obj.volume,
        "type": order_type,
        "position": obj.ticket,
        "price": exist_price,
        "deviation": 20,
        "magic": 234000,
        "comment": 'close_trail_version',
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC, # also tried with ORDER_FILLING_RETURN
    }
    
    result = mt5.order_send(close_request) # send order to close a position
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print("Close Order "+obj.symbol+" failed!!...comment Code: "+str(result.comment))

def close_all_positions():
    positions = mt5.positions_get()
    for obj in positions: 
        close_single_position(obj=obj)
        

def close_slave_positions():
    """
    If the positions is already filled in master, then no need for slave position in local
    """
    existing_positions = list(set([i.symbol for i in mt5.positions_get()]))
    server_positions = client.get_active_positions()
    co_exisiting_positions = np.intersect1d(existing_positions, server_positions)
    if len(co_exisiting_positions) > 0:
        for obj in mt5.positions_get():
            if obj.symbol in co_exisiting_positions:
                close_single_position(obj=obj)
    
def exist_on_initial_plan_changed():
    positions = mt5.positions_get()
    # Takeout all the positions regardless of Trail or Real If the inital plan is changed
    for obj in positions:
        # If the current position size is less than the half of the stop, Also once after the 1R hit, If the initial plan changed! exit!
        if (obj.profit < 0):
            signal = ind.get_candle_signal(obj.symbol, verb=False)
                
            if signal:                
                # when entry was Long but current signal is Short or if entry was short and the current signal is Long
                # 0 for long, 1 for short positions
                if (obj.type == 0 and signal == "S") or (obj.type == 1 and signal == "L"):
                    close_single_position(obj)

if __name__ == "__main__":
    # breakeven_1R_positions()
    # print(get_dollar_value("GBPJPY"))
    # print(get_exchange_price("NZDUSD"))
    # print(strategy_selector())
    print(num_of_parallel_tickers())