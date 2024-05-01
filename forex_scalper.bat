set account_risk=3
set target_ratio=5.0
set security=FOREX
set system=SCALPER

python scalper.py ^
    --strategy break ^
    --trades_per_day 10 ^
    --each_position_risk 0.5 ^
    --system %system% ^
    --security %security% ^
    --timeframe 60 ^
    --account_risk %account_risk% ^
    --target_ratio %target_ratio%