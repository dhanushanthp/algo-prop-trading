import pandas as pd
from datetime import datetime
import os
from modules.meta import util

def check_file_exists(file_path):
    if os.path.isfile(file_path):
        return True
    else:
        return False

def create_directory_if_not_exists(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    
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

if __name__ == "__main__":
    # update_pnl("testing", "4_CDL", "REVERSE" , 100, -1.2, 0.15)
    print(get_most_risk_percentage("testing", strategy="TESTING"))