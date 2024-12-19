from modules.meta.Account import Account
from modules.meta import util
from modules.common import files_util
import time

class TradeTracker:
    def __init__(self):
        self.account = Account()
        self.account_id = self.account.get_account_id()
        self.account_name = self.account.get_account_name()

    def record_pnl_logs(self, pnl, rr):
        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/trade_logs/{self.account_id}_{current_date}.csv"

        if not files_util.check_file_exists(file_path=file_path):
            with open(file_path, mode="w") as file:
                file.write("Timestamp,AccountID,Pnl,RR\n")

        with open(file_path, mode="a") as file:
            file.write(f"{util.get_current_time().strftime('%Y-%m-%d %H:%M:%S')},{self.account_id},{round(pnl, 2)},{round(rr, 2)}\n")

    def daily_pnl_track(self, pnl, rr, system, strategy, account_risk_percentage, each_position_risk_percentage):
        current_date = util.get_current_time().strftime('%Y-%m-%d')
        file_path = f"PnLData/pnl_trades/{self.account_id}.csv"

        if not files_util.check_file_exists(file_path=file_path):
            with open(file_path, mode="w") as file:
                file.write("Date,AccountID,AccountName,System,Strategy,AccountRiskPerc,PositionRiskPerc,Pnl,RR\n")

        with open(file_path, mode="a") as file:
            file.write(f"{current_date},{self.account_id},{self.account_name},{system},{strategy},{account_risk_percentage},{each_position_risk_percentage},{round(pnl, 2)},{round(rr, 2)}\n")

if __name__ == "__main__":
    ref = TradeTracker()
    # for i in range(10):
    #     ref.record_pnl_logs(200, 2.0)
    #     time.sleep(2)

    for i in range(10):
        ref.daily_pnl_track(200, 2.0, "Syste", "strategy", "acc_per", "eachPos")