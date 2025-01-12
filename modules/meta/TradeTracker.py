from modules.meta.Account import Account
from modules.meta import util
from modules.common import files_util
import time
import pandas as pd
from tabulate import tabulate
from glob import glob

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
        if files_util.check_file_exists(file_path=file_path):
            df = pd.read_csv(file_path)
            df = df.groupby("Symbol")["PnL"].mean().round(2).reset_index(name="PnL")
            df["risk_position"] = df["PnL"] < (- each_position_risk_appertide)
            self.record_symbol_moving_average(pnl_df=df)
            print(tabulate(df, headers='keys', tablefmt='pretty', showindex=False))
            selected_symbols =  df[df["risk_position"]]["Symbol"].unique()
            return selected_symbols

        return []
    
    def get_dynamic_account_risk_percen(self, max_account_risk:float) -> float:
        """
        Calculate the dynamic position size based on the account's recent trade performance.
        Args:
            max_account_risk (float): The maximum allowable position size.
        Returns:
            float: The calculated position size.
        The function reads the account's trade data from a CSV file and adjusts the position size based on the 
        performance of the last three trades. If there are fewer than three records, it returns a default position 
        size of 1.0. If the last three trades were losses, it decreases the position size by 0.1, but not below 1. 
        Otherwise, it increases the position size by 0.1, up to the maximum allowable position size.
        """
        file_path = f"PnLData/pnl_trades/{self.account_id}.csv"

        # If exists, means at least one trade has been made
        if files_util.check_file_exists(file_path=file_path):
            df = pd.read_csv(file_path)
            last_acc_risk_perc = df.iloc[-1]["AccountRiskPerc"]
            prev_day_pnl = df.iloc[-1]["Pnl"]
            
            # Check if the last 3 trades were losses
            if len(df) > 3:
                # Reset the trade percentage
                if all(df["Pnl"].tail(3) < 0):
                    return 1.0

            if prev_day_pnl > 0:
                # Winning Trades
                return min(max_account_risk, last_acc_risk_perc + 0.1)
            else:
                # Losing Trades
                return max(1.0, last_acc_risk_perc - 0.1)
                
        return 1.0


    def get_dynamic_rr(self, num_records:int=5, default:float=2.0) -> float:
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
        current_time = util.get_current_time()
        current_date = current_time.strftime('%Y-%m-%d')
        all_files = glob(f"PnLData/trade_logs/{self.account_id}_*.csv")
        all_files = [file for file in all_files if current_date not in file]
        if len(all_files) >= num_records:
            all_files = sorted(all_files, reverse=True)[:num_records]
            df_dict = {"date": [], "max_rr": []}
            for file_name in all_files:
                date = file_name.split("/")[-1].split("_")[-1].split(".")[0]
                single_file = pd.read_csv(file_name)
                single_file["RR"] = single_file["RR"].abs()
                df_dict["date"].append(date)
                max_rr = max(1, single_file["RR"].max())
                df_dict["max_rr"].append(max_rr)

            df = pd.DataFrame(df_dict)
            return max(default, round(df["max_rr"].mean() - 1, 2))
        
        return default
    

    def get_rr_change(self) -> tuple:
        """
        Calculate the change in risk-reward (RR) over the last 5 minutes.
        This method reads a CSV file containing trade logs for the current date,
        filters the data to include only the last 5 minutes, and calculates the 
        change in RR within that period.
        Returns:
            tuple: A tuple containing:
                - rr_change (float): The difference between the maximum and minimum RR values in the last 5 minutes.
                - max_rr (float): The maximum RR value in the last 5 minutes.
                - min_rr (float): The minimum RR value in the last 5 minutes.
        """
        current_time = util.get_current_time()
        current_date = current_time.strftime('%Y-%m-%d')
        file_path = f"PnLData/trade_logs/{self.account_id}_{current_date}.csv"
        if files_util.check_file_exists(file_path=file_path):
            df = pd.read_csv(file_path)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df.set_index('Timestamp', inplace=True)
            # Filter data for the last 5 minutes
            current_time = pd.to_datetime(current_time.strftime('%Y-%m-%d %H:%M:%S'))
            filtered_df = df.loc[current_time - pd.Timedelta(minutes=5):current_time]
            if not filtered_df.empty:
                rr_change = round(filtered_df['RR'].max() - filtered_df['RR'].min(), 2)
                return rr_change, round(filtered_df['RR'].max(), 2), round(filtered_df['RR'].min(), 2)
        
        return 0, 0, 0


    def record_pnl_logs(self, pnl, rr, rr_change):
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
                file.write("Timestamp,AccountID,Pnl,RR,RRChange\n")

        with open(file_path, mode="a") as file:
            file.write(f"{util.get_current_time().strftime('%Y-%m-%d %H:%M:%S')},{self.account_id},{round(pnl, 2)},{round(rr, 2)},{round(rr_change, 2)}\n")
    
    def record_symbol_moving_average(self, pnl_df:pd.DataFrame):
        """
        Records the moving average of symbols' profit and loss (PnL) to a CSV file.
        This function takes a DataFrame containing symbols and their respective PnL,
        adds a timestamp, and appends the data to a CSV file named with the account ID
        and the current date. If the file does not exist, it creates it and writes the
        header.
        Args:
            pnl_df (pd.DataFrame): A DataFrame containing the columns "Symbol" and "PnL".
        Returns:
            None
        """
        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/symbol_moving_avg/{self.account_id}_{current_date}.csv"

        # Only pick selected columns
        pnl_df = pnl_df[["Symbol", "PnL"]].copy()

        if not files_util.check_file_exists(file_path=file_path):
            with open(file_path, mode="w") as file:
                file.write("Timestamp,Symbol,PnL\n")

        pnl_df["Timestamp"] = util.get_current_time().strftime('%Y-%m-%d %H:%M:%S')
        pnl_df = pnl_df[["Timestamp", "Symbol", "PnL"]]
        pnl_df.to_csv(file_path, mode="a", header=False, index=False)

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
                file.write("Timestamp,Symbol,PnL,Mark\n")

        pnl_df["Timestamp"] = util.get_current_time().strftime('%Y-%m-%d %H:%M:%S')
        pnl_df.rename(columns={"symbol": "Symbol", "net_pnl":"PnL"}, inplace=True)
        pnl_df = pnl_df[["Timestamp", "Symbol", "PnL", "Mark"]]
        pnl_df.to_csv(file_path, mode="a", header=False, index=False)

    def daily_pnl_track(self, pnl, rr, strategy, market_direction, account_risk_percentage, each_position_risk_percentage, equity):
        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/pnl_trades/{self.account_id}.csv"

        if not files_util.check_file_exists(file_path=file_path):
            with open(file_path, mode="w") as file:
                file.write("Date,AccountID,AccountName,System,Strategy,AccountRiskPerc,PositionRiskPerc,Pnl,RR,Equity\n")

        with open(file_path, mode="a") as file:
            file.write(f"{current_date},{self.account_id},{self.account_name},{strategy},{market_direction},{account_risk_percentage},{each_position_risk_percentage},{round(pnl, 2)},{round(rr, 2)},{round(equity)}\n")

if __name__ == "__main__":
    ref = TradeTracker()
    # for i in range(10):
    #     ref.record_pnl_logs(200, 2.0)
    #     time.sleep(2)

    # for i in range(10):
    #     ref.daily_pnl_track(200, 2.0, "Syste", "strategy", "acc_per", "eachPos")

    # print(ref.symbol_historic_pnl(each_position_risk_appertide=12))
    # print(ref.get_rr_change())
    print(ref.get_dynamic_rr(default=10.0))