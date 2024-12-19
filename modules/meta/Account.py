import MetaTrader5 as mt
mt.initialize()
from typing import Tuple

class Account:
    def get_account_name(self):
        info = mt.account_info()
        balance = round(info.balance/1000)
        return f"{info.name}"

    def get_account_details(self):
        """
        Retrieves and returns essential details of the trading account.

        This function fetches information such as balance, equity, margin-free funds,
        and profit from the MetaTrader 5 trading account. If the account information is
        successfully obtained, it returns a Object containing these values.

        Returns:
            Object: Object of balance, equity, margin_free, profit.
                Returns None if account information retrieval fails.
        """
        
        account_info=mt.account_info()
        return account_info
    
    def get_account_id(self):
        return self.get_account_details().login

    def get_liquid_balance(self) -> float:
        return self.get_account_details().balance
    
    def get_equity(self) -> float:
        """
        What is the actual amount that my account is holding with the reflection of PnL
        """
        return self.get_account_details().equity
    
    def get_profit(self) -> float:
        return self.get_account_details().profit
    
if __name__ == "__main__":
    ref = Account()
    print(ref.get_account_id())