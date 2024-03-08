@REM test: sniper_ranger.bat break 60 no
@REM real: sniper_ranger.bat break 60 yes

set account_risk=2.0
set strategy=%1
set timeframe=%2
set target_ratio=2.0

python sniper_ranger.py ^
    --strategy %strategy% ^
    --timeframe %timeframe% ^
    --account_risk %account_risk% ^
    --each_position_risk 0.5 ^
    --target_ratio %target_ratio% ^
    --early_profit yes ^
    --early_rr 1.1 ^
    --trace_exit %3 ^
    --persist_data no ^
    --addtional_levels no