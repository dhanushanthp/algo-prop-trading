import indicators as ind
import mng_pos as mp
from datetime import datetime

while True:
    mp.breakeven_1R_positions()
    account_size, equity, _, total_active_profit = ind.get_account_details()
    
    if total_active_profit > 50:
        print(f"Profit taking hit @ {datetime.now().strftime('%H:%M:%S')}")
        mp.close_all_positions()
    
    # if equity < account_size-100:
    #     mp.close_all_positions()
    
    