@REM test: sniper_ranger.bat break no yes
@REM real: sniper_ranger.bat break yes no

python sniper_ranger.py ^
    --strategy %1 ^
    --timeframe 60 ^
    --account_risk 1.0 ^
    --each_position_risk 0.5 ^
    --target_ratio 2.0 ^
    --early_profit yes ^
    --early_rr 1.1 ^
    --trace_exit %2 ^
    --persist_data no ^
    --addtional_levels %3