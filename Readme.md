# History
The first commit has been made on 2023 Nov 06, to start this as Meta Query Project.

# Automated Trading
I recommend automating trading instead of doing it manually. While it's possible for individuals to trade manually, emotions can negatively impact their decisions. For instance, a trader might gain confidence from a series of winning trades, not realizing that the market was simply favorable at that time. This confidence can lead to increased risk due to greed. If the market then reverses, the trader may not adapt, resulting in significant losses. Over time, this cycle can erode their confidence.


Emotions like greed and fear greatly influence this process. The best way to eliminate these emotions is by using a trading bot that makes decisions based on set rules, such as:

1. When to make a trade
2. Which symbol to trade
3. The risk level for each trade
4. Entry and exit plans


In trading, there's no single right or wrong approach. If a method works for you and brings in profit, that's what matters.

From my experience, I’ve learned that the market doesn’t always move in one direction. Some trading experts suggest holding your position until the market closes if you’re day trading. It’s also important to focus on tight stops with very high profit targets. I’ve been trading with a 1-hour timeframe, but the problem is that the stop is large, and hence the target must be large as well. This makes it challenging to achieve a high risk-to-reward ratio because entry opportunities are always a 50-50 chance. The only way to be profitable in the market is to have a very high risk-to-reward ratio to beat the odds of 50/50. Therefore, it’s best to focus on shorter timeframes, such as 15 minutes, because 5 minutes is very noisy. Trading based on reversal points is advisable since the market occasionally trends but mostly reverses, even on trend days.

# Mindset of trading
| **Win Rate (%)** | **Risk-Reward Ratio 1:1** | **Risk-Reward Ratio 1:2** | **Risk-Reward Ratio 1:3** | **Risk-Reward Ratio 1:4** | **Risk-Reward Ratio 1:5** |
|------------------|---------------------------|---------------------------|---------------------------|---------------------------|---------------------------|
| 90%              | 0.8                        | 1.7                        | 2.6                        | 3.5                        | 4.4                        |
| 80%              | 0.6                        | 1.4                        | 2.2                        | 3.0                        | 3.8                        |
| 70%              | 0.4                        | 1.1                        | 1.8                        | 2.5                        | 3.2                        |
| 60%              | 0.2                        | 0.8                        | 1.4                        | 2.0                        | 2.6                        |
| 55%              | 0.1                        | 0.65                       | 1.2                        | 1.75                       | 2.3                        |
| 50%              | 0.0                        | 0.5                        | 1.0                        | 1.5                        | 2.0                        |
| 45%              | -0.1                       | 0.35                       | 0.8                        | 1.25                       | 1.7                        |
| 40%              | -0.2                       | 0.2                        | 0.6                        | 1.0                        | 1.4                        |
| 35%              | -0.3                       | 0.05                       | 0.4                        | 0.75                       | 1.1                        |
| 30%              | -0.4                       | -0.1                       | 0.2                        | 0.5                        | 0.8                        |
| 25%              | -0.5                       | -0.25                      | 0.0                        | 0.25                       | 0.5                        |


# Configuration
### enable_neutralizer
(This don't work, Since market is unpreditable)
Assesses existing trading positions and identifies those that need neutralization based on a specified risk threshold. It compares the current price of each open position to a dynamically calculated midpoint. If the price crosses the threshold defined by `enable_ratio`, it recommends taking an opposite position to mitigate risk.

### enable_breakeven
(This don't work, Since market is unpreditable)
Moves the stop-loss of existing positions to the breakeven point once a certain profit threshold is met for each position.

### enable_trail_stop
(This don't work, Since market is unpreditable)
Activates trailing stops and targets for existing positions, guided by predefined multipliers and the trading timeframe.

### multiple_positions
(This don't work, Since market is unpreditable)
Defines the rule for managing multiple positions in the same symbol and direction. The default is "by_trades":

- **"by_active"**: Permits only one active position per direction for a symbol.
- **"by_active_limit"**: Limits the number of trades in the same direction for a symbol to a specified maximum.
- **"by_trades"**: Allows only one trade per direction per day for a symbol.
- **"by_open"**: Allows additional trades if a specified time interval has passed since the last trade.

> GO WITH A FLOW......

# Selected Strategies
## [Trade Based on Previos Day Close](FRX_PREV_DAY_CLOSE_DIR.bat)
| year_month | Win Rate |
|------------|--------------|
| 2023_10    | 49.0%        |
| 2023_11    | 57.0%        |
| 2023_12    | 50.0%        |
| 2024_1     | 44.0%        |
| 2024_2     | 56.0%        |
| 2024_3     | 48.0%        |
| 2024_4     | 51.0%        |
| 2024_5     | 57.0%        |
| 2024_6     | 52.0%        |
| 2024_7     | 58.0%        |
| 2024_8     | 52.0%        |


## [15 minutes 4 Candle Break](FRX_15M_4CDL_BREAK.bat)


## [15 minutes 4 Candle Reverse](FRX_15M_4CDL_REVERSE.bat)
