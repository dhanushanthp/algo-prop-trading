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
    }

    # Get the current UTC time
    utc_now = datetime.utcnow()

    # Use pytz to convert the UTC time to the local time of the specified city
    local_time = utc_now.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(timezones[city]))

    day_of_week = local_time.strftime('%A')
    hour = int(local_time.strftime('%H'))
    
    return day_of_week, hour

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
    
print(is_c_pair_active("US500.cash"))   