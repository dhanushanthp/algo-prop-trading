@REM sniper_ranger.bat 1% timeframe break

set account_risk=%1
set target_ratio=2.0

python sniper_ranger.py ^
    --strategy %3 ^
    --timeframe %2 ^
    --account_risk %account_risk% ^
    --each_position_risk 0.5 ^
    --target_ratio %target_ratio% ^
    --early_rr 2.0