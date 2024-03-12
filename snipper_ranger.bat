@REM sniper_ranger.bat 1%

set account_risk=%1
set target_ratio=2.0

python sniper_ranger.py ^
    --strategy break ^
    --timeframe 60 ^
    --account_risk %account_risk% ^
    --each_position_risk 0.5 ^
    --target_ratio %target_ratio% ^
    --early_rr 1.5