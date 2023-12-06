import time
import mng_pos as mp
import indicators as ind
import sys
from datetime import datetime
import MetaTrader5 as mt


account_size, _, _, _ = ind.get_account_details()

# establish connection to MetaTrader 5 terminal
if not mt.initialize():
    print("initialize() failed, error code =", mt.last_error())
    quit()

while True:
    print(f"\n-------  Executed @ {datetime.now().strftime('%H:%M:%S')}------------------")
    # Fail Safe
    _, equity, _, _ = ind.get_account_details()
    print(f"Equity: {equity}, account_size: {account_size - account_size * 2/100}")
    if equity <= account_size - account_size * 2/100:
        mp.close_all_positions()
        sys.exit()
    
    # mp.exist_on_initial_plan_changed()
    mp.breakeven_1R_positions()
    time.sleep(60)