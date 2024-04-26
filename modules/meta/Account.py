import MetaTrader5 as mt
from typing import Tuple

class Account:
    def get_account_name(self):
        info = mt.account_info()
        balance = round(info.balance/1000)
        return f"{info.name} {balance}K "

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

    def get_liquid_balance(self) -> float:
        return self.get_account_details().balance
    
    def get_equity(self) -> float:
        return self.get_account_details().equity
    
    def get_profit(self) -> float:
        return self.get_account_details().profit
