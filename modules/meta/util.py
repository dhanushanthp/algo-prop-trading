from datetime import datetime, timedelta,  time
import pytz

import MetaTrader5 as mt5
mt5.initialize()
import modules.meta.Currencies as curr
import modules.config as config
from typing import Tuple
import pandas as pd
from termcolor import colored
from colorama import init
init()

def error_logging(result, request_str={}) -> bool:
    if result:
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_string = f"{result.comment}"
            print(error_string)

            if result.comment in ["Invalid volume", "Invalid price"]:
                return False
            return True
    return True
            # self.alert.send_msg(f"ERR: {self.account_name} <br> {error_string} <br> ```{request_str}```")

def get_last_sunday():
    today = get_current_time()
    # Calculate the number of days to subtract to reach the last Sunday
    days_to_subtract = today.weekday() + 1  # Adding 1 to include the current day
    # Subtract days to get to the last Sunday
    last_sunday_date = today - timedelta(days=days_to_subtract)
    return last_sunday_date

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
        raise Exception(f"TIMEFRAME FOR PREVIOUS CANDLE NOT DEFINED: {timeframe}")
    return selected_time

def get_local_time(city) -> Tuple[int, int, int]:
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


def get_str_date_object(date_str:str):
    # Convert the string to a datetime object
    date_str = date_str.split(" ")[-1]
    date_str = date_str.split(":")
    hour = int(date_str[0])
    min = int(date_str[1])
    return hour, min


def find_trade_time_gap(date_str:str):
    signal_hour, signal_min = get_str_date_object(date_str=date_str)
    _, hour, min = get_current_day_hour_min()
    time_gap = (hour * 60 + min) - (signal_hour*60 + signal_min)
    return time_gap


def get_traded_time(epoch)-> datetime:
    """
    Converts an epoch timestamp to a timezone-aware datetime object in the 'Etc/GMT' timezone.

    Args:
        epoch (int): The epoch timestamp to be converted.

    Returns:
        datetime: The corresponding timezone-aware datetime object in the 'Etc/GMT' timezone.

    Example:
        >>> epoch = 1655560800
        >>> get_traded_time(epoch)
        datetime.datetime(2022, 6, 18, 0, 0, tzinfo=<StaticTzInfo 'Etc/GMT'>)

    Notes:
        - This function uses the 'Etc/GMT' timezone for conversion, which is equivalent to UTC with no offset.
        - The function requires the `pytz` library for timezone handling.
        - Ensure that the input `epoch` is a valid integer representing the number of seconds since the Unix epoch (00:00:00 UTC on 1 January 1970).

    Raises:
        TypeError: If the input `epoch` is not an integer.
        ValueError: If the input `epoch` is not a valid epoch timestamp.

    """
    normal_time = datetime.fromtimestamp(epoch, pytz.timezone('Etc/GMT'))
    return normal_time

def get_account_name():
    info = mt5.account_info()
    balance = round(info.balance/1000)
    return f"{info.name} {balance}K "

def get_server_ip():
    return config.local_ip

def get_us_time()-> datetime:
    current_time =  datetime.now(pytz.timezone("US/Eastern"))
    return current_time

def get_us_hour_min() -> Tuple[int, int]:
    current_time = get_us_time()
    hour = int(current_time.strftime("%H"))
    minute = int(current_time.strftime("%M"))
    return hour, minute

def get_current_time() -> datetime:
    current_time =  datetime.now(pytz.timezone(f'Etc/GMT-{config.server_timezone}'))
    return current_time

def get_week_day() -> int:
    """
    Get the weekday (0 = Monday, 6 = Sunday)
    """
    week_day = get_current_time().weekday()
    return week_day

def get_current_gmt_time() -> datetime:
    current_time =  datetime.now(pytz.timezone('Etc/GMT'))
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

def get_current_day_hour_min() -> Tuple[int, int, int]:
    """
    Returns Day Of Week, Hour, Minute
    This calls the current time with GMT offset
    """
    local_time = get_current_time()
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

