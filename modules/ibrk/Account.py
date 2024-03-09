class Account:
    def __init__(self, ibrk):
        self.ibrk = ibrk

    def get_liquid_balance(self) -> float:
        return float(self.ibrk.get_account()["liquidity"])
    
    def get_equity(self) -> float:
        return float(self.ibrk.get_account()["accout_value"])
    
    def get_profit(self) -> float:
        return float(self.ibrk.get_account()["unrealized_pnl"])

if __name__ == "__main__":
    obj = Account()
    print(obj.get_liquid_balance())
    print(obj.get_equity())
    print(obj.get_profit())