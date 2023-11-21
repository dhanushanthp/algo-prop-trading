import indicators as ind
import mng_pos as mp

while True:
    mp.breakeven_1R_positions()
    account_size, equity, _, total_active_profit = ind.get_account_details()
    
    if total_active_profit > 100:
        mp.close_all_positions()
    
    # if equity < account_size-100:
    #     mp.close_all_positions()
    
    