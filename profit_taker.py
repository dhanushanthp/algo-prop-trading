import indicators as ind
import mng_pos as mp

while True:
    account_size, equity, _, total_active_profit = ind.get_account_details()
    
    if total_active_profit > 32:
        mp.close_all_positions()
        
    if total_active_profit < -16:
        mp.close_all_positions()
    
    