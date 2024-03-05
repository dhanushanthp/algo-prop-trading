@REM test: sniper_ranger.bat break no yes
@REM real: sniper_ranger.bat break yes no

set account_risk=1.0
set timeframe=60
set target_ratio=2.0

python sniper_ranger.py ^
    --strategy %1 ^
    --timeframe %timeframe% ^
    --account_risk %account_risk% ^
    --each_position_risk 0.5 ^
    --target_ratio %target_ratio% ^
    --early_profit yes ^
    --early_rr 1.1 ^
    --trace_exit %2 ^
    --persist_data no ^
    --addtional_levels %3