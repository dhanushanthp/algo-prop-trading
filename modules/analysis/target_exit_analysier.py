from glob import glob
import pandas as pd
from tqdm import tqdm

def calculate_slope(x1, y1, x2, y2):
    """
    Calculate the slope between two points (x1, y1) and (x2, y2).
    
    Parameters:
    x1 (float): x-coordinate of the first point
    y1 (float): y-coordinate of the first point
    x2 (float): x-coordinate of the second point
    y2 (float): y-coordinate of the second point
    
    Returns:
    float: Slope between the two points
    """
    if x1 == x2:
        raise ValueError("The slope is undefined for vertical lines (x1 cannot be equal to x2).")
    
    return (y2 - y1) / (x2 - x1)

def generate_insights(file_name):
    data = pd.read_csv(file_name, names=["iteration", "system", "strategy", "time", "pnl", "rr", "risk_per_trade"])
    data["time"] = pd.to_datetime(data["time"])
    data.set_index('time', inplace=True)
    
    data['1h_moving_avg_rr'] = data['rr'].rolling('1h').mean()
    data['15m_moving_avg_rr'] = data['rr'].rolling('15min').mean()
    
    data['1h_moving_avg_pnl'] = data['pnl'].rolling('1h').mean()
    data['15m_moving_avg_pnl'] = data['pnl'].rolling('15min').mean()
    
    data = data.reset_index()
    
    data["time_in_15minute"] = data["time"].dt.round('15min')
    data["time_in_hour"] = data["time"].dt.round('1h')
    
    # Change in every 1 hour
    hour_agg = data.groupby("time_in_hour")["1h_moving_avg_rr"].mean().reset_index(name="each_hour_rr_change")
    hour_agg["change_in_hour"] = hour_agg["each_hour_rr_change"].diff()
    hour_agg["change_in_hour"] = hour_agg["change_in_hour"].fillna(0)
    hour_agg = hour_agg[["time_in_hour", "change_in_hour"]].copy()
    
    # Change in every 1 hour
    min15_agg = data.groupby("time_in_15minute")["15m_moving_avg_rr"].mean().reset_index(name="each_15min_rr_change")
    min15_agg["change_in_15min"] = min15_agg["each_15min_rr_change"].diff()
    min15_agg["change_in_15min"] = min15_agg["change_in_15min"].fillna(0)
    min15_agg = min15_agg[["time_in_15minute", "change_in_15min"]].copy()
    
    data = data.merge(hour_agg, on="time_in_hour")
    data = data.merge(min15_agg, on="time_in_15minute")

    data["hour_vs_15min_change_difference"] = data["change_in_hour"] - data["change_in_15min"]

    # Generate slope
    hour_agg = data.groupby("time_in_hour")["1h_moving_avg_rr"].first().reset_index()
    hour_agg = hour_agg.reset_index()
    hour_agg["shift_1_index"] = hour_agg["index"].shift(-1)
    hour_agg["shift_2_index"] = hour_agg["index"].shift(-2)
    hour_agg["shift_4_index"] = hour_agg["index"].shift(-4)

    hour_agg["shift_1_1h_moving_avg_rr"] = hour_agg["1h_moving_avg_rr"].shift(-1)
    hour_agg["shift_2_1h_moving_avg_rr"] = hour_agg["1h_moving_avg_rr"].shift(-2)
    hour_agg["shift_4_1h_moving_avg_rr"] = hour_agg["1h_moving_avg_rr"].shift(-4)

    hour_agg["shope_1_shift"] = hour_agg.apply(lambda x: calculate_slope(x["index"], x["1h_moving_avg_rr"], x["shift_1_index"], x["shift_1_1h_moving_avg_rr"]) , axis=1)
    hour_agg["shope_2_shift"] = hour_agg.apply(lambda x: calculate_slope(x["index"], x["1h_moving_avg_rr"], x["shift_2_index"], x["shift_2_1h_moving_avg_rr"]) , axis=1)
    hour_agg["shope_4_shift"] = hour_agg.apply(lambda x: calculate_slope(x["index"], x["1h_moving_avg_rr"], x["shift_4_index"], x["shift_4_1h_moving_avg_rr"]) , axis=1)

    hour_agg = hour_agg[["time_in_hour", "shope_1_shift", "shope_2_shift", "shope_4_shift"]].drop_duplicates()

    data = data.merge(hour_agg, on="time_in_hour", how="left")

    return data

directory = "C:\\Users\\DHANUSHANTHPUSHPARAJ\\OneDrive\\Financial Freedom\\Phoenix\\data\\pnl\\10_1_0_4\\*"
files = glob(directory)

for file_name in tqdm(files):
    data = generate_insights(file_name=file_name)
    data.to_csv(file_name.replace("pnl", "pnl_enchanced"), index=False)
