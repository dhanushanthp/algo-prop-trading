import pandas as pd
from datetime import datetime

def update_pnl(pnl:float, rr:float, each_pos_percentage:float):
    """
    Updates the profit and loss (PnL) tracker with the provided data.

    Parameters:
        pnl (float): The profit or loss value to be recorded.
        rr (float): The risk-reward ratio associated with the trade.
        each_pos_percentage (float): The percentage of risk for each position.

    Returns:
        None

    This function reads the existing trade tracker data from 'trade_tracker.csv', 
    appends a new row with the current date, pnl, rr, and each_pos_percentage values, 
    and writes the updated data back to 'trade_tracker.csv'.
    """

    current_date_str = datetime.now().strftime("%Y-%m-%d")
    df = pd.read_csv("trade_tracker.csv")
    data = {"date":current_date_str, "pnl": round(pnl, 2), "rr":round(rr, 2), "risk_percentage":each_pos_percentage}
    new_df = pd.DataFrame([data], columns=df.columns)
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_csv("trade_tracker.csv", index=False)

# update_pnl(100, 1.2, 0.1)

def get_most_risk_percentage():
    df = pd.read_csv("trade_tracker.csv")
    df = df.tail(2).copy()
    
    # If the last trade is loss then reduce the risk by 0.05%
    if df["rr"].iloc[-1] < 0:
        return round(max(float(df["risk_percentage"].iloc[-1]) - 0.05, 0.1), 2)

    # If we have 2 continues wins then increase the risk by 0.05
    if len(df) >= 2:
        same_risk = df["risk_percentage"].nunique() == 1
        if same_risk:
            if all(df["rr"] > 1):
                return round(min(float(df["risk_percentage"].unique()[-1]) + 0.05, 0.35), 2)
    
    return df["risk_percentage"].iloc[-1]
        

# print(get_most_risk_percentage())