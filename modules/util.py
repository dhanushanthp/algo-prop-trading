from datetime import datetime, timedelta,  time
import pytz

import MetaTrader5 as mt5
mt5.initialize()
import modules.currency_pairs as curr
import modules.config as config

def get_local_time(city):
    # Create a dictionary to map cities to their respective time zones
    timezones = {
        'New York': 'America/New_York',
        'London': 'Europe/London',
        'Tokyo': 'Asia/Tokyo',
        'Sydney': 'Australia/Sydney',
        'Berlin':'Europe/Berlin'
    }

    # Get the current UTC time
    utc_now = datetime.utcnow()

    # Use pytz to convert the UTC time to the local time of the specified city
    local_time = utc_now.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(timezones[city]))

    day_of_week = local_time.strftime('%A')
    hour = int(local_time.strftime('%H'))
    minute = int(local_time.strftime('%M'))
    
    return day_of_week, hour, minute

def get_traded_time(epoch):
    normal_time = datetime.fromtimestamp(epoch, pytz.timezone('Etc/GMT'))
    return normal_time

def get_current_time():
    current_time =  datetime.now(pytz.timezone(f'Etc/GMT-{config.server_timezone}'))
    return current_time

def get_time_difference(epoch):
    traded_time = get_traded_time(epoch)
    traded_hour = traded_time.hour
    traded_minute = traded_time.minute + (traded_hour * 60)
    current_time = get_current_time()
    current_hour = current_time.hour
    current_minute = current_time.minute + (60 * current_hour)
    difference = round(current_minute - traded_minute)
    return difference

def boolean(input):
    if input == "yes" or input == "True" or input == "true":
        return True

    return False

def get_gmt_time():
    tm_zone = pytz.timezone(f'Etc/GMT-{config.server_timezone}')
    local_time = datetime.now(tm_zone)
    day_of_week = local_time.strftime('%A')
    hour = int(local_time.strftime('%H'))
    minute = int(local_time.strftime('%M'))
    return day_of_week, hour, minute

def curr_round(symbol, price):
    round_factor = 5 if symbol in curr.currencies else 2
    round_factor = 2 if symbol == "XAUUSD" else round_factor
    round_factor = 3 if symbol in curr.jpy_currencies else round_factor
    return round(price, round_factor)

def get_today_profit():
    tm_zone = pytz.timezone('Etc/GMT-2')
    start_time = datetime.combine(datetime.now(tm_zone).date(), time()).replace(tzinfo=tm_zone)
    end_time = datetime.now(tm_zone) + timedelta(hours=4)
    data = mt5.history_deals_get(start_time, end_time)
    output = round(sum([i.profit + i.commission for i in data]))
    return output

def get_market_status():
    market_open = False
    market_about_to_close= False
    day, hour, minute = get_gmt_time()
    print(f"{'Day & Time'.ljust(20)}: {day}: {str(hour).zfill(2)}:{str(minute).zfill(2)}")

    if day not in ["Saturday","Sunday"]:
        # Once market open become disabled, No new trades
        # We give first 1 hour and last 1 hour as non-trading time
        if (hour >= 1 and hour <= 22):
            market_open = True
    
    # Close all the position 30 minute before the market close
    if (day in ["Saturday","Sunday"]) or (hour >= 23 and minute >= 15):
        market_about_to_close = True

    return market_open, market_about_to_close


def is_c_pair_active(currency_pair):
    symbol_info=mt5.symbol_info(currency_pair)
    mt5.symbol_select(currency_pair, True)
    if symbol_info:
        return symbol_info.session_open, symbol_info.session_close

if __name__ == "__main__":
    # print(is_c_pair_active("US500.cash"))   
    # print(get_gmt_time())
    print(get_market_status())
    print(get_today_profit())