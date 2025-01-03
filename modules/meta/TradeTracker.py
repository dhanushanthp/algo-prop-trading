from modules.meta.Account import Account
from modules.meta import util
from modules.common import files_util
import time
import pandas as pd
from pprint import pprint

class TradeTracker:
    def __init__(self):
        self.account = Account()
        self.account_id = self.account.get_account_id()
        self.account_name = self.account.get_account_name()

    def symbol_historic_pnl(self, each_position_risk_appertide)->list:
        """
        Calculate the historic profit and loss (PnL) for each symbol and identify symbols with a mean PnL below a specified risk appetite.
        Args:
            each_position_risk_appertide (float): The risk appetite threshold for each position. Symbols with a mean PnL below the negative of this value will be flagged.
        Returns:
            list: A list of symbols that have a mean PnL below the specified risk appetite threshold.
        Raises:
            FileNotFoundError: If the CSV file containing the PnL data does not exist.
            pd.errors.EmptyDataError: If the CSV file is empty.
            KeyError: If the required columns ("Symbol", "PnL") are not present in the CSV file.
        """

        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/symbol_trade_logs/{self.account_id}_{current_date}.csv"
        df = pd.read_csv(file_path)
        df = df.groupby("Symbol")["PnL"].mean().reset_index(name="pnl_mean")
        df["risk_position"] = df["pnl_mean"] < (- each_position_risk_appertide)
        pprint(df)
        selected_symbols =  df[df["risk_position"]]["Symbol"].unique()
        return selected_symbols


    def record_pnl_logs(self, pnl, rr):
        """
        Records profit and loss (PnL) logs along with risk-reward (RR) ratio to a CSV file.
        This method creates a new CSV file for each day if it does not already exist, 
        and appends the PnL and RR data with a timestamp to the file.
        Args:
            pnl (float): The profit and loss value to be recorded.
            rr (float): The risk-reward ratio to be recorded.
        Returns:
            None
        """
        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/trade_logs/{self.account_id}_{current_date}.csv"

        if not files_util.check_file_exists(file_path=file_path):
            with open(file_path, mode="w") as file:
                file.write("Timestamp,AccountID,Pnl,RR\n")

        with open(file_path, mode="a") as file:
            file.write(f"{util.get_current_time().strftime('%Y-%m-%d %H:%M:%S')},{self.account_id},{round(pnl, 2)},{round(rr, 2)}\n")
    
    def record_symbol_pnl_logs(self, pnl_df:pd.DataFrame):
        """
        Records the profit and loss (PnL) logs for symbols to a CSV file.
        
        Args:
            pnl_df (pandas.DataFrame): A DataFrame containing the PnL data with columns "Symbol" and "PnL".
        
        The function appends the PnL data to a CSV file named with the account ID and current date.
        If the file does not exist, it creates the file and writes the header.
        The CSV file is stored in the "PnLData/symbol_trade_logs/" directory.
        """

        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/symbol_trade_logs/{self.account_id}_{current_date}.csv"

        if not files_util.check_file_exists(file_path=file_path):
            with open(file_path, mode="w") as file:
                file.write("Timestamp,Symbol,PnL\n")

        pnl_df["Timestamp"] = util.get_current_time().strftime('%Y-%m-%d %H:%M:%S')
        pnl_df.rename(columns={"symbol": "Symbol", "net_pnl":"PnL"}, inplace=True)
        pnl_df = pnl_df[["Timestamp", "Symbol", "PnL"]]
        pnl_df.to_csv(file_path, mode="a", header=False, index=False)

    def daily_pnl_track(self, pnl, rr, system, strategy, account_risk_percentage, each_position_risk_percentage, equity):
        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/pnl_trades/{self.account_id}.csv"

        if not files_util.check_file_exists(file_path=file_path):
            with open(file_path, mode="w") as file:
                file.write("Date,AccountID,AccountName,System,Strategy,AccountRiskPerc,PositionRiskPerc,Pnl,RR,Equity\n")

        with open(file_path, mode="a") as file:
            file.write(f"{current_date},{self.account_id},{self.account_name},{system},{strategy},{account_risk_percentage},{each_position_risk_percentage},{round(pnl, 2)},{round(rr, 2)},{round(equity)}\n")

if __name__ == "__main__":
    ref = TradeTracker()
    # for i in range(10):
    #     ref.record_pnl_logs(200, 2.0)
    #     time.sleep(2)

    # for i in range(10):
    #     ref.daily_pnl_track(200, 2.0, "Syste", "strategy", "acc_per", "eachPos")

    print(ref.symbol_historic_pnl(each_position_risk_appertide=12))