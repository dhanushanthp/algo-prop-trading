from datetime import datetime, timedelta, time
import pytz
import MetaTrader5 as mt5
import pandas as pd
import sys

mt5.initialize()

def get_today_profit(file_name, start_date):
    tm_zone = pytz.timezone('Etc/GMT-2')
    start_time = datetime.combine(datetime(year=int(start_date[0:4]), month=int(start_date[4:6]), day=int(start_date[6:]), tzinfo=tm_zone) , time())  
    end_time = datetime.now(tm_zone) + timedelta(hours=4)
    data = mt5.history_deals_get(start_time, end_time)
    df=pd.DataFrame(list(data),columns=data[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.to_csv(f"data/history/{file_name}.csv", index=False)

if __name__ == "__main__":
    file_name = sys.argv[1]
    start_date = sys.argv[2]
    get_today_profit(file_name=f"{file_name}_{start_date}", start_date=start_date)