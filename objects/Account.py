import MetaTrader5 as mt
from typing import Tuple

class Account:
    def __init__(self) -> None:
        pass

    def get_account_name(self):
        info = mt.account_info()
        balance = round(info.balance/1000)
        return f"{info.name} {balance}K "

    def get_account_details() -> Tuple[float, float, float, float]:
        """
        Retrieves and returns essential details of the trading account.

        This function fetches information such as balance, equity, margin-free funds,
        and profit from the MetaTrader 5 trading account. If the account information is
        successfully obtained, it returns a tuple containing these values.

        Returns:
            tuple: A tuple containing trading account details in the order of (balance, equity, margin_free, profit).
                Returns None if account information retrieval fails.
        """
        
        account_info=mt.account_info()
        if account_info!=None:
            # display trading account data 'as is'
            return account_info.balance, account_info.equity, account_info.margin_free, account_info.profit
