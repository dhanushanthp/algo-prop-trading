import MetaTrader5 as mt5
import indicators as ind
import util
import currency_pairs as curr
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
            return get_exchange_price("GBPUSD")
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

def get_value_at_risk_by_points(symbol, difference, positions):
    dollor_value = get_dollar_value(symbol)
    
    if symbol in curr.indexes:
        risk = difference * dollor_value * positions
    else:
        risk = difference * dollor_value * 100000 * positions
    return round(risk, 2)

def get_points_in_risk(symbol, lots, risk):
    dollor_value = get_dollar_value(symbol)
    
    if symbol in curr.indexes:
        points_in_risk =  risk/(dollor_value * lots)
    else:
        points_in_risk =  risk/(dollor_value * 100000 * lots)

    return points_in_risk

def stop_round(symbol, stop_price):
    if symbol in curr.currencies:
        if symbol in curr.jpy_currencies:
            return round(stop_price, 3)
        return round(stop_price, 5)
    else:
        return round(stop_price, 2)


def get_last_trades_position(symbol, current_trade_timeframe):
    """
    If you already have made some money. Then don't entry this for another 1 hour
    """

    tm_zone = pytz.timezone('Etc/GMT-2')
    start_time = datetime.combine(datetime.now(tm_zone).date(), time()).replace(tzinfo=tm_zone) - timedelta(hours=2)
    end_time = datetime.now(tm_zone) + timedelta(hours=4)

    exit_traded_position = [i for i in mt5.history_deals_get(start_time,  end_time) if i.symbol== symbol and i.entry==1]

    if len(exit_traded_position) > 0:
        last_traded_time = exit_traded_position[-1].time

        position_id = exit_traded_position[-1].position_id
        entry_traded_object = [i for i in mt5.history_deals_get(start_time,  end_time) if i.position_id == position_id and i.entry == 0]
        if len(entry_traded_object) > 0:
            # Wait until the last traded timeframe is complete
            timeframe = int(entry_traded_object[-1].magic)  # in minutes
            timeframe = max(timeframe, current_trade_timeframe) # Pick the max timeframe based on previous and current suggested trade timeframe
        else:
            timeframe = current_trade_timeframe

        current_time = (datetime.now(tm_zone) + timedelta(hours=2))

        current_time_epoch = current_time.timestamp()
        time_difference = (current_time_epoch - last_traded_time)/60

        if time_difference < timeframe:
            print(f"{symbol.ljust(12)}: Last/Current TF: {timeframe} > Wait Time {round(timeframe - time_difference)} Minutes!", end="")
            return False

    return True


def get_continues_wins():
    tm_zone = pytz.timezone('Etc/GMT-2')
    start_time = datetime.combine(datetime.now(tm_zone).date(), time()).replace(tzinfo=tm_zone)
    end_time = datetime.now(tm_zone) + timedelta(hours=4)
    traded_win_loss = [i.profit > 0 for i in mt5.history_deals_get(start_time,  end_time) if i.entry==1][-10:]
    traded_win_loss.reverse()
    
    # If last trade is win
    count_wins = 1

    if len(traded_win_loss) > 1:
        
        # If last one is loss then return 0 wins
        if not traded_win_loss[0]:
            return 0

        for i in range(len(traded_win_loss) - 1):
            if (traded_win_loss[i] == traded_win_loss[i+1]) and traded_win_loss[i]:
                count_wins += 1
            else:
                break
    
    return count_wins
    

def num_of_parallel_tickers():
        
    count_wins = get_continues_wins()
    if count_wins > 4:
        return count_wins
    
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


def exit_one_r():
    existing_positions = mt5.positions_get()
    for position in existing_positions:
        symbol = position.symbol
        entry_price = position.price_open
        stop_loss = position.sl
        quantity = position.volume
        max_loss = get_value_at_risk(symbol, entry_price, stop_loss, quantity)
        if (position.profit > max_loss * 0.9):
            close_single_position(position)


