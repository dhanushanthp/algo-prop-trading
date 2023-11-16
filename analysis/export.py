from datetime import datetime, timedelta, time
import pytz
import MetaTrader5 as mt5
import pandas as pd

mt5.initialize()

def get_today_profit():
    tm_zone = pytz.timezone('Etc/GMT-2')
    start_time = datetime.combine(datetime.now(tm_zone).date(), time())  
    end_time = datetime.now(tm_zone) + timedelta(hours=4)
    data = mt5.history_deals_get(start_time, end_time)
    df=pd.DataFrame(list(data),columns=data[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.to_csv(f"trades_{datetime.now(tm_zone).date()}.csv", index=False)

if __name__ == "__main__":
    get_today_profit()