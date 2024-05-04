set timeframe=60
set account_risk=1.0
set each_position_risk=0.1
set trades_per_day=10
set target_ratio=5.0
set security=FOREX
set systems=DAILY_HL,3CDL_STR
set strategy=break
set enable_trail_stop=no
set enable_breakeven=yes

python smart_trader.py ^
    --strategy %strategy% ^
    --enable_trail_stop %enable_trail_stop% ^
    --enable_breakeven %enable_breakeven% ^
    --trades_per_day %trades_per_day% ^
    --num_prev_cdl_for_stop 2 ^
    --each_position_risk %each_position_risk% ^
    --systems %system% ^
    --security %security% ^
    --timeframe %timeframe% ^
    --account_risk %account_risk% ^
    --target_ratio %target_ratio%