def adjust_positions_trailing_stops(risk):
    existing_positions = mt5.positions_get()
    for position in existing_positions:
        symbol = position.symbol
        stop_price = position.sl
        short_tf = int(position.comment.split("|")[-1])
        high, low, _ = ind.get_stop_range(symbol, short_tf)
        
        if position.type == 0:
            new_stop_point = util.curr_round(position.symbol, low)
            trail_stop = max(stop_price, new_stop_point)
        else:
            new_stop_point = util.curr_round(position.symbol, high)
            trail_stop = min(stop_price, new_stop_point)        

        # If the stop is already equal to existing stop, then no need to change it!
        # Enable trailning once price moved 1/4 of the stop, Otherswise this will keep adjust while the price is on
        # negative 
        if ((position.profit > risk/4) or (position.profit < -risk/2)) and trail_stop != stop_price:
            print(f"STP Updated: {position.symbol}, PRE: {round(stop_price, 5)}, CURR: {trail_stop}")

            modify_request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": position.type,
                "position": position.ticket,
                "sl": trail_stop,
                "tp": position.tp,
                "comment": position.comment,
                "magic": position.magic,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
                "ENUM_ORDER_STATE": mt5.ORDER_FILLING_RETURN,
            }
            
            result = mt5.order_send(modify_request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                if result.comment != "No changes":
                    print("Trailing STOP for " + position.symbol + " failed!!...Error: "+str(result.comment))

def trail_stop_half_points(risk):
    existing_positions = mt5.positions_get()
    for position in existing_positions:
        symbol = position.symbol
        stop_price = position.sl
        quantity = position.volume

        bid_price, ask_price = ind.get_bid_ask(symbol)
        
        total_points_in_risk = get_points_in_risk(symbol, quantity, risk)/2 # Trailning 0.5R
        
        if position.type == 0:
            new_stop_point = util.curr_round(position.symbol, (bid_price - total_points_in_risk))
            trail_stop = max(stop_price, new_stop_point)
        else:
            new_stop_point = util.curr_round(position.symbol, (ask_price + total_points_in_risk))
            trail_stop = min(stop_price, new_stop_point)

        # If the stop is already equal to existing stop, then no need to change it!
        # Enable trailning once price moved 1/4 of the stop
        if (position.profit > risk/4) and trail_stop != stop_price:
            print(f"STP Updated: {position.symbol}, PRE: {stop_price}, CURR: {trail_stop}")

            modify_request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": position.type,
                "position": position.ticket,
                "sl": trail_stop,
                "tp": position.tp,
                "comment": position.comment,
                "magic": position.magic,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
                "ENUM_ORDER_STATE": mt5.ORDER_FILLING_RETURN,
            }
            
            result = mt5.order_send(modify_request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                if result.comment != "No changes":
                    print("Trailing STOP for " + position.symbol + " failed!!...Error: "+str(result.comment))


def breakeven_1R_positions():
    existing_positions = mt5.positions_get()
    for position in existing_positions:
        symbol = position.symbol
        entry_price = position.price_open
        stop_loss = position.sl
        quantity = position.volume
        max_loss = get_value_at_risk(symbol, entry_price, stop_loss, quantity)
        if (position.profit > max_loss/4) and max_loss != 0:
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


def close_all_positions_on_exit():
    """
    This only closes the positions which has possible loss than 0. This is not heling out.
    """
    positions = mt5.positions_get()
    for obj in positions:
        symbol = obj.symbol
        stop_price = obj.sl
        entry_price = obj.price_open
        entry_type = obj.type

        if (entry_type == 0 and stop_price < entry_price) or (entry_type ==1 and stop_price > entry_price):
            close_single_position(obj=obj)
        

def exist_on_initial_plan_changed_ema():
    positions = mt5.positions_get()
    # Takeout all the positions regardless of Trail or Real If the inital plan is changed
    for obj in positions:
        # If the current position size is less than the half of the stop, Also once after the 1R hit, If the initial plan changed! exit!
        signal, sma = ind.is_ema_cross(obj.symbol, int(obj.comment))

        if signal:
            # when entry was Long but current signal is Short or if entry was short and the current signal is Long
            # 0 for long, 1 for short positions
            if (obj.type == 0 and signal == "S") or (obj.type == 1 and signal == "L"):
                close_single_position(obj)


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
    # print(num_of_parallel_tickers())
    # print(get_continues_wins())
    # print(exist_on_initial_plan_changed_ema())
    # print(get_last_trades_position("UK100.cash", 15))
    print(adjust_positions_trailing_stops(25))