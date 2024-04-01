@REM sniper_ranger.bat 1% timeframe break

set account_risk=1
set target_ratio=10.0
set security=FOREX

python smart_trader.py ^
    --strategy break ^
    --security %security% ^
    --timeframe 60 ^
    --account_risk %account_risk% ^
    --each_position_risk 0.25 ^
    --target_ratio %target_ratio%