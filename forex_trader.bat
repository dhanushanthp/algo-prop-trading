@REM sniper_ranger.bat 1% timeframe break

set account_risk=1
set target_ratio=8.0
set security=FOREX
set system=3CDL_STR

python smart_trader.py ^
    --strategy break ^
    --system %system% ^
    --security %security% ^
    --timeframe 60 ^
    --account_risk %account_risk% ^
    --each_position_risk 0.5 ^
    --target_ratio %target_ratio%