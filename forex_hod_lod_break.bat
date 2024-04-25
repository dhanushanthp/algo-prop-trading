set account_risk=1
set target_ratio=5.0
set security=FOREX
set system=DAILY_HL

python smart_trader.py ^
    --strategy break ^
    --trades_per_day 10 ^
    --each_position_risk 0.3 ^
    --system %system% ^
    --security %security% ^
    --timeframe 60 ^
    --account_risk %account_risk% ^
    --target_ratio %target_ratio%