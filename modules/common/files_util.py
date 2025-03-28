import pandas as pd
from datetime import datetime
import os
from modules.meta import util
from glob import glob
from modules import config

def check_file_exists(file_path):
    if os.path.isfile(file_path):
        return True
    else:
        return False

def create_directory_if_not_exists(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def get_previous_pnl_direction():
    """
    Retrieves the most recent profit and loss (PnL) and strategy information 
    from a trade tracker CSV file specific to the server's IP.

    The function reads the last entry in a CSV file named 
    `trade_tracker_<server_ip>.csv` located in the `data/` directory. 
    The server IP is determined dynamically using the `util.get_server_ip()` function.
    It extracts the PnL and strategy from the last record in the file.

    Returns:
        tuple: A tuple containing:
            - pnl (float): The profit and loss value from the last trade record.
            - strategy (str): The trading strategy used for the last trade.
    """
    file_name = f"data/trade_tracker_{util.get_server_ip()}.csv"
    data = pd.read_csv(file_name)
    data = data.iloc[-1]
    pnl = data["pnl"]
    strategy = data["strategy"]
    return pnl, strategy

@DeprecationWarning
def update_pnl(file_name:str, system:str, strategy:str, pnl:float, rr:float, each_pos_percentage:float):
    """
    Updates the profit and loss (PnL) tracker with the provided data.

    Parameters:
        file_name (str): name of the file
        pnl (float): The profit or loss value to be recorded.
        rr (float): The risk-reward ratio associated with the trade.
        each_pos_percentage (float): The percentage of risk for each position.

    Returns:
        None

    This function reads the existing trade tracker data from 'trade_tracker.csv', 
    appends a new row with the current date, pnl, rr, and each_pos_percentage values, 
    and writes the updated data back to 'trade_tracker.csv'.
    """
    file_name = f"data/trade_tracker_{file_name}.csv"
    current_date_str = util.get_current_time().strftime('%Y-%m-%d')
    
    if check_file_exists(file_path=file_name):
        df = pd.read_csv(file_name)
    else:
        df = pd.DataFrame(columns=["date", "system", "strategy", "pnl", "rr", "risk_percentage"])

    data = {"date":current_date_str, 
            "system":system, 
            "strategy":strategy, 
            "pnl": round(pnl, 2), 
            "rr":round(rr, 2), 
            "risk_percentage":each_pos_percentage}
    
    new_df = pd.DataFrame([data], columns=df.columns)
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_csv(file_name, index=False)


def get_strategy():
    file_name = f"data/trade_tracker_{util.get_server_ip()}.csv" 
    today_day = util.get_current_time().strftime("%A")
    # If it's a monday then reset to BREAK
    if today_day == "Monday":
        return "BREAK"
    
    if check_file_exists(file_path=file_name):
        df = pd.read_csv(file_name)
        if len(df) >= 2:
            previous_day = df.iloc[-1]
            prev_strategy = previous_day["strategy"]
            day_before_prev_day = df.iloc[-2]
            
            # if previous_day["pnl"] < 0 and day_before_prev_day["pnl"] < 0 and previous_day["strategy"] == day_before_prev_day["strategy"]:
            # Just a flip
            if previous_day["pnl"] < 0:
                # If PnL is negative for previous and day before previous then toggle
                return "BREAK" if prev_strategy == "REVERSE" else "REVERSE"
            else:
                return previous_day["strategy"]
    
    return "BREAK"


def get_previous_pnls():
    """
    Get last 3 records of the PnL
    """
    file_name = f"data/trade_tracker_{util.get_server_ip()}.csv"
    
    if check_file_exists(file_path=file_name):
        df = pd.read_csv(file_name)
        if len(df) > 3:
            df = df.tail(3).copy()
            return df
    
    return None

def get_dynamic_rr(num_records: int = 3, default:bool=True) -> float:
    """
    Calculate the dynamic risk-reward ratio (RR) based on the most traded files.

    This function reads the most recent CSV files from a specified directory, extracts the
    risk-reward ratio (RR) values, and calculates the average of the maximum RR values from
    each file. The RR values are converted to their absolute values before calculating the maximum.

    Args:
    num_records (int): The number of most recent files to consider. Default is 3.

    Returns:
    float: The average of the maximum RR values from the most recent files, rounded to 2 decimal places.
    """
    if default:
        return 2.0
    else:
        all_files = sorted(glob(f"data/pnl/{config.local_ip}/*"), reverse=True)[:num_records]
        df_dict = {"date": [], "max_rr": []}
        for file_name in all_files:
            date = file_name.split("/")[-1]
            single_file = pd.read_csv(file_name, names=["index", "system", "Strategy", "pnl", "rr", "risk"])
            single_file["rr"] = single_file["rr"].abs()
            df_dict["date"].append(date)
            max_rr = max(1, single_file["rr"].max())
            df_dict["max_rr"].append(max_rr)

        df = pd.DataFrame(df_dict)
        return min(2, round(df["max_rr"].mean(), 2))



def get_most_risk_percentage(file_name:str, **kwargs):
    """
    Calculate the adjusted risk percentage based on the most recent trades from a CSV file.

    This function reads a CSV file named in the format "trade_tracker_<file_name>.csv",
    checks the last two trades, and adjusts the risk percentage according to specific rules:
    
    1. If the most recent trade (last entry) is a loss (risk/reward ratio < 0), the risk 
       percentage is decreased by 0.05%, but not below 0.1%.
    2. If the last two trades are both wins (risk/reward ratio > 1) and the risk percentage 
       was the same for both, the risk percentage is increased by 0.05%, but not above 0.35%.
    3. If none of the above conditions are met, the current risk percentage remains unchanged.

    If the file does not exist or cannot be read, the function returns a default risk percentage of 0.1%.

    Args:
        file_name (str): The identifier to be appended to the prefix "trade_tracker_" for the CSV file name.

    Returns:
        float: The adjusted risk percentage rounded to two decimal places.
    """
    file_name = f"data/trade_tracker_{file_name}.csv"
    selected_strategy = kwargs["strategy"]
    
    MINIMUM_RISK=0.05
    MAXIMUM_RISK=0.35
    CHANGE_RATE=0.05
    
    if check_file_exists(file_path=file_name):
        df = pd.read_csv(file_name)
        df = df.tail(2).copy()
        
        """
        Strategy Selection
        """
        # If the last 2 trades are loss then change the strategy
        if len(df) > 0:
            previous_strategy = df.iloc[-1]["strategy"]
            if len(df) >= 2:
                last_2_trades = df.tail(2)
                if all(last_2_trades["rr"] < 0):
                    previous_strategy = "BREAK" if previous_strategy == "REVERSE" else "REVERSE"

        """
        Risk management
        """
        # If the last trade is loss then reduce the risk by 0.05%
        if df["rr"].iloc[-1] < 0:
            return round(max(float(df["risk_percentage"].iloc[-1]) - CHANGE_RATE, MINIMUM_RISK), 2), selected_strategy

        # If we have 2 continues wins then increase the risk by 0.05
        if len(df) >= 2:
            same_risk = df["risk_percentage"].nunique() == 1
            if same_risk:
                if all(df["rr"] > 1):
                    return round(min(float(df["risk_percentage"].unique()[-1]) + CHANGE_RATE, MAXIMUM_RISK), 2), selected_strategy

        
        return df["risk_percentage"].iloc[-1], selected_strategy

    return MINIMUM_RISK, selected_strategy

@DeprecationWarning
def record_pnl(iteration, pnl, rr, risk_per, strategy, system, dirc="pnl"):
    """
    Records profit and loss (PnL) data along with risk and reward ratios to a CSV file.
    
    This function saves the provided PnL, risk-reward ratio, and risk percentage data to a CSV file named
    with the current date in the format 'YYYY-MM-DD.csv'. The file is stored in a directory specific to the
    server's IP address, under 'data/pnl/'.

    Args:
        pnl (float): The profit or loss value to be recorded.
        rr (float): The risk-reward ratio to be recorded.
        risk_per (float): The risk percentage to be recorded.
    
    Side Effects:
        Creates a directory for storing PnL files if it does not already exist.
        Appends a line to a CSV file with the current timestamp, pnl, rr, and risk_per values.

    Utilizes:
        util.get_server_ip(): Retrieves the IP address of the server.
        util.get_current_time(): Retrieves the current time.
        create_directory_if_not_exists(directory_path): Ensures the target directory exists.
    """
    dir_path = f"data/{dirc}/{util.get_server_ip()}"
    create_directory_if_not_exists(directory_path=dir_path)
    current_date = util.get_current_time().strftime('%Y-%m-%d')
    file_path = f"{dir_path}/{current_date}.csv"
    with open(file_path, mode="a") as file:
        file.write(f"{iteration},{system},{strategy},{util.get_current_time().strftime('%Y-%m-%d %H:%M:%S')},{round(pnl, 2)},{round(rr, 2)},{risk_per}\n")

@DeprecationWarning
def record_pnl_directional(long_pnl, short_pnl, strategy, system, dirc="directional_pnl"):
    """
    Records the directional profit and loss (PnL) data to a CSV file.

    This function logs the long and short PnL values for a specific trading strategy and system 
    to a CSV file. The data is saved in a directory structure organized by the date and the server's IP address.

    Args:
        long_pnl (float): The profit and loss value for long positions.
        short_pnl (float): The profit and loss value for short positions.
        strategy (str): The name of the trading strategy.
        system (str): The identifier for the trading system.
        dirc (str, optional): The name of the top-level directory where the PnL data will be stored. 
                              Defaults to "directional_pnl".

    Details:
        - The function creates a directory structure under `data/` based on the specified directory 
          name (`dirc`) and the server's IP address.
        - The PnL data is appended to a CSV file named with the current date (in the format YYYY-MM-DD).
        - Each record in the CSV file contains the system, strategy, current timestamp, rounded long PnL, 
          and rounded short PnL values.
    """
    dir_path = f"data/{dirc}/{util.get_server_ip()}"
    create_directory_if_not_exists(directory_path=dir_path)
    current_date = util.get_current_time().strftime('%Y-%m-%d')
    file_path = f"{dir_path}/{current_date}.csv"
    with open(file_path, mode="a") as file:
        file.write(f"{system},{strategy},{util.get_current_time().strftime('%Y-%m-%d %H:%M:%S')},{round(long_pnl, 3)},{round(short_pnl, 3)}\n")

if __name__ == "__main__":
    # update_pnl("testing", "4_CDL", "REVERSE" , 100, -1.2, 0.15)
    # print(get_most_risk_percentage("testing", strategy="TESTING"))
    # print(get_previous_pnl_direction())
    # print(get_strategy())
    print(get_dynamic_rr())