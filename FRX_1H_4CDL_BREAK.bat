REM Set the path to project
set TRADEAU_PATH=C:\Users\%USERNAME%\OneDrive\Financial Freedom\Phoenix
set PYTHONPATH=%PYTHONPATH%;%TRADEAU_PATH%
cd /d %TRADEAU_PATH%

REM Time and Trading
set start_hour=4
set timeframe=60
set trades_per_day=100

REM Risk Management
set account_risk=1.0
set each_position_risk=0.1
set target_ratio=5.0
set enable_dynamic_position_risk=no
set max_loss_exit=yes
set max_target_exit=yes

REM Strategy and System
set strategy=BREAK
set systems=4CDL_PULLBACK_EXT

REM Security
set security=FOREX

REM Trade Controls
set enable_trail_stop=no
set enable_breakeven=yes
set enable_neutralizer=yes
set multiple_positions=by_trades

python smart_trader.py ^
    --strategy %strategy% ^
    --enable_trail_stop %enable_trail_stop% ^
    --enable_breakeven %enable_breakeven% ^
    --enable_neutralizer %enable_neutralizer% ^
    --max_loss_exit %max_loss_exit% ^
    --max_target_exit %max_target_exit% ^
    --trades_per_day %trades_per_day% ^
    --num_prev_cdl_for_stop 2 ^
    --each_position_risk %each_position_risk% ^
    --systems %systems% ^
    --security %security% ^
    --timeframe %timeframe% ^
    --account_risk %account_risk% ^
    --start_hour %start_hour% ^
    --enable_dynamic_position_risk %enable_dynamic_position_risk% ^
    --multiple_positions %multiple_positions% ^
    --target_ratio %target_ratio%