def index_of_active_bar(symbol:str, timeframe:int) -> int:
    """
    Count the bars in a days
    """
    server_date = get_current_time()

    # Generate off market hours high and lows
    start_time = datetime(int(server_date.year), int(server_date.month), int(server_date.day), 
                            hour=0, minute=0, tzinfo=pytz.timezone('Etc/GMT'))
    
    previous_bars = mt5.copy_rates_range(symbol, 
                                         match_timeframe(timeframe=timeframe), 
                                         start_time, 
                                         server_date + timedelta(hours=config.server_timezone))

    if previous_bars is not None:
        return len(list(previous_bars)) - 1
    
    return 0

def is_us_premarket_peroid() -> bool:
    """
    Check is this US premarket hour
    Exit any trade or no new trades between 8AM and 930AM US time to avoid the high volatile moves
    """
    us_hour, _ = get_us_hour_min()
    condition = (us_hour >= 8) and (us_hour < 16)
    return condition

def is_us_activemarket_peroid() -> bool:
    """
    Check is this US premarket hour
    Exit any trade or no new trades between 8AM and 930AM US time to avoid the high volatile moves
    """
    us_hour, us_min = get_us_hour_min()
    condition = (us_hour > 9 or (us_hour == 9 and us_min >= 36)) and us_hour < 16
    return condition 

def get_market_status(start_hour:int=10, start_minute:int=0) -> Tuple[bool, bool]:
    """
    Determine the market status based on the current day and time.
    Args:
        start_hour (int): The hour at which the market opens. Defaults to 10.
        start_minute (int): The minute at which the market opens. Defaults to 0.
    Returns:
        Tuple[bool, bool]: A tuple containing two boolean values:
            - market_open (bool): True if the market is open, False otherwise.
            - market_about_to_close (bool): True if the market is about to close, False otherwise.
    Notes:
        - The market is considered open from `start_hour` to 22:00 on weekdays.
        - Added minutes to avoid the market volatility
        - The market is considered about to close if:
            - It is a weekend (Saturday or Sunday).
            - It is 23:15 or later.
            - It is before 01:00.
    """
    market_open = False
    market_about_to_close= False
    day, hour, minute = get_current_day_hour_min()

    if day not in ["Saturday","Sunday"]:
        # Once market open become disabled, No new trades
        # We give first 1 hour and last 1 hour as non-trading time
        if (((hour >= start_hour and minute >= start_minute) 
             or (hour > start_hour)
             ) and hour < 22):
            market_open = True
    
    # Close all the position 30 minute before the market close
    # Closed on weekends
    # Or Just 45 minutes before the market close
    # Or just 1 hour before the market open -> this will help usto reset the today's closed positions PnL
    # Also it's best to avoid first 1 hour, since the spread is very high
    if (day in ["Saturday","Sunday"]) or (hour >= 23 and minute >= 15) or (hour < 1):
        market_about_to_close = True

    return market_open, market_about_to_close

def cl(status):
    if status:
        return colored(status, 'green')
    else:
        return colored(status, 'red')

def cl_status(status, color):
    return colored(status, color)

def is_c_pair_active(currency_pair):
    symbol_info=mt5.symbol_info(currency_pair)
    mt5.symbol_select(currency_pair, True)
    if symbol_info:
        return symbol_info.session_open, symbol_info.session_close

def get_maket_events() -> dict:
    today = get_current_time().strftime("%Y-%m-%d")
    data = pd.read_csv("data/market_data.csv")
    today_events = data[data["date"] == today]
    today_events = today_events.groupby(["hour"])["symbol"].agg(list).reset_index()
    mapping = dict(zip(today_events["hour"], today_events["symbol"]))
    return mapping

if __name__ == "__main__":
    import sys
    # symbol = sys.argv[1]
    # timeframe = int(sys.argv[2])
    # print(is_c_pair_active("US500.cash"))   
    # print(get_gmt_time())
    # print(get_market_status())
    # print(get_today_profit())
    # print(index_of_active_bar(symbol, timeframe))
    curr_date = get_current_day_hour_min()
    print(curr_date)
    given_time = get_str_date_object(date_str="2024-09-30 00:50:17")
    print(given_time)
    print(find_trade_time_gap(date_str="2024-09-30 00:50:17"))

    # print(get_current_day_hour_min())
    # print(is_us_premarket_peroid())
    # print(get_maket_events())
    # print(get_last_sunday())