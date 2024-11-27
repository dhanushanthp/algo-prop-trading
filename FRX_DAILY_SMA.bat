REM Set the path to project
set TRADEAU_PATH=C:\Users\%USERNAME%\OneDrive\Financial Freedom\Phoenix
set PYTHONPATH=%PYTHONPATH%;%TRADEAU_PATH%
cd /d %TRADEAU_PATH%

REM Time and Trading
set start_hour=1
set atr_check_timeframe=60
set timeframe=15
set trades_per_day=100

REM Risk Management
set entry_with_st_tgt=no
set account_risk=1.0
set account_target_ratio=2.0
set each_position_risk=0.02
set target_ratio=5.0
set enable_dynamic_direction=no
set max_loss_exit=yes
set max_target_exit=yes

REM Strategy and System
set strategy=BREAK
set systems=DAY_CLOSE_SMA

REM Security
set security=FOREX

REM Trade Controls
set enable_trail_stop=no
set enable_breakeven=no
set enable_neutralizer=no
REM by_active or by_trades or by_open or by_active_limit or by_active_both_direction or by_active_single_direction
set multiple_positions=by_active_single_direction

set record_pnl=yes
set close_by_time=no
set close_by_solid_cdl=no

REM NON-PRIMARY, PRIMARY, SINGLE
set primary_symbols=PRIMARY
REM CANDLE or "ATR5M", "ATR15M", "ATR1H", "ATR2H", "ATR4H", "ATR1D"
set primary_stop_selection=ATR15M
set enable_sec_stop_selection=no
set secondary_stop_selection=ATR15M
set max_trades_on_same_direction=100

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
    --atr_check_timeframe %atr_check_timeframe% ^
    --account_risk %account_risk% ^
    --start_hour %start_hour% ^
    --enable_dynamic_direction %enable_dynamic_direction% ^
    --multiple_positions %multiple_positions% ^
    --record_pnl %record_pnl% ^
    --close_by_time %close_by_time% ^
    --close_by_solid_cdl %close_by_solid_cdl% ^
    --primary_symbols %primary_symbols% ^
    --primary_stop_selection %primary_stop_selection% ^
    --secondary_stop_selection %secondary_stop_selection% ^
    --enable_sec_stop_selection %enable_sec_stop_selection% ^
    --max_trades_on_same_direction %max_trades_on_same_direction% ^
    --account_target_ratio %account_target_ratio% ^
    --entry_with_st_tgt %entry_with_st_tgt% ^
    --target_ratio %target_ratio%