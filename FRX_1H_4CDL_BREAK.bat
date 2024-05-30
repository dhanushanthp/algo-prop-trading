set timeframe=60
set account_risk=1.0
set each_position_risk=0.1
set trades_per_day=15
set target_ratio=10.0
set security=FOREX
set systems=4CDL_REV_EXT
set strategy=BREAK
set enable_trail_stop=no
set enable_breakeven=yes
set enable_neutralizer=yes
set limit_profit_loss=yes
set start_hour=4

python smart_trader.py ^
    --strategy %strategy% ^
    --enable_trail_stop %enable_trail_stop% ^
    --enable_breakeven %enable_breakeven% ^
    --enable_neutralizer %enable_neutralizer% ^
    --limit_profit_loss %limit_profit_loss% ^
    --trades_per_day %trades_per_day% ^
    --num_prev_cdl_for_stop 2 ^
    --each_position_risk %each_position_risk% ^
    --systems %systems% ^
    --security %security% ^
    --timeframe %timeframe% ^
    --account_risk %account_risk% ^
    --start_hour %start_hour% ^
    --target_ratio %target_ratio%