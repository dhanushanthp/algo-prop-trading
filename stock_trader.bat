@REM sniper_ranger.bat 1% timeframe break

set account_risk=1
set target_ratio=4.0
set security=STOCK

python smart_trader.py ^
    --strategy break ^
    --security %security% ^
    --timeframe 5 ^
    --account_risk %account_risk% ^
    --each_position_risk 0.5 ^
    --target_ratio %target_ratio%