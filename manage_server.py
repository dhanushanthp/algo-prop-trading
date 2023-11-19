import time
import mng_pos as mp

import MetaTrader5 as mt

# establish connection to MetaTrader 5 terminal
if not mt.initialize():
    print("initialize() failed, error code =", mt.last_error())
    quit()

while True:
    # mp.exist_on_initial_plan_changed()
    mp.breakeven_1R_positions()
    time.sleep(60)