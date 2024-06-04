set timeframe=60
set account_risk=1.0
set each_position_risk=0.1
set trades_per_day=100
set target_ratio=10.0
set security=FOREX
set systems=DAILY_HL,DAILY_HL_DOUBLE_HIT
set strategy=BREAK
set enable_trail_stop=no
set enable_breakeven=no
set enable_neutralizer=yes
set limit_profit_loss=yes
set start_hour=4
set enable_dynamic_position_risk=yes

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
    --enable_dynamic_position_risk %enable_dynamic_position_risk% ^
    --target_ratio %target_ratio%