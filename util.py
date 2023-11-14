from datetime import datetime
import pytz

import MetaTrader5 as mt5
mt5.initialize()

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

def get_gmt_time():
    tm_zone = pytz.timezone('Etc/GMT-2')
    local_time = datetime.now(tm_zone)
    day_of_week = local_time.strftime('%A')
    hour = int(local_time.strftime('%H'))
    minute = int(local_time.strftime('%M'))
    return day_of_week, hour, minute


def get_market_status():
    market_open = False
    market_about_to_close= False
    day, hour, minut = get_gmt_time()
    print(day, hour, minut)

    if day not in ["Saturday","Sunday"]:
        # Once market open become disabled, No new trades
        if hour >= 0 and minut > 10 and hour < 21:
            market_open = True
    
    if (day in ["Saturday","Sunday"]) or hour >= 21:
        market_about_to_close = True

    return market_open, market_about_to_close

# # Get and print the local time (including day of the week) for each city
# cities = ['New York', 'London', 'Tokyo', 'Sydney']
# for city in cities:
#     local_time = get_local_time(city)
#     print(local_time)

def is_c_pair_active(currency_pair):
    symbol_info=mt5.symbol_info(currency_pair)
    mt5.symbol_select(currency_pair, True)
    if symbol_info:
        return symbol_info.session_open, symbol_info.session_close
    
# print(is_c_pair_active("US500.cash"))   

print(get_market_